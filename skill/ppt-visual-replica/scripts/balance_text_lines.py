#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CJK_RE = re.compile(r"[\u3400-\u9fff]")


def split_text(text: str, lines: int) -> str:
    text = " ".join(str(text).split())
    if lines <= 1 or not text:
        return text
    if " " in text and not CJK_RE.search(text):
        words = text.split()
        chunks = [[] for _ in range(lines)]
        for idx, word in enumerate(words):
            chunks[min(lines - 1, int(idx * lines / max(1, len(words))))].append(word)
        return "\n".join(" ".join(c).strip() for c in chunks if c)
    n = len(text)
    return "\n".join(
        text[round(i * n / lines) : round((i + 1) * n / lines)] for i in range(lines)
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enforce expected line counts and group font sizes."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--rules", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    rules = json.loads(args.rules.read_text(encoding="utf-8-sig"))
    elements = {str(e.get("id")): e for e in manifest.get("elements", [])}
    changed = []
    for item in manifest.get("elements", []):
        if item.get("type") != "text":
            continue
        expected = item.get("expected_lines")
        if expected:
            new_text = split_text(str(item.get("text", "")), int(expected))
            if new_text != item.get("text"):
                item["text"] = new_text
                item["actual_or_estimated_lines"] = int(expected)
                changed.append(item.get("id"))
    for group in rules.get("text_groups", []):
        ids = [str(v) for v in group.get("element_ids", []) if str(v) in elements]
        if not ids:
            continue
        size = group.get("font_size")
        if size is None:
            sizes = [
                float(elements[i].get("font_size", 0))
                for i in ids
                if elements[i].get("font_size")
            ]
            size = min(sizes) if sizes else None
        if size:
            for i in ids:
                elements[i]["font_size"] = size
                changed.append(i)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {"changed": sorted(set(str(v) for v in changed)), "out": str(args.out)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
