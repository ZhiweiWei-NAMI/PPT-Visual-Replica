#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ABSOLUTE_PATH_RE = re.compile(
    r"((?<![A-Za-z0-9])[A-Za-z]:[\\/](?![nrtbfav0'\"`])[^\s`'\"]+|/(Users|home|mnt|Volumes)/[^\s`'\"]+)"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan skill files for hard-coded paths and forbidden domain residue."
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--forbidden", nargs="*", default=[])
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    hits = []
    for path in args.root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {
            ".md",
            ".py",
            ".yaml",
            ".yml",
            ".json",
        }:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), 1):
            if ABSOLUTE_PATH_RE.search(line):
                hits.append(
                    {
                        "path": str(path),
                        "line": line_no,
                        "type": "absolute_path",
                        "text": line.strip(),
                    }
                )
            for term in args.forbidden:
                if term and term.lower() in line.lower():
                    hits.append(
                        {
                            "path": str(path),
                            "line": line_no,
                            "type": "forbidden_term",
                            "term": term,
                            "text": line.strip(),
                        }
                    )
    report = {"status": "passed" if not hits else "failed", "hits": hits}
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if hits:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
