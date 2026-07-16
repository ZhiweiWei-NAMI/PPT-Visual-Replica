#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


VALID_CLASSIFICATIONS = {"text", "layout_native", "imagegen_asset"}


def load_items(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        return data
    for key in ("items", "anchors", "visuals"):
        if isinstance(data.get(key), list):
            return data[key]
    raise ValueError("inventory must be a list or contain items/anchors/visuals")


def item_id(item: dict[str, Any], index: int) -> str:
    value = item.get("id") or item.get("anchor_id")
    if not value:
        raise ValueError(f"inventory item {index} is missing id/anchor_id")
    return str(value)


def classification(item: dict[str, Any], semantic_id: str) -> str:
    values = [
        item.get(key)
        for key in ("classification", "route", "class")
        if item.get(key) is not None
    ]
    normalized = {str(value).strip().lower() for value in values}
    if not normalized:
        raise ValueError(f"{semantic_id}: missing explicit classification")
    if len(normalized) != 1:
        raise ValueError(
            f"{semantic_id}: conflicting classifications: {sorted(normalized)}"
        )
    value = normalized.pop()
    if value not in VALID_CLASSIFICATIONS:
        raise ValueError(f"{semantic_id}: unsupported classification: {value}")
    return value


def validate_bbox(item: dict[str, Any], semantic_id: str) -> None:
    raw = item.get("bbox")
    if not isinstance(raw, list) or len(raw) != 4:
        raise ValueError(f"{semantic_id}: bbox must be [x, y, w, h]")
    values = [float(value) for value in raw]
    if values[2] <= 0 or values[3] <= 0:
        raise ValueError(f"{semantic_id}: bbox width and height must be positive")


def resolve_input(path_value: str, inventory_path: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = inventory_path.parent / path
    return path.resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prompt_for_group(
    reference: str,
    items: list[dict[str, Any]],
    rows: int,
    cols: int,
    margin: int,
    gap: int,
    background: str,
) -> str:
    lines = []
    for index, item in enumerate(items, 1):
        semantic_id = str(item["_semantic_id"])
        label = item.get("label") or item.get("semantic_label") or semantic_id
        lines.append(f"{index}. {label} [{semantic_id}]")
    used = len(items)
    return (
        "Create an isolated asset grid for a PowerPoint visual replica.\n"
        f"Use the full reference image ({reference}) for global style and the supplied exact crops/residual crops for object identity.\n"
        "Objects in row-major order:\n" + "\n".join(lines) + "\n"
        f"Grid: {rows} rows x {cols} columns; use the first {used} cells and leave every unused cell empty.\n"
        f"Margin: {margin}px. Gap: {gap}px. Center exactly one complete object in each used cell.\n"
        f"Background: perfectly uniform {background}; no texture, shadows, panels, labels, arrows, or surrounding slide context.\n"
        "Text: no readable text, letters, numbers, or watermark.\n"
        "Preserve the complete silhouette and every border; keep clear background space on all sides.\n"
        "Output: one clean grid image for deterministic cell cutting."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create strict image-generation prompt rows for semantic assets."
    )
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cycle", type=int, default=1)
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--margin", type=int, default=64)
    parser.add_argument("--gap", type=int, default=48)
    parser.add_argument("--background", default="#00FF00")
    parser.add_argument(
        "--provider", default="imagegen", choices=["imagegen", "openai", "gemini"]
    )
    parser.add_argument("--skip-input-existence-check", action="store_true")
    args = parser.parse_args()

    if args.rows < 1 or args.cols < 1:
        raise ValueError("rows and cols must be positive")
    if args.cycle < 1:
        raise ValueError("cycle must be positive")
    if not args.reference.is_file() and not args.skip_input_existence_check:
        raise FileNotFoundError(f"reference image not found: {args.reference}")

    reference_path = args.reference.resolve()
    reference_hash = sha256(reference_path) if reference_path.is_file() else None
    semantic_items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(load_items(args.inventory), 1):
        semantic_id = item_id(item, index)
        if semantic_id in seen_ids:
            raise ValueError(f"duplicate inventory id: {semantic_id}")
        seen_ids.add(semantic_id)
        route = classification(item, semantic_id)
        validate_bbox(item, semantic_id)
        if route != "imagegen_asset":
            continue
        if int(item.get("semantic_unit_count", 1)) != 1:
            raise ValueError(f"{semantic_id}: semantic_unit_count must equal 1")
        crop_value = str(item.get("source_crop") or "").strip()
        if not crop_value:
            raise ValueError(f"{semantic_id}: source_crop is required")
        if (
            not args.skip_input_existence_check
            and not resolve_input(crop_value, args.inventory).is_file()
        ):
            raise FileNotFoundError(
                f"{semantic_id}: source crop not found: {crop_value}"
            )
        prepared = dict(item)
        prepared["_semantic_id"] = semantic_id
        crop_path = resolve_input(crop_value, args.inventory)
        prepared["_source_crop_sha256"] = (
            sha256(crop_path) if crop_path.is_file() else None
        )
        semantic_items.append(prepared)

    capacity = args.rows * args.cols
    prompt_rows = []
    for offset in range(0, len(semantic_items), capacity):
        batch = semantic_items[offset : offset + capacity]
        batch_number = offset // capacity + 1
        effective_cols = min(args.cols, len(batch))
        effective_rows = math.ceil(len(batch) / effective_cols)
        ids = [str(item["_semantic_id"]) for item in batch]
        prompt_id = f"assets_cycle_{args.cycle:02d}_batch_{batch_number:03d}"
        prompt_rows.append(
            {
                "prompt_id": prompt_id,
                "cycle": args.cycle,
                "provider": args.provider,
                "prompt_mode": "asset_grid",
                "source_anchor_ids": ids,
                "reference_inputs": (
                    [
                        {
                            "role": "full_reference",
                            "path": str(args.reference),
                            "sha256": reference_hash,
                        }
                    ]
                    + [
                        {
                            "role": "object_crop",
                            "anchor_id": str(item["_semantic_id"]),
                            "path": str(item["source_crop"]),
                            "sha256": item["_source_crop_sha256"],
                        }
                        for item in batch
                    ]
                ),
                "grid": {
                    "rows": effective_rows,
                    "cols": effective_cols,
                    "used_cells": len(batch),
                    "ids": ids,
                    "margin": args.margin,
                    "gap": args.gap,
                    "background": args.background,
                },
                "prompt": prompt_for_group(
                    str(args.reference),
                    batch,
                    effective_rows,
                    effective_cols,
                    args.margin,
                    args.gap,
                    args.background,
                ),
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    serialized = "\n".join(json.dumps(row, ensure_ascii=False) for row in prompt_rows)
    args.out.write_text(serialized + ("\n" if serialized else ""), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "passed",
                "prompt_rows": len(prompt_rows),
                "semantic_items": len(semantic_items),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
