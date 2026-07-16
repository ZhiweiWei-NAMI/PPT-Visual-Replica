#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree

from PIL import Image


VALID_CLASSIFICATIONS = {"text", "layout_native", "imagegen_asset"}
VALID_IMAGE_SOURCES = {"imagegen_asset", "openai_image", "gemini_image", "user_asset"}
REQUIRED_MATCH_QA = {
    "identity",
    "isolation",
    "border_integrity",
    "alpha_or_chroma",
    "style_fidelity",
}
REQUIRED_VISUAL_CHECKS = {
    "overall_fidelity",
    "asset_completeness",
    "border_integrity",
    "alpha_or_chroma",
    "text_layout",
    "residual_review",
}
REQUIRED_HASH_FILES = {
    "reference",
    "pptx",
    "preview",
    "asset_manifest",
    "layout_manifest",
}
PATH_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".json", ".jsonl", ".pptx"}


class Validator:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.gates: list[dict[str, Any]] = []
        self.failures: list[str] = []
        self.parsed: dict[Path, Any] = {}

    def gate(self, name: str, passed: bool, details: Any = None) -> None:
        status = "pass" if passed else "fail"
        record: dict[str, Any] = {"name": name, "status": status}
        if details not in (None, [], {}, ""):
            record["details"] = details
        self.gates.append(record)
        if not passed:
            self.failures.append(name)

    def resolve(self, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.root / path
        return path.resolve()

    def relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(path.resolve())

    def load_json(self, path: Path) -> Any:
        if path in self.parsed:
            return self.parsed[path]
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        self.parsed[path] = data
        return data

    def load_jsonl(self, path: Path) -> list[Any]:
        if path in self.parsed:
            return self.parsed[path]
        rows = []
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8-sig").splitlines(), 1
        ):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise ValueError(f"{path}:{line_number}: {error}") from error
        self.parsed[path] = rows
        return rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_pixel_sha256(image: Image.Image) -> str:
    normalized = image.convert("RGBA")
    digest = hashlib.sha256()
    digest.update(f"{normalized.width}x{normalized.height}".encode("ascii"))
    digest.update(normalized.tobytes())
    return digest.hexdigest()


def cycle_number(path: Path) -> int:
    match = re.search(r"cycle_(\d+)", path.name)
    return int(match.group(1)) if match else -1


def records(data: Any, keys: Iterable[str]) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def record_id(item: dict[str, Any]) -> str:
    return str(
        item.get("semantic_unit_id") or item.get("anchor_id") or item.get("id") or ""
    ).strip()


def classification(item: dict[str, Any]) -> str:
    values = [
        str(item[key]).strip().lower()
        for key in ("classification", "route", "class")
        if item.get(key) is not None
    ]
    return values[0] if len(set(values)) == 1 and values else ""


