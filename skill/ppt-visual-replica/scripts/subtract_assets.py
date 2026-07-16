#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


VALID_STATUSES = {"accepted", "rejected", "unresolved"}
REQUIRED_QA = {
    "identity",
    "isolation",
    "border_integrity",
    "alpha_or_chroma",
    "style_fidelity",
}


def load_items(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        return data
    for key in ("items", "matches", "redboxes"):
        if isinstance(data.get(key), list):
            return data[key]
    raise ValueError("matches JSON must be a list or contain items/matches/redboxes")


def semantic_id(item: dict[str, Any], index: int) -> str:
    value = item.get("semantic_unit_id") or item.get("anchor_id") or item.get("id")
    if not value:
        raise ValueError(f"match {index} is missing semantic_unit_id/anchor_id/id")
    return str(value)


def bbox(item: dict[str, Any], semantic_unit_id: str) -> list[int]:
    raw = item.get("bbox") or item.get("anchor_slot")
    if not isinstance(raw, list) or len(raw) != 4:
        raise ValueError(f"{semantic_unit_id}: bbox must be [x, y, w, h]")
    values = [int(round(float(value))) for value in raw]
    if values[2] <= 0 or values[3] <= 0:
        raise ValueError(f"{semantic_unit_id}: bbox width and height must be positive")
    return values


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_asset(path_value: str, matches_path: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = matches_path.parent / path
    return path.resolve()


def validate_accepted(
    item: dict[str, Any], semantic_unit_id: str, matches_path: Path
) -> Path:
    if int(item.get("semantic_unit_count", 0)) != 1:
        raise ValueError(
            f"{semantic_unit_id}: accepted match must declare semantic_unit_count: 1"
        )
    qa = item.get("qa")
    if not isinstance(qa, dict):
        raise ValueError(f"{semantic_unit_id}: accepted match is missing qa")
    missing = sorted(REQUIRED_QA - set(qa))
    if missing:
        raise ValueError(
            f"{semantic_unit_id}: accepted match is missing QA gates: {missing}"
        )
    failed = sorted(key for key in REQUIRED_QA if str(qa.get(key)).lower() != "pass")
    if failed:
        raise ValueError(
            f"{semantic_unit_id}: accepted match has non-pass QA gates: {failed}"
        )
    path_value = str(
        item.get("asset_path") or item.get("assigned_asset") or item.get("path") or ""
    ).strip()
    if not path_value:
        raise ValueError(f"{semantic_unit_id}: accepted match is missing asset_path")
    asset_path = resolve_asset(path_value, matches_path)
    if not asset_path.is_file():
        raise FileNotFoundError(
            f"{semantic_unit_id}: accepted asset not found: {path_value}"
        )
    return asset_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a residual by subtracting QA-accepted semantic anchors only."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--input",
        dest="input_image",
        type=Path,
        help="Current residual image for this cycle.",
    )
    source_group.add_argument(
        "--reference", dest="input_image", type=Path, help="Legacy alias for --input."
    )
    parser.add_argument("--matches", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--mask-out", type=Path)
    parser.add_argument("--report-out", type=Path)
    parser.add_argument("--fill", default="#FFFFFF")
    args = parser.parse_args()

    image = Image.open(args.input_image).convert("RGB")
    mask = Image.new("RGB", image.size, "black")
    image_draw = ImageDraw.Draw(image)
    mask_draw = ImageDraw.Draw(mask)

    accepted = []
    skipped = []
    seen_ids: set[str] = set()
    for index, item in enumerate(load_items(args.matches), 1):
        unit_id = semantic_id(item, index)
        if unit_id in seen_ids:
            raise ValueError(f"duplicate match id: {unit_id}")
        seen_ids.add(unit_id)
        status = (
            str(item.get("resolution_status") or item.get("status") or "")
            .strip()
            .lower()
        )
        if status not in VALID_STATUSES:
            raise ValueError(
                f"{unit_id}: resolution_status must be accepted, rejected, or unresolved"
            )
        box = bbox(item, unit_id)
        x, y, width, height = box
        if x < 0 or y < 0 or x + width > image.width or y + height > image.height:
            raise ValueError(f"{unit_id}: bbox is outside the current residual")
        if status != "accepted":
            skipped.append(
                {"semantic_unit_id": unit_id, "resolution_status": status, "bbox": box}
            )
            continue

        asset_path = validate_accepted(item, unit_id, args.matches)
        rectangle = [x, y, x + width - 1, y + height - 1]
        image_draw.rectangle(rectangle, fill=args.fill)
        mask_draw.rectangle(rectangle, fill="white")
        accepted.append(
            {
                "semantic_unit_id": unit_id,
                "resolution_status": "accepted",
                "bbox": box,
                "asset_path": str(asset_path),
                "asset_sha256": sha256(asset_path),
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out)
    if args.mask_out:
        args.mask_out.parent.mkdir(parents=True, exist_ok=True)
        mask.save(args.mask_out)

    report = {
        "status": "passed",
        "input": str(args.input_image),
        "input_sha256": sha256(args.input_image),
        "matches": str(args.matches),
        "accepted_count": len(accepted),
        "remaining_count": len(skipped),
        "accepted": accepted,
        "remaining": skipped,
        "out": str(args.out),
        "out_sha256": sha256(args.out),
    }
    if args.report_out:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
