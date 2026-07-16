#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_color(value: str) -> tuple[int, int, int]:
    value = value.strip()
    if value.startswith("#"):
        value = value[1:]
        if len(value) != 6:
            raise ValueError("hex background color must contain six digits")
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 3 or any(part < 0 or part > 255 for part in parts):
        raise ValueError("background color must be #RRGGBB or r,g,b")
    return parts[0], parts[1], parts[2]


def color_distance(pixel: tuple[int, int, int], key: tuple[int, int, int]) -> float:
    return math.sqrt(sum((pixel[index] - key[index]) ** 2 for index in range(3)))


def is_key_pixel(
    pixel: tuple[int, int, int],
    key: tuple[int, int, int],
    tolerance: int,
    dominance: int,
) -> bool:
    if color_distance(pixel, key) <= tolerance:
        return True
    dominant_channel = max(range(3), key=lambda index: key[index])
    other_channels = [index for index in range(3) if index != dominant_channel]
    if key[dominant_channel] - max(key[index] for index in other_channels) < 80:
        return False
    return (
        pixel[dominant_channel] > 120
        and pixel[dominant_channel] - max(pixel[index] for index in other_channels)
        >= dominance
    )


def remove_background(
    image: Image.Image,
    key: tuple[int, int, int],
    tolerance: int,
    dominance: int,
) -> Image.Image:
    output = image.convert("RGBA")
    pixels = output.load()
    for y in range(output.height):
        for x in range(output.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha and is_key_pixel((red, green, blue), key, tolerance, dominance):
                pixels[x, y] = (red, green, blue, 0)
    return output


def boundary_key_ratio(
    image: Image.Image,
    key: tuple[int, int, int],
    tolerance: int,
    dominance: int,
) -> tuple[int, int, float]:
    pixels = image.load()
    boundary_count = 0
    suspicious_count = 0
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            neighbours = ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
            if not any(
                nx < 0
                or ny < 0
                or nx >= image.width
                or ny >= image.height
                or pixels[nx, ny][3] == 0
                for nx, ny in neighbours
            ):
                continue
            boundary_count += 1
            if is_key_pixel(
                (red, green, blue), key, tolerance + 20, max(5, dominance // 2)
            ):
                suspicious_count += 1
    ratio = suspicious_count / boundary_count if boundary_count else 0.0
    return suspicious_count, boundary_count, ratio


def trim_with_padding(image: Image.Image, padding: int) -> Image.Image:
    alpha_bbox = image.getchannel("A").getbbox()
    if alpha_bbox is None:
        return image
    trimmed = image.crop(alpha_bbox)
    if padding <= 0:
        return trimmed
    output = Image.new(
        "RGBA",
        (trimmed.width + padding * 2, trimmed.height + padding * 2),
        (0, 0, 0, 0),
    )
    output.alpha_composite(trimmed, (padding, padding))
    return output


def load_spec(
    path: Path | None, rows: int, cols: int, margin: int, gap: int, ids: list[str]
) -> dict[str, Any]:
    if path:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        "rows": rows,
        "cols": cols,
        "margin": margin,
        "gap": gap,
        "ids": ids,
        "used_cells": len(ids) or rows * cols,
    }


def cells_from_spec(
    spec: dict[str, Any], width: int, height: int
) -> list[dict[str, Any]]:
    if isinstance(spec.get("cells"), list):
        cells = list(spec["cells"])
        used = int(spec.get("used_cells", len(cells)))
        if used < 0 or used > len(cells):
            raise ValueError("used_cells is outside the explicit cells list")
        return cells[:used]

    rows = int(spec["rows"])
    cols = int(spec["cols"])
    margin = int(spec.get("margin", 0))
    gap = int(spec.get("gap", 0))
    ids = [str(value) for value in (spec.get("ids") or [])]
    used = int(spec.get("used_cells", len(ids) or rows * cols))
    if rows < 1 or cols < 1 or used < 1 or used > rows * cols:
        raise ValueError("grid rows, cols, and used_cells are inconsistent")
    if ids and len(ids) != used:
        raise ValueError("ids length must equal used_cells")
    available_width = width - margin * 2 - gap * (cols - 1)
    available_height = height - margin * 2 - gap * (rows - 1)
    if available_width <= 0 or available_height <= 0:
        raise ValueError("grid margin/gap leaves no cell area")
    cell_width = available_width / cols
    cell_height = available_height / rows
    cells = []
    for index in range(used):
        row = index // cols
        column = index % cols
        cells.append(
            {
                "id": ids[index] if ids else f"cell_{index + 1:03d}",
                "bbox": [
                    round(margin + column * (cell_width + gap)),
                    round(margin + row * (cell_height + gap)),
                    round(cell_width),
                    round(cell_height),
                ],
            }
        )
    return cells


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cut declared asset-grid cells and emit technical QA evidence."
    )
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--manifest-out", type=Path)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--rows", type=int, default=1)
    parser.add_argument("--cols", type=int, default=1)
    parser.add_argument("--margin", type=int, default=0)
    parser.add_argument("--gap", type=int, default=0)
    parser.add_argument("--ids", nargs="*", default=[])
    parser.add_argument("--background", default="#00FF00")
    parser.add_argument("--tolerance", type=int, default=45)
    parser.add_argument("--dominance", type=int, default=35)
    parser.add_argument("--trim-padding", type=int, default=4)
    parser.add_argument("--border-guard", type=int, default=2)
    parser.add_argument("--max-boundary-key-ratio", type=float, default=0.05)
    parser.add_argument("--allow-border-touch", action="store_true")
    parser.add_argument("--allow-key-residue", action="store_true")
    args = parser.parse_args()

    if args.trim_padding < 0 or args.border_guard < 0:
        raise ValueError("trim-padding and border-guard must be non-negative")
    if not 0 <= args.max_boundary_key_ratio <= 1:
        raise ValueError("max-boundary-key-ratio must be between 0 and 1")

    source = Image.open(args.image).convert("RGBA")
    spec = load_spec(args.spec, args.rows, args.cols, args.margin, args.gap, args.ids)
    key = parse_color(str(spec.get("background") or args.background))
    cells = cells_from_spec(spec, source.width, source.height)
    ids = [str(cell.get("id") or "") for cell in cells]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError("every used cell must have a unique non-empty id")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    failures = []
    for cell in cells:
        x, y, width, height = [int(round(float(value))) for value in cell["bbox"]]
        asset_id = str(cell["id"])
        if (
            width <= 0
            or height <= 0
            or x < 0
            or y < 0
            or x + width > source.width
            or y + height > source.height
        ):
            raise ValueError(f"{asset_id}: cell bbox is outside the source grid")

        raw_cell = source.crop((x, y, x + width, y + height))
        transparent = remove_background(raw_cell, key, args.tolerance, args.dominance)
        alpha_bbox = transparent.getchannel("A").getbbox()
        empty = alpha_bbox is None
        border_touch = False
        if alpha_bbox is not None:
            left, top, right, bottom = alpha_bbox
            guard = args.border_guard
            border_touch = (
                left <= guard
                or top <= guard
                or right >= transparent.width - guard
                or bottom >= transparent.height - guard
            )
        suspicious, boundary, residue_ratio = boundary_key_ratio(
            transparent, key, args.tolerance, args.dominance
        )
        border_status = (
            "pass" if not border_touch or args.allow_border_touch else "fail"
        )
        chroma_status = (
            "pass"
            if residue_ratio <= args.max_boundary_key_ratio or args.allow_key_residue
            else "fail"
        )
        empty_status = "fail" if empty else "pass"
        cut_status = (
            "pass"
            if {border_status, chroma_status, empty_status} == {"pass"}
            else "fail"
        )

        final = trim_with_padding(transparent, args.trim_padding)
        output_path = args.out_dir / f"{asset_id}.png"
        final.save(output_path)
        record = {
            "id": asset_id,
            "semantic_unit_id": asset_id,
            "source_grid": str(args.image),
            "cell_bbox": [x, y, width, height],
            "path": str(output_path),
            "sha256": sha256(output_path),
            "size": [final.width, final.height],
            "semantic_unit_count": 1,
            "cut_status": cut_status,
            "resolution_status": "needs_visual_review"
            if cut_status == "pass"
            else "rejected",
            "qa": {
                "non_empty": empty_status,
                "border_integrity": border_status,
                "alpha_or_chroma": chroma_status,
                "raw_foreground_bbox": list(alpha_bbox) if alpha_bbox else None,
                "raw_cell_border_touch": border_touch,
                "boundary_key_pixels": suspicious,
                "boundary_pixels": boundary,
                "boundary_key_ratio": round(residue_ratio, 6),
                "trim_padding": args.trim_padding,
            },
        }
        records.append(record)
        if cut_status != "pass":
            failures.append({"id": asset_id, "qa": record["qa"]})

    report = {
        "status": "failed" if failures else "passed",
        "source_grid": str(args.image),
        "declared_cells": len(cells),
        "assets": records,
        "failures": failures,
    }
    if args.manifest_out:
        args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