def valid_bbox(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    try:
        numbers = [float(item) for item in value]
    except (TypeError, ValueError):
        return False
    return numbers[2] > 0 and numbers[3] > 0


def extract_path_values(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for child in value.values():
            found.update(extract_path_values(child))
    elif isinstance(value, list):
        for child in value:
            found.update(extract_path_values(child))
    elif isinstance(value, str):
        candidate = Path(value)
        if candidate.suffix.lower() in PATH_SUFFIXES:
            found.add(value)
    return found


def parse_picture_metadata(description: str) -> str:
    try:
        payload = json.loads(description)
    except json.JSONDecodeError:
        match = re.search(r"semantic_unit_id[=:]\s*([^;\s]+)", description)
        return match.group(1) if match else ""
    if isinstance(payload, dict):
        return str(payload.get("semantic_unit_id") or "")
    return ""


def pptx_evidence(path: Path) -> dict[str, Any]:
    namespaces = {
        "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    }
    picture_ids: list[str] = []
    triangle_shapes = []
    native_arrowheads = 0
    media_hashes = []
    media_pixel_hashes = []
    with zipfile.ZipFile(path) as archive:
        slide_names = sorted(
            name
            for name in archive.namelist()
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        )
        for slide_name in slide_names:
            root = ElementTree.fromstring(archive.read(slide_name))
            for node in root.findall(".//p:pic/p:nvPicPr/p:cNvPr", namespaces):
                picture_ids.append(parse_picture_metadata(node.attrib.get("descr", "")))
            for node in root.findall(".//p:sp/p:spPr/a:prstGeom", namespaces):
                if node.attrib.get("prst") in {"triangle", "rtTriangle"}:
                    triangle_shapes.append(
                        {"slide": slide_name, "preset": node.attrib.get("prst")}
                    )
            native_arrowheads += len(root.findall(".//a:headEnd", namespaces))
            native_arrowheads += len(root.findall(".//a:tailEnd", namespaces))
        for name in archive.namelist():
            if name.startswith("ppt/media/") and not name.endswith("/"):
                payload = archive.read(name)
                media_hashes.append(hashlib.sha256(payload).hexdigest())
                try:
                    with Image.open(io.BytesIO(payload)) as image:
                        media_pixel_hashes.append(image_pixel_sha256(image))
                except (OSError, ValueError):
                    pass
    return {
        "slide_count": len(slide_names),
        "picture_semantic_ids": picture_ids,
        "triangle_shapes": triangle_shapes,
        "native_arrowhead_count": native_arrowheads,
        "media_hashes": media_hashes,
        "media_pixel_hashes": media_pixel_hashes,
    }


def validate(root: Path, report_path: Path) -> dict[str, Any]:
    validator = Validator(root)
    required = {
        "reference": root / "reference.png",
        "inventory": root / "visual_inventory.json",
        "asset_manifest": root / "asset_manifest.json",
        "layout_manifest": root / "layout_manifest.json",
        "layout_rules": root / "layout_rules.json",
        "visual_review": root / "visual_review.json",
    }
    required_dirs = [
        root / "reference_crops",
        root / "prompts",
        root / "generated",
        root / "assets",
        root / "validation",
    ]
    missing = [
        validator.relative(path) for path in required.values() if not path.is_file()
    ]
    missing.extend(
        validator.relative(path) for path in required_dirs if not path.is_dir()
    )
    validator.gate("required_artifacts", not missing, missing)

    parse_errors = []
    for path in sorted(root.rglob("*.json")):
        if path.resolve() == report_path.resolve():
            continue
        try:
            validator.load_json(path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            parse_errors.append(f"{validator.relative(path)}: {error}")
    for path in sorted(root.rglob("*.jsonl")):
        try:
            validator.load_jsonl(path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            parse_errors.append(f"{validator.relative(path)}: {error}")
    validator.gate("utf8_json_parse", not parse_errors, parse_errors)

    if missing or parse_errors:
        return finalize(validator, report_path)

    inventory_data = validator.load_json(required["inventory"])
    inventory_items = records(inventory_data, ("items", "anchors", "visuals"))
    inventory_errors = []
    inventory_ids = []
    semantic_items: dict[str, dict[str, Any]] = {}
    crop_paths: set[Path] = set()
    for index, item in enumerate(inventory_items, 1):
        unit_id = record_id(item)
        route = classification(item)
        if not unit_id:
            inventory_errors.append(f"item {index}: missing id")
            continue
        inventory_ids.append(unit_id)
        if route not in VALID_CLASSIFICATIONS:
            inventory_errors.append(f"{unit_id}: invalid or conflicting classification")
        if not valid_bbox(item.get("bbox")):
            inventory_errors.append(f"{unit_id}: invalid bbox")
        if route == "imagegen_asset":
            semantic_items[unit_id] = item
            if int(item.get("semantic_unit_count", 0)) != 1:
                inventory_errors.append(f"{unit_id}: semantic_unit_count must equal 1")
            crop_value = str(item.get("source_crop") or "").strip()
            if not crop_value:
                inventory_errors.append(f"{unit_id}: missing source_crop")
            else:
                crop_path = validator.resolve(crop_value)
                crop_paths.add(crop_path)
                if not crop_path.is_file():
                    inventory_errors.append(f"{unit_id}: missing crop {crop_value}")
    duplicates = sorted(
        unit_id for unit_id, count in Counter(inventory_ids).items() if count > 1
    )
    if duplicates:
        inventory_errors.append(f"duplicate ids: {duplicates}")
    validator.gate(
        "inventory_contract",
        bool(inventory_items) and not inventory_errors,
        inventory_errors,
    )

    prompt_files = sorted((root / "prompts").glob("assets_cycle_*.jsonl"))
    prompt_coverage: Counter[str] = Counter()
    prompt_crop_paths: set[Path] = set()
    prompt_errors = []
    for prompt_file in prompt_files:
        for row_index, row in enumerate(validator.load_jsonl(prompt_file), 1):
            if not isinstance(row, dict):
                prompt_errors.append(
                    f"{validator.relative(prompt_file)}:{row_index}: row is not an object"
                )
                continue
            ids = [str(value) for value in (row.get("source_anchor_ids") or [])]
            inputs = row.get("reference_inputs") or []
            full_refs = [
                entry
                for entry in inputs
                if isinstance(entry, dict) and entry.get("role") == "full_reference"
            ]
            object_crops = [
                entry
                for entry in inputs
                if isinstance(entry, dict) and entry.get("role") == "object_crop"
            ]
            if not full_refs:
                prompt_errors.append(
                    f"{validator.relative(prompt_file)}:{row_index}: missing full_reference input"
                )
            for entry in full_refs:
                path_value = str(entry.get("path") or "")
                path = validator.resolve(path_value) if path_value else Path()
                if not path_value or path != required["reference"].resolve():
                    prompt_errors.append(
                        f"{validator.relative(prompt_file)}:{row_index}: full_reference path mismatch"
                    )
                elif not entry.get("sha256") or str(entry["sha256"]).lower() != sha256(
                    path
                ):
                    prompt_errors.append(
                        f"{validator.relative(prompt_file)}:{row_index}: stale full_reference hash"
                    )
            crop_ids = Counter(
                str(entry.get("anchor_id") or "") for entry in object_crops
            )
            for unit_id in ids:
                prompt_coverage[unit_id] += 1
                if crop_ids[unit_id] != 1:
                    prompt_errors.append(
                        f"{validator.relative(prompt_file)}:{row_index}: {unit_id} needs one object crop"
                    )
            grid = row.get("grid") or {}
            if (
                int(grid.get("used_cells", -1)) != len(ids)
                or list(grid.get("ids") or []) != ids
            ):
                prompt_errors.append(
                    f"{validator.relative(prompt_file)}:{row_index}: grid ids/used_cells mismatch"
                )
            for entry in object_crops:
                path_value = str(entry.get("path") or "")
                if path_value:
                    path = validator.resolve(path_value)
                    prompt_crop_paths.add(path)
                    if (
                        not path.is_file()
                        or not entry.get("sha256")
                        or str(entry["sha256"]).lower() != sha256(path)
                    ):
                        prompt_errors.append(
                            f"{validator.relative(prompt_file)}:{row_index}: missing or stale crop hash: {path_value}"
                        )
    missing_prompt_ids = sorted(set(semantic_items) - set(prompt_coverage))
    unknown_prompt_ids = sorted(set(prompt_coverage) - set(semantic_items))
    if missing_prompt_ids:
        prompt_errors.append(
            f"semantic ids without prompt coverage: {missing_prompt_ids}"
        )
    if unknown_prompt_ids:
        prompt_errors.append(f"prompt ids absent from inventory: {unknown_prompt_ids}")
    validator.gate(
        "prompt_traceability",
        (bool(prompt_files) or not semantic_items) and not prompt_errors,
        prompt_errors,
    )

    match_files = sorted(root.glob("asset_match_cycle_*.json"))
    accepted_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    match_errors = []
    referenced_match_assets: set[Path] = set()
    for match_file in match_files:
        for item in records(validator.load_json(match_file), ("matches", "items")):
            unit_id = record_id(item)
            status = str(
                item.get("resolution_status") or item.get("status") or ""
            ).lower()
            if not unit_id or status not in {"accepted", "rejected", "unresolved"}:
                match_errors.append(
                    f"{validator.relative(match_file)}: invalid id or resolution_status"
                )
                continue
            if unit_id not in semantic_items:
                match_errors.append(
                    f"{validator.relative(match_file)}: stale or unknown semantic id: {unit_id}"
                )
            if status != "accepted":
                continue
            accepted_by_id[unit_id].append(item)
            if int(item.get("semantic_unit_count", 0)) != 1:
                match_errors.append(
                    f"{unit_id}: accepted match semantic_unit_count must equal 1"
                )
            qa = item.get("qa") if isinstance(item.get("qa"), dict) else {}
            failed_qa = sorted(
                key for key in REQUIRED_MATCH_QA if str(qa.get(key)).lower() != "pass"
            )
            if failed_qa:
                match_errors.append(
                    f"{unit_id}: accepted match has non-pass QA: {failed_qa}"
                )
            asset_value = str(
                item.get("asset_path")
                or item.get("assigned_asset")
                or item.get("path")
                or ""
            )
            if not asset_value:
                match_errors.append(f"{unit_id}: accepted match has no asset path")
            else:
                asset_path = validator.resolve(asset_value)
                referenced_match_assets.add(asset_path)
                if not asset_path.is_file():
                    match_errors.append(
                        f"{unit_id}: accepted asset missing: {asset_value}"
                    )
    for unit_id in sorted(semantic_items):
        count = len(accepted_by_id.get(unit_id, []))
        if count != 1:
            match_errors.append(
                f"{unit_id}: expected one accepted match, found {count}"
            )
    extra_accepted = sorted(set(accepted_by_id) - set(semantic_items))
    if extra_accepted:
        match_errors.append(f"accepted ids absent from inventory: {extra_accepted}")
    validator.gate(
        "accepted_match_traceability",
        (bool(match_files) or not semantic_items) and not match_errors,
        match_errors,
    )

    asset_data = validator.load_json(required["asset_manifest"])
    asset_items = records(asset_data, ("assets", "items"))
    asset_errors = []
    asset_ids = []
    asset_paths: dict[str, Path] = {}
    paths_to_items: dict[Path, list[dict[str, Any]]] = defaultdict(list)
    for item in asset_items:
        unit_id = record_id(item)
        asset_ids.append(unit_id)
        path_value = str(item.get("path") or item.get("asset_path") or "")
        if not unit_id or not path_value:
            asset_errors.append("asset manifest item missing semantic id or path")
            continue
        if int(item.get("semantic_unit_count", 0)) != 1:
            asset_errors.append(f"{unit_id}: semantic_unit_count must equal 1")
        source_type = str(item.get("source_type") or "")
        if source_type not in VALID_IMAGE_SOURCES:
            asset_errors.append(f"{unit_id}: invalid source_type: {source_type}")
        elif source_type == "user_asset":
            if not item.get("provenance") or not item.get("user_approval"):
                asset_errors.append(
                    f"{unit_id}: user asset needs provenance and user_approval"
                )
        elif not item.get("source_record") and not item.get("source_grid"):
            asset_errors.append(
                f"{unit_id}: generated asset needs source_record or source_grid"
            )
        path = validator.resolve(path_value)
        asset_paths[unit_id] = path
        paths_to_items[path].append(item)
        if not path.is_file():
            asset_errors.append(f"{unit_id}: missing asset {path_value}")
        elif not item.get("sha256") or str(item["sha256"]).lower() != sha256(path):
            asset_errors.append(f"{unit_id}: missing or stale asset sha256")
    if Counter(asset_ids) != Counter(semantic_items.keys()):
        asset_errors.append(
            "asset manifest semantic ids do not exactly match inventory imagegen ids"
        )
    for path, items in paths_to_items.items():
        if len(items) <= 1:
            continue
        groups = {str(item.get("reuse_group") or "") for item in items}
        if "" in groups or len(groups) != 1:
            asset_errors.append(
                f"asset path reused without one explicit reuse_group: {validator.relative(path)}"
            )
    for unit_id, accepted_items in accepted_by_id.items():
        if not accepted_items or unit_id not in asset_paths:
            continue
        accepted_value = str(
            accepted_items[0].get("asset_path")
            or accepted_items[0].get("assigned_asset")
            or accepted_items[0].get("path")
            or ""
        )
        if accepted_value and validator.resolve(accepted_value) != asset_paths[unit_id]:
            asset_errors.append(
                f"{unit_id}: accepted match and asset manifest paths disagree"
            )
    validator.gate(
        "asset_manifest_traceability",
        (bool(asset_items) or not semantic_items) and not asset_errors,
        asset_errors,
    )

    actual_assets = {path.resolve() for path in (root / "assets").rglob("*.png")}
    declared_assets = set(asset_paths.values())
    asset_cleanliness = {
        "unreferenced": sorted(
            validator.relative(path) for path in actual_assets - declared_assets
        ),
        "missing": sorted(
            validator.relative(path) for path in declared_assets - actual_assets
        ),
    }
    validator.gate(
        "asset_directory_clean", not any(asset_cleanliness.values()), asset_cleanliness
    )

    actual_crops = {
        path.resolve() for path in (root / "reference_crops").rglob("*.png")
    }
    referenced_crops = crop_paths | prompt_crop_paths
    crop_cleanliness = {
        "unreferenced": sorted(
            validator.relative(path) for path in actual_crops - referenced_crops
        ),
        "missing": sorted(
            validator.relative(path) for path in referenced_crops - actual_crops
        ),
    }
    validator.gate(
        "crop_directory_clean", not any(crop_cleanliness.values()), crop_cleanliness
    )

    generated_root = (root / "generated").resolve()
    referenced_generated: set[Path] = set()
    queue: list[Path] = []
    for data in (asset_data, *[validator.load_json(path) for path in match_files]):
        queue.extend(validator.resolve(value) for value in extract_path_values(data))
    while queue:
        path = queue.pop().resolve()
        if path in referenced_generated or generated_root not in path.parents:
            continue
        referenced_generated.add(path)
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl"}:
            continue
        data = (
            validator.load_json(path)
            if path.suffix.lower() == ".json"
            else validator.load_jsonl(path)
        )
        queue.extend(validator.resolve(value) for value in extract_path_values(data))
    actual_generated = {
        path.resolve() for path in (root / "generated").rglob("*") if path.is_file()
    }
    generated_unreferenced = sorted(
        validator.relative(path) for path in actual_generated - referenced_generated
    )
    validator.gate(
        "generated_files_referenced", not generated_unreferenced, generated_unreferenced
    )

    layout_data = validator.load_json(required["layout_manifest"])
    layout_items = records(layout_data, ("elements", "items"))
    layout_errors = []
    layout_element_ids = []
    layout_picture_ids = []
    structural_arrow_count = 0
    for item in layout_items:
        element_id = str(item.get("id") or "")
        layout_element_ids.append(element_id)
        element_type = str(item.get("type") or "")
        if not element_id:
            layout_errors.append("layout element missing id")
        if element_type == "image":
            unit_id = str(item.get("semantic_unit_id") or "")
            layout_picture_ids.append(unit_id)
            if not unit_id or int(item.get("semantic_unit_count", 0)) != 1:
                layout_errors.append(f"{element_id}: image semantic metadata missing")
            if str(item.get("source_type") or "") not in VALID_IMAGE_SOURCES:
                layout_errors.append(f"{element_id}: invalid image source_type")
            if str(item.get("scaling") or "") != "uniform_contain" or not valid_bbox(
                item.get("fitted_bbox")
            ):
                layout_errors.append(
                    f"{element_id}: missing uniform contain fitted_bbox"
                )
        if element_type == "line" and str(item.get("purpose")) == "structural_arrow":
            structural_arrow_count += 1
            if not item.get("begin_arrow") and not item.get("end_arrow"):
                layout_errors.append(
                    f"{element_id}: structural arrow has no native arrowhead metadata"
                )
        if (
            element_type in {"right_arrow", "down_arrow"}
            and item.get("block_arrow_reference") is not True
        ):
            layout_errors.append(
                f"{element_id}: block arrow lacks block_arrow_reference"
            )
    duplicate_layout_ids = sorted(
        value
        for value, count in Counter(layout_element_ids).items()
        if count > 1 or not value
    )
    if duplicate_layout_ids:
        layout_errors.append(f"invalid or duplicate layout ids: {duplicate_layout_ids}")
    if Counter(layout_picture_ids) != Counter(semantic_items.keys()):
        layout_errors.append(
            "layout picture semantic ids do not exactly match inventory imagegen ids"
        )
    validator.gate(
        "layout_manifest_traceability",
        bool(layout_items) and not layout_errors,
        layout_errors,
    )

    redbox_files = sorted(root.glob("residual_cycle_*_redboxes.json"), key=cycle_number)
    residual_errors = []
    if not redbox_files:
        residual_errors.append("no residual red-box files")
    else:
        for redbox_file in redbox_files:
            redbox_data = validator.load_json(redbox_file)
            cycle_items = records(redbox_data, ("unresolved", "redboxes", "items"))
            stale_ids = sorted(
                {record_id(item) for item in cycle_items} - set(semantic_items)
            )
            if stale_ids:
                residual_errors.append(
                    f"{validator.relative(redbox_file)} has stale ids: {stale_ids}"
                )
        final_redboxes = validator.load_json(redbox_files[-1])
        unresolved = records(final_redboxes, ("unresolved", "redboxes", "items"))
        declared_count = (
            final_redboxes.get("unresolved_semantic_visuals")
            if isinstance(final_redboxes, dict)
            else None
        )
        if declared_count is None or int(declared_count) != len(unresolved):
            residual_errors.append(
                "final residual red-box count is missing or inconsistent"
            )
        if unresolved:
            residual_errors.append(
                f"final residual still has unresolved ids: {[record_id(item) for item in unresolved]}"
            )
    validator.gate("residual_coverage_closed", not residual_errors, residual_errors)

    visual_review = validator.load_json(required["visual_review"])
    review_errors = []
    if not isinstance(visual_review, dict) or str(
        visual_review.get("status")
    ).lower() not in {"pass", "passed"}:
        review_errors.append("visual review status is not passed")
    checks = visual_review.get("checks") if isinstance(visual_review, dict) else {}
    if not isinstance(checks, dict):
        checks = {}
    for name in sorted(REQUIRED_VISUAL_CHECKS):
        if str(checks.get(name)).lower() != "pass":
            review_errors.append(f"visual check is not pass: {name}")
    review_files = visual_review.get("files") if isinstance(visual_review, dict) else {}
    if not isinstance(review_files, dict):
        review_files = {}
    resolved_review_files: dict[str, Path] = {}
    for name in sorted(REQUIRED_HASH_FILES):
        entry = review_files.get(name)
        if (
            not isinstance(entry, dict)
            or not entry.get("path")
            or not entry.get("sha256")
        ):
            review_errors.append(f"missing review file hash record: {name}")
            continue
        path = validator.resolve(str(entry["path"]))
        resolved_review_files[name] = path
        if not path.is_file():
            review_errors.append(f"review file missing: {name} -> {entry['path']}")
        elif sha256(path).lower() != str(entry["sha256"]).lower():
            review_errors.append(f"stale review hash: {name}")
    expected_paths = {
        "reference": required["reference"].resolve(),
        "asset_manifest": required["asset_manifest"].resolve(),
        "layout_manifest": required["layout_manifest"].resolve(),
    }
    for name, expected in expected_paths.items():
        if resolved_review_files.get(name) != expected:
            review_errors.append(
                f"review {name} path does not target the required artifact"
            )
    validator.gate("current_visual_review", not review_errors, review_errors)

    pptx_path = resolved_review_files.get("pptx")
    pptx_errors = []
    ppt_evidence: dict[str, Any] = {}
    if not pptx_path or not pptx_path.is_file():
        pptx_errors.append("current PPTX is unavailable")
    else:
        try:
            ppt_evidence = pptx_evidence(pptx_path)
        except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as error:
            pptx_errors.append(f"PPTX package parse failed: {error}")
        else:
            if Counter(ppt_evidence["picture_semantic_ids"]) != Counter(
                layout_picture_ids
            ):
                pptx_errors.append(
                    "PPTX picture semantic metadata does not match layout manifest"
                )
            if ppt_evidence["triangle_shapes"]:
                pptx_errors.append(
                    f"PPTX contains forbidden triangle shapes: {ppt_evidence['triangle_shapes']}"
                )
            if ppt_evidence["native_arrowhead_count"] < structural_arrow_count:
                pptx_errors.append(
                    "PPTX has fewer native arrowheads than structural arrows"
                )
            reference_hash = sha256(required["reference"])
            if reference_hash in ppt_evidence["media_hashes"]:
                pptx_errors.append("reference bitmap is embedded in PPTX media")
            with Image.open(required["reference"]) as reference_image:
                reference_pixel_hash = image_pixel_sha256(reference_image)
            if reference_pixel_hash in ppt_evidence["media_pixel_hashes"]:
                pptx_errors.append(
                    "a re-encoded copy of the reference bitmap is embedded in PPTX media"
                )
    validator.gate("pptx_package_and_metadata", not pptx_errors, pptx_errors)

    stale_files = []
    for pattern in (
        "qa*.txt",
        "*qa*.txt",
        "validation*.txt",
        "*.py",
        "*.ps1",
        "*.js",
        "*.mjs",
    ):
        stale_files.extend(path for path in root.rglob(pattern) if path.is_file())
    stale_names = sorted({validator.relative(path) for path in stale_files})
    validator.gate("no_stale_qa_or_temporary_scripts", not stale_names, stale_names)

    return finalize(validator, report_path, ppt_evidence)


def finalize(
    validator: Validator, report_path: Path, ppt_evidence: dict[str, Any] | None = None
) -> dict[str, Any]:
    report = {
        "status": "passed" if not validator.failures else "failed",
        "root": str(validator.root),
        "gates": validator.gates,
        "failures": validator.failures,
        "pptx_evidence": ppt_evidence or {},
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a PPT visual-replica delivery with fail-closed gates."
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    report_path = (
        args.report.resolve() if args.report else root / "validation_report.json"
    )
    report = validate(root, report_path)
    print(json.dumps(report, ensure_ascii=False))
    if report["status"] != "passed":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
