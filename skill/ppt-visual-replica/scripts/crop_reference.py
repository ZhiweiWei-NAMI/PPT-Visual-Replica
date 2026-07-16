#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image


def load_boxes(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        return data
    for key in ("items", "anchors", "boxes", "redboxes"):
        if isinstance(data.get(key), list):
            return data[key]
    raise ValueError(
        "boxes JSON must be a list or contain items/anchors/boxes/redboxes"
    )


def bbox(item: dict[str, Any], anchor_id: str) -> tuple[int, int, int, int]:
    raw = item.get("bbox")
    if isinstance(raw, list) and len(raw) == 4:
        result = tuple(int(round(float(v))) for v in raw)
    else:
        try:
            result = tuple(int(round(float(item[k]))) for k in ("x", "y", "w", "h"))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{anchor_id}: bbox must be [x, y, w, h]") from error
    if result[2] <= 0 or result[3] <= 0:
        raise ValueError(f"{anchor_id}: bbox width and height must be positive")
    return result  # type: ignore[return-value]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crop reference/residual image anchors."
    )
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--boxes", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--manifest-out", type=Path)
    parser.add_argument("--pad", type=int, default=0)
    args = parser.parse_args()

    image = Image.open(args.image).convert("RGBA")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    seen_ids: set[str] = set()
    for idx, item in enumerate(load_boxes(args.boxes), 1):
        anchor_id = str(item.get("anchor_id") or item.get("id") or f"anchor_{idx:03d}")
        if anchor_id in seen_ids:
            raise ValueError(f"duplicate anchor id: {anchor_id}")
        seen_ids.add(anchor_id)
        if (
            item.get("semantic_unit_count") is not None
            and int(item["semantic_unit_count"]) != 1
        ):
            raise ValueError(f"{anchor_id}: semantic_unit_count must equal 1")
        x, y, w, h = bbox(item, anchor_id)
        if x < 0 or y < 0 or x + w > image.width or y + h > image.height:
            raise ValueError(f"{anchor_id}: bbox is outside the source image")
        left = max(0, x - args.pad)
        top = max(0, y - args.pad)
        right = min(image.width, x + w + args.pad)
        bottom = min(image.height, y + h + args.pad)
        out = args.out_dir / f"{anchor_id}.png"
        image.crop((left, top, right, bottom)).save(out)
        records.append(
            {
                "anchor_id": anchor_id,
                "semantic_unit_id": anchor_id,
                "semantic_unit_count": 1,
                "crop_role": "exact_anchor" if args.pad == 0 else "context_crop",
                "source_bbox": [x, y, w, h],
                "crop_bbox": [left, top, right - left, bottom - top],
                "path": str(out),
            }
        )
    if args.manifest_out:
        args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_out.write_text(
            json.dumps({"crops": records}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(
        json.dumps(
            {"count": len(records), "out_dir": str(args.out_dir)}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
