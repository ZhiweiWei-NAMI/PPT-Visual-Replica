#!/usr/bin/env python
"""Render reference/candidate asset pairs without implying approval.

Based on the asset wall contributed in PR #2. Review decisions belong to the
reviewer; this tool checks file availability and preserves content-bound records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

IMAGE_ROLES = {
    "imagegen_asset", "api_generated_asset", "provided_asset", "user_asset",
    "generated_scene_background", "openai_image", "gemini_image", "image",
}
NATIVE_ROLES = {"text", "layout_native", "native", "native_shape"}
DECISIONS = {"needs_review", "approved", "rejected"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_assets(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, dict):
        data = next((data[k] for k in
                     ("assets", "minimum_semantic_units", "items", "anchors", "visuals")
                     if isinstance(data.get(k), list)), None)
    if not isinstance(data, list) or any(not isinstance(x, dict) for x in data):
        raise ValueError("input must be a list of objects or an assets/items inventory")
    return data


def asset_id(item: dict[str, Any]) -> str:
    value = next((item[k] for k in
                  ("asset_id", "semantic_unit_id", "id", "anchor_id") if item.get(k)), None)
    if value is None:
        raise ValueError("each reviewed item needs an explicit stable ID")
    return str(value)


def asset_role(item: dict[str, Any]) -> str:
    return str(item.get("role") or item.get("classification")
               or item.get("route") or item.get("source_type") or "")


def index_assets(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for item in items:
        role = asset_role(item)
        if role in NATIVE_ROLES:
            continue
        if role not in IMAGE_ROLES and not item.get("path") and not item.get("asset_path"):
            raise ValueError("image inventory item needs an image role or asset path")
        key = asset_id(item)
        if key in result:
            raise ValueError(f"duplicate asset ID: {key}")
        result[key] = item
    return result


def resolve_path(root: Path, value: Any) -> Path | None:
    if not value:
        return None
    # Portable relative paths from older Windows manifests.
    path = Path(str(value).replace("\\", "/"))
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def relative(path: Path | None, base: Path) -> str:
    if path is None:
        return ""
    try:
        return Path(os.path.relpath(path, base)).as_posix()
    except ValueError as exc:
        raise ValueError("review inputs and outputs must be on the same volume") from exc


def load_image(path: Path | None) -> tuple[Image.Image | None, str, str]:
    if path is None or not path.is_file():
        return None, "missing", ""
    try:
        with Image.open(path) as source:
            image = source.convert("RGBA")
            image.load()
        return image, "available", ""
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        return None, "error", str(exc)


def image_hash(image: Image.Image | None) -> str | None:
    if image is None:
        return None
    digest = hashlib.sha256()
    digest.update(str(image.size).encode("ascii"))
    digest.update(image.tobytes())
    return digest.hexdigest()


def reference_image(item: dict[str, Any], root: Path,
                    reference: Path | None) -> tuple[Image.Image | None, str, str]:
    if item.get("source_crop"):
        return load_image(resolve_path(root, item["source_crop"]))
    bbox = item.get("bbox", item.get("bbox_px"))
    if reference is None or bbox is None:
        return None, "not_supplied", ""
    image, state, error = load_image(reference)
    if image is None:
        return None, state, error
    try:
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError("bbox must be [x, y, width, height]")
        x, y, width, height = map(float, bbox)
        if not all(math.isfinite(v) for v in (x, y, width, height)):
            raise ValueError("bbox contains a non-finite value")
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            raise ValueError("bbox must have nonnegative origin and positive size")
        if x + width > image.width or y + height > image.height:
            raise ValueError("bbox extends beyond the reference")
        return image.crop((math.floor(x), math.floor(y),
                           math.ceil(x + width), math.ceil(y + height))), "available", ""
    except (TypeError, ValueError) as exc:
        return None, "error", str(exc)


def wrapped(draw: ImageDraw.ImageDraw, text: str, font: Any, width: int) -> list[str]:
    lines, current = [], ""
    for char in text:
        if char == "\n" or (current and draw.textlength(current + char, font=font) > width):
            lines.append(current)
            current = "" if char == "\n" else char
        else:
            current += char
    lines.append(current)
    return lines


def paint_image(wall: Image.Image, image: Image.Image | None, xy: tuple[int, int],
                size: int, label: str, font: Any) -> None:
    pane = Image.new("RGBA", (size, size), (248, 249, 250, 255))
    draw = ImageDraw.Draw(pane)
    for y in range(0, size, 12):
        for x in range(0, size, 12):
            if (x // 12 + y // 12) % 2 == 0:
                draw.rectangle((x, y, x + 11, y + 11), fill=(218, 222, 228, 255))
    if image is None:
        draw.rectangle((0, 0, size - 1, size - 1), outline=(190, 45, 45), width=2)
        draw.text((8, 8), label, fill=(140, 30, 30), font=font)
    else:
        thumb = ImageOps.contain(image, (size - 8, size - 8), Image.Resampling.LANCZOS)
        pane.alpha_composite(thumb, ((size - thumb.width) // 2, (size - thumb.height) // 2))
    wall.paste(pane.convert("RGB"), xy)


def generate_review(assets_path: Path, root: Path, wall_out: Path, review_out: Path,
                    inventory_path: Path | None = None, reference: Path | None = None,
                    path_map: dict[str, str] | None = None, columns: int = 3,
                    cell_size: int = 180, font_path: Path | None = None) -> dict[str, Any]:
    if columns < 1 or cell_size < 96:
        raise ValueError("columns must be positive and cell-size at least 96")
    root, wall_out, review_out = root.resolve(), wall_out.resolve(), review_out.resolve()
    candidates = index_assets(load_assets(assets_path))
    expected = index_assets(load_assets(inventory_path)) if inventory_path else {}
    keys = list(expected) + [key for key in candidates if key not in expected]
    if not keys:
        raise ValueError("no reviewable image assets found")
    mapping = path_map or {}
    if not isinstance(mapping, dict) or any(
        not isinstance(k, str) or not isinstance(v, str) for k, v in mapping.items()
    ):
        raise ValueError("path-map must map exact source path strings to path strings")
    old = read_json(review_out) if review_out.is_file() else {}
    if not isinstance(old, dict) or not isinstance(old.get("assets", []), list):
        raise ValueError("invalid existing review; refusing to overwrite")
    prior = {}
    for row in old.get("assets", []):
        key = str(row["asset_id"])
        if key in prior:
            raise ValueError("existing review has duplicate IDs")
        prior[key] = row
    font = ImageFont.truetype(str(font_path), 14) if font_path else ImageFont.load_default()
    records, pictures = [], []
    protected = {assets_path.resolve()}
    if inventory_path:
        protected.add(inventory_path.resolve())
    if reference:
        protected.add(reference.resolve())
    for key in keys:
        item = candidates.get(key)
        context = {**(item or {}), **expected.get(key, {})}
        original_path = (item.get("path") or item.get("asset_path")) if item else None
        candidate_path = resolve_path(root, mapping.get(str(original_path), original_path))
        if candidate_path:
            protected.add(candidate_path)
        crop_path = resolve_path(root, context.get("source_crop"))
        if crop_path:
            protected.add(crop_path)
        candidate, availability, error = load_image(candidate_path)
        ref_image, ref_state, ref_error = reference_image(context, root, reference)
        signature = {
            "asset_sha256": image_hash(candidate),
            "reference_sha256": image_hash(ref_image),
            "reference_status": ref_state,
            "in_inventory": key in expected if inventory_path else None,
        }
        fingerprint = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
        previous = prior.get(key, {})
        unchanged = (previous.get("fingerprint") == fingerprint
                     and availability == "available" and ref_state not in {"missing", "error"})
        decision = previous.get("review_status", "needs_review") if unchanged else "needs_review"
        if decision not in DECISIONS:
            decision = "needs_review"
        row = {
            "asset_id": key, "role": asset_role(context),
            "path": relative(candidate_path, review_out.parent),
            "source_path": str(original_path or ""),
            "availability": availability, "error": error,
            "reference_status": ref_state, "reference_error": ref_error,
            **signature, "fingerprint": fingerprint,
            "review_status": decision,
            "notes": str(previous.get("notes", "")),
        }
        if unchanged:
            for field in ("reviewer", "reviewed_at", "action", "previous_review"):
                if field in previous:
                    row[field] = previous[field]
        elif previous:
            row["previous_review"] = {
                field: previous[field] for field in
                ("review_status", "reviewer", "reviewed_at", "action", "fingerprint")
                if field in previous
            }
            row["review_invalidated"] = True
        records.append(row)
        pictures.append((ref_image, candidate))
    if wall_out == review_out or wall_out in protected or review_out in protected:
        raise ValueError("output paths must not overwrite inputs or each other")
    # Size labels to keep long IDs readable instead of silently clipping them.
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    card_w, gap, padding = 2 * cell_size + 36, 16, 20
    labels = [wrapped(probe, row["asset_id"], font, card_w - 24) for row in records]
    label_lines = max(len(lines) for lines in labels)
    card_h = cell_size + 76 + label_lines * 18
    cols = min(columns, len(keys))
    rows = math.ceil(len(keys) / cols)
    width, height = 2 * padding + cols * (card_w + gap) - gap, 2 * padding + rows * (card_h + gap) - gap
    if width * height > 80_000_000:
        raise ValueError("wall too large; split the manifest into smaller review batches")
    wall = Image.new("RGB", (width, height), (245, 247, 250))
    draw = ImageDraw.Draw(wall)
    for index, (row, pair) in enumerate(zip(records, pictures)):
        x = padding + index % cols * (card_w + gap)
        y = padding + index // cols * (card_h + gap)
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=6,
                               fill="white", outline=(205, 210, 218))
        draw.text((x + 12, y + 10), "Reference", font=font, fill="black")
        draw.text((x + cell_size + 24, y + 10), "Candidate", font=font, fill="black")
        paint_image(wall, pair[0], (x + 12, y + 30), cell_size, row["reference_status"], font)
        paint_image(wall, pair[1], (x + cell_size + 24, y + 30), cell_size, row["availability"], font)
        for offset, line in enumerate(labels[index]):
            draw.text((x + 12, y + cell_size + 38 + offset * 18), line, font=font, fill="black")
        label = f'{row["availability"]} / {row["review_status"]}'
        draw.text((x + 12, y + card_h - 23), label, font=font, fill=(75, 80, 90))
    issues = [r["asset_id"] for r in records if r["availability"] != "available"
              or r["reference_status"] in {"missing", "error"}]
    review = {
        "schema_version": 2,
        "asset_review_wall": relative(wall_out, review_out.parent),
        "source": relative(assets_path.resolve(), review_out.parent),
        "inventory": relative(inventory_path.resolve(), review_out.parent) if inventory_path else None,
        "reference": relative(reference.resolve(), review_out.parent) if reference else None,
        "paths_relative_to": "this review JSON",
        "instructions": "Compare reference and candidate, including lost color details. "
                        "Record agent or user decisions explicitly. Rendering this wall is not approval.",
        "coverage": {
            "inventory_supplied": inventory_path is not None,
            "missing_asset_ids": [k for k in expected if k not in candidates],
            "unlisted_asset_ids": [k for k in candidates if inventory_path and k not in expected],
            "limitation": "Coverage is relative to the supplied inventory; inspect the full reference "
                          "to find elements omitted from both inputs.",
        },
        "integrity": {"status": "failed" if issues else "passed", "problem_asset_ids": issues},
        "assets": records,
    }
    wall_out.parent.mkdir(parents=True, exist_ok=True)
    review_out.parent.mkdir(parents=True, exist_ok=True)
    wall.save(wall_out)
    review_out.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return review


def main() -> None:
    parser = argparse.ArgumentParser(description="Create optional reference/candidate asset review pairs.")
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--root", type=Path, help="base for all input asset and crop paths")
    parser.add_argument("--inventory", type=Path, help="expected image objects, matched by stable ID")
    parser.add_argument("--reference", type=Path, help="reference image for inventory bbox crops")
    parser.add_argument("--path-map", type=Path, help="JSON mapping exact manifest paths to actual paths")
    parser.add_argument("--wall-out", required=True, type=Path)
    parser.add_argument("--review-out", required=True, type=Path)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--cell-size", type=int, default=180)
    parser.add_argument("--font", type=Path, help="font supporting the labels' language")
    parser.add_argument("--require-reviewed", action="store_true",
                        help="exit nonzero unless all assets have explicit approval; opt-in only")
    args = parser.parse_args()
    try:
        review = generate_review(
            args.assets, args.root or args.assets.parent, args.wall_out, args.review_out,
            args.inventory, args.reference, read_json(args.path_map) if args.path_map else None,
            args.columns, args.cell_size, args.font,
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"asset review failed: {exc}\n")
    print(json.dumps({
        "assets": len(review["assets"]), "wall": str(args.wall_out),
        "review": str(args.review_out), "integrity": review["integrity"],
    }, ensure_ascii=False))
    if review["integrity"]["status"] != "passed":
        raise SystemExit(2)
    if args.require_reviewed and any(
        r["review_status"] != "approved" for r in review["assets"]
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
