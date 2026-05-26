#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


SEMANTIC_ASSET_ROLES = {"imagegen_asset", "api_generated_asset", "provided_asset", "generated_scene_background"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_assets(path: Path) -> list[dict[str, Any]]:
    data = load_json(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("assets", "minimum_semantic_units", "items"):
            if isinstance(data.get(key), list):
                return data[key]
    raise ValueError("asset source must be a list or contain assets/minimum_semantic_units/items")


def asset_id(item: dict[str, Any], index: int) -> str:
    return str(item.get("asset_id") or item.get("id") or item.get("anchor_id") or f"asset_{index:03d}")


def asset_role(item: dict[str, Any]) -> str:
    return str(item.get("role") or item.get("classification") or item.get("route") or "")


def resolve_path(root: Path, value: Any, asset_dir: Path | None = None) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    if path.is_absolute():
        return path
    candidate = root / path
    if candidate.exists() or not asset_dir:
        return candidate
    return asset_dir / path.name


def fit_bbox(src_w: int, src_h: int, box_w: int, box_h: int) -> tuple[int, int, int, int]:
    if src_w <= 0 or src_h <= 0:
        return 0, 0, box_w, box_h
    scale = min(box_w / src_w, box_h / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    return (box_w - new_w) // 2, (box_h - new_h) // 2, new_w, new_h


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: tuple[int, int, int], max_width: int) -> None:
    font = ImageFont.load_default()
    words = text.replace("\\", "/").split("/")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current}/{word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    for offset, line in enumerate(lines[:3]):
        draw.text((xy[0], xy[1] + offset * 13), line, fill=fill, font=font)


def make_review_wall(
    assets: list[dict[str, Any]],
    root: Path,
    asset_dir: Path | None,
    out: Path,
    columns: int,
    cell_size: int,
    label_height: int,
    background: tuple[int, int, int],
) -> list[dict[str, Any]]:
    filtered = [
        (idx, item)
        for idx, item in enumerate(assets, 1)
        if asset_role(item) in SEMANTIC_ASSET_ROLES or item.get("path")
    ]
    if not filtered:
        raise ValueError("no reviewable assets found")

    rows = math.ceil(len(filtered) / columns)
    gap = 16
    pad = 20
    cell_w = cell_size
    cell_h = cell_size + label_height
    wall = Image.new("RGB", (pad * 2 + columns * cell_w + (columns - 1) * gap, pad * 2 + rows * cell_h + (rows - 1) * gap), background)
    draw = ImageDraw.Draw(wall)
    records = []

    for display_index, (source_index, item) in enumerate(filtered):
        col = display_index % columns
        row = display_index // columns
        left = pad + col * (cell_w + gap)
        top = pad + row * (cell_h + gap)
        draw.rounded_rectangle((left, top, left + cell_w, top + cell_h), radius=6, fill=(255, 255, 255), outline=(210, 215, 222))
        image_box = (left + 12, top + 12, cell_w - 24, cell_size - 24)

        path = resolve_path(root, item.get("path"), asset_dir)
        status = "missing"
        if path and path.exists():
            try:
                img = Image.open(path).convert("RGBA")
                x, y, w, h = fit_bbox(img.width, img.height, image_box[2], image_box[3])
                checker = Image.new("RGBA", (image_box[2], image_box[3]), (248, 249, 250, 255))
                for cy in range(0, image_box[3], 12):
                    for cx in range(0, image_box[2], 12):
                        if (cx // 12 + cy // 12) % 2 == 0:
                            ImageDraw.Draw(checker).rectangle((cx, cy, cx + 11, cy + 11), fill=(235, 238, 242, 255))
                resized = img.resize((w, h), Image.Resampling.LANCZOS)
                checker.alpha_composite(resized, (x, y))
                wall.paste(checker.convert("RGB"), (image_box[0], image_box[1]))
                status = "needs_review"
            except Exception as exc:  # pragma: no cover - defensive CLI reporting
                status = f"error: {exc}"

        if status == "missing":
            draw.rectangle((image_box[0], image_box[1], image_box[0] + image_box[2], image_box[1] + image_box[3]), fill=(255, 246, 246), outline=(236, 120, 120))
            draw.text((image_box[0] + 8, image_box[1] + 8), "missing", fill=(160, 40, 40), font=ImageFont.load_default())

        item_id = asset_id(item, source_index)
        label_y = top + cell_size
        draw.text((left + 12, label_y), item_id, fill=(20, 24, 31), font=ImageFont.load_default())
        draw_text(draw, (left + 12, label_y + 15), str(item.get("path") or ""), (82, 88, 102), cell_w - 24)
        records.append({
            "asset_id": item_id,
            "role": asset_role(item),
            "path": str(path) if path else "",
            "review_status": status,
            "notes": "",
        })

    out.parent.mkdir(parents=True, exist_ok=True)
    wall.save(out)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an asset review wall and confirmation JSON template.")
    parser.add_argument("--assets", required=True, type=Path, help="asset_manifest.json or visual_inventory.json")
    parser.add_argument("--root", type=Path, help="base directory for relative asset paths; defaults to --assets parent")
    parser.add_argument("--asset-dir", type=Path, help="fallback directory for asset filenames when manifest paths are virtual")
    parser.add_argument("--wall-out", required=True, type=Path)
    parser.add_argument("--review-out", required=True, type=Path)
    parser.add_argument("--columns", type=int, default=5)
    parser.add_argument("--cell-size", type=int, default=180)
    parser.add_argument("--label-height", type=int, default=56)
    args = parser.parse_args()

    root = args.root or args.assets.parent
    assets = load_assets(args.assets)
    records = make_review_wall(
        assets=assets,
        root=root,
        asset_dir=args.asset_dir,
        out=args.wall_out,
        columns=max(1, args.columns),
        cell_size=max(96, args.cell_size),
        label_height=max(40, args.label_height),
        background=(246, 248, 251),
    )
    review = {
        "asset_review_wall": str(args.wall_out),
        "source": str(args.assets),
        "instructions": "User confirmation gate before PPT export: confirm that no semantic assets are missing and no green object details were removed by background cutting. Mark any failed item as regenerate, replace_with_provided_asset, or remove.",
        "assets": records,
    }
    args.review_out.parent.mkdir(parents=True, exist_ok=True)
    args.review_out.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"assets": len(records), "wall": str(args.wall_out), "review": str(args.review_out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
