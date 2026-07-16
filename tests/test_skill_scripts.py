from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "skill" / "ppt-visual-replica" / "scripts"


def run_script(
    name: str, *arguments: object, check: bool = True
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(SCRIPTS / name),
        *(str(argument) for argument in arguments),
    ]
    return subprocess.run(
        command, check=check, capture_output=True, text=True, encoding="utf-8"
    )


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_image(path: Path, size: tuple[int, int], color: tuple[int, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA" if len(color) == 4 else "RGB", size, color).save(path)


class SkillScriptTests(unittest.TestCase):
    def test_prompt_pack_uses_explicit_classification_and_declared_cells(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            make_image(root / "reference.png", (120, 80), (255, 255, 255))
            items = []
            for index in range(3):
                crop = root / "reference_crops" / f"icon_{index}.png"
                make_image(crop, (12, 12), (index * 40, 20, 180, 255))
                items.append(
                    {
                        "id": f"icon_{index}",
                        "classification": "imagegen_asset",
                        "bbox": [index * 20, 0, 12, 12],
                        "source_crop": f"reference_crops/icon_{index}.png",
                        "semantic_unit_count": 1,
                    }
                )
            items.append(
                {"id": "caption", "classification": "text", "bbox": [0, 40, 100, 20]}
            )
            inventory = root / "visual_inventory.json"
            write_json(inventory, {"items": items})
            output = root / "prompts" / "assets_cycle_1.jsonl"

            run_script(
                "generate_prompt_pack.py",
                "--inventory",
                inventory,
                "--reference",
                root / "reference.png",
                "--out",
                output,
                "--rows",
                2,
                "--cols",
                2,
            )
            rows = [
                json.loads(line)
                for line in output.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(1, len(rows))
            self.assertEqual(3, rows[0]["grid"]["used_cells"])
            self.assertEqual(["icon_0", "icon_1", "icon_2"], rows[0]["grid"]["ids"])
            self.assertIn("leave every unused cell empty", rows[0]["prompt"])

            items[0].pop("classification")
            write_json(inventory, {"items": items})
            failed = run_script(
                "generate_prompt_pack.py",
                "--inventory",
                inventory,
                "--reference",
                root / "reference.png",
                "--out",
                output,
                check=False,
            )
            self.assertNotEqual(0, failed.returncode)
            self.assertIn("missing explicit classification", failed.stderr)

    def test_grid_cut_ignores_unused_cells_and_reports_clipping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            grid = Image.new("RGB", (300, 100), (0, 255, 0))
            draw = ImageDraw.Draw(grid)
            draw.rectangle((20, 20, 70, 70), fill=(220, 30, 30))
            draw.rectangle((120, 20, 170, 70), fill=(30, 30, 220))
            grid_path = root / "grid.png"
            grid.save(grid_path)
            spec = root / "spec.json"
            write_json(
                spec,
                {
                    "rows": 1,
                    "cols": 3,
                    "used_cells": 2,
                    "ids": ["red", "blue"],
                    "margin": 0,
                    "gap": 0,
                    "background": "#00FF00",
                },
            )
            manifest = root / "cut_manifest.json"
            run_script(
                "grid_cut.py",
                "--image",
                grid_path,
                "--out-dir",
                root / "assets",
                "--manifest-out",
                manifest,
                "--spec",
                spec,
            )
            self.assertEqual(
                ["blue.png", "red.png"],
                sorted(path.name for path in (root / "assets").glob("*.png")),
            )
            self.assertEqual(
                "passed", json.loads(manifest.read_text(encoding="utf-8"))["status"]
            )

            clipped = Image.new("RGB", (100, 100), (0, 255, 0))
            ImageDraw.Draw(clipped).rectangle((0, 10, 50, 80), fill=(220, 30, 30))
            clipped_path = root / "clipped.png"
            clipped.save(clipped_path)
            clipped_spec = root / "clipped_spec.json"
            write_json(
                clipped_spec,
                {
                    "rows": 1,
                    "cols": 1,
                    "used_cells": 1,
                    "ids": ["clipped"],
                    "background": "#00FF00",
                },
            )
            failed = run_script(
                "grid_cut.py",
                "--image",
                clipped_path,
                "--out-dir",
                root / "clipped_assets",
                "--manifest-out",
                root / "clipped_manifest.json",
                "--spec",
                clipped_spec,
                check=False,
            )
            self.assertEqual(2, failed.returncode)
            self.assertEqual(
                "failed",
                json.loads(
                    (root / "clipped_manifest.json").read_text(encoding="utf-8")
                )["status"],
            )

    def test_subtract_assets_only_removes_accepted_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            make_image(root / "residual.png", (80, 40), (0, 0, 0))
            make_image(root / "assets" / "accepted.png", (10, 10), (255, 0, 0, 255))
            qa = {
                name: "pass"
                for name in (
                    "identity",
                    "isolation",
                    "border_integrity",
                    "alpha_or_chroma",
                    "style_fidelity",
                )
            }
            matches = root / "asset_match_cycle_1.json"
            write_json(
                matches,
                {
                    "matches": [
                        {
                            "semantic_unit_id": "accepted",
                            "bbox": [0, 0, 20, 20],
                            "asset_path": "assets/accepted.png",
                            "semantic_unit_count": 1,
                            "resolution_status": "accepted",
                            "qa": qa,
                        },
                        {
                            "semantic_unit_id": "rejected",
                            "bbox": [40, 0, 20, 20],
                            "resolution_status": "rejected",
                        },
                    ]
                },
            )
            output = root / "residual_cycle_1.png"
            report = root / "subtract_report.json"
            run_script(
                "subtract_assets.py",
                "--input",
                root / "residual.png",
                "--matches",
                matches,
                "--out",
                output,
                "--report-out",
                report,
            )
            with Image.open(output) as image:
                self.assertEqual((255, 255, 255), image.getpixel((5, 5)))
                self.assertEqual((0, 0, 0), image.getpixel((45, 5)))
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(1, payload["accepted_count"])
            self.assertEqual(1, payload["remaining_count"])

    def test_end_to_end_delivery_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            make_image(root / "reference.png", (100, 100), (240, 240, 240))
            make_image(
                root / "reference_crops" / "icon.png", (20, 20), (180, 20, 20, 255)
            )
            make_image(root / "generated" / "grid.png", (60, 60), (0, 255, 0))
            make_image(root / "assets" / "icon.png", (24, 24), (20, 40, 200, 255))
            make_image(root / "residual_cycle_1.png", (100, 100), (255, 255, 255))
            make_image(root / "validation" / "slide_1.png", (100, 100), (245, 245, 245))
            (root / "prompts").mkdir(parents=True, exist_ok=True)

            write_json(
                root / "visual_inventory.json",
                {
                    "items": [
                        {
                            "id": "icon",
                            "classification": "imagegen_asset",
                            "bbox": [30, 30, 30, 30],
                            "source_crop": "reference_crops/icon.png",
                            "semantic_unit_count": 1,
                        },
                        {
                            "id": "panel",
                            "classification": "layout_native",
                            "bbox": [10, 10, 80, 80],
                        },
                        {
                            "id": "label",
                            "classification": "text",
                            "bbox": [10, 5, 80, 10],
                        },
                    ]
                },
            )
            prompt_row = {
                "prompt_id": "assets_cycle_01_batch_001",
                "source_anchor_ids": ["icon"],
                "reference_inputs": [
                    {
                        "role": "full_reference",
                        "path": "reference.png",
                        "sha256": file_hash(root / "reference.png"),
                    },
                    {
                        "role": "object_crop",
                        "anchor_id": "icon",
                        "path": "reference_crops/icon.png",
                        "sha256": file_hash(root / "reference_crops" / "icon.png"),
                    },
                ],
                "grid": {"rows": 1, "cols": 1, "used_cells": 1, "ids": ["icon"]},
            }
            (root / "prompts" / "assets_cycle_1.jsonl").write_text(
                json.dumps(prompt_row) + "\n", encoding="utf-8"
            )
            match_qa = {
                name: "pass"
                for name in (
                    "identity",
                    "isolation",
                    "border_integrity",
                    "alpha_or_chroma",
                    "style_fidelity",
                )
            }
            write_json(
                root / "asset_match_cycle_1.json",
                {
                    "matches": [
                        {
                            "semantic_unit_id": "icon",
                            "bbox": [30, 30, 30, 30],
                            "asset_path": "assets/icon.png",
                            "semantic_unit_count": 1,
                            "resolution_status": "accepted",
                            "qa": match_qa,
                        }
                    ]
                },
            )
            write_json(
                root / "residual_cycle_1_redboxes.json",
                {"cycle": 1, "unresolved_semantic_visuals": 0, "redboxes": []},
            )
            write_json(
                root / "asset_manifest.json",
                {
                    "assets": [
                        {
                            "semantic_unit_id": "icon",
                            "path": "assets/icon.png",
                            "source_type": "imagegen_asset",
                            "semantic_unit_count": 1,
                            "source_grid": "generated/grid.png",
                            "sha256": file_hash(root / "assets" / "icon.png"),
                        }
                    ]
                },
            )
            write_json(root / "layout_rules.json", {})
            layout = root / "layout_manifest.json"
            write_json(
                layout,
                {
                    "canvas": {"width": 100, "height": 100},
                    "slide": {"width_in": 10, "height_in": 10},
                    "elements": [
                        {
                            "id": "panel",
                            "type": "rect",
                            "purpose": "panel",
                            "x": 10,
                            "y": 10,
                            "w": 80,
                            "h": 80,
                            "fill": "#EEEEEE",
                        },
                        {
                            "id": "label",
                            "type": "text",
                            "x": 10,
                            "y": 5,
                            "w": 80,
                            "h": 10,
                            "text": "Label",
                            "expected_lines": 1,
                        },
                        {
                            "id": "icon_picture",
                            "type": "image",
                            "path": "assets/icon.png",
                            "source_type": "imagegen_asset",
                            "semantic_unit_id": "icon",
                            "semantic_unit_count": 1,
                            "anchor_slot": [30, 30, 30, 30],
                        },
                        {
                            "id": "flow",
                            "type": "line",
                            "purpose": "structural_arrow",
                            "x1": 20,
                            "y1": 70,
                            "x2": 80,
                            "y2": 70,
                            "end_arrow": {
                                "type": "triangle",
                                "width": "sm",
                                "length": "sm",
                            },
                        },
                    ],
                },
            )
            pptx = root / "delivery.pptx"
            run_script(
                "build_pptx.py",
                "--manifest",
                layout,
                "--asset-dir",
                root,
                "--out",
                pptx,
            )

            review_files = {
                "reference": root / "reference.png",
                "pptx": pptx,
                "preview": root / "validation" / "slide_1.png",
                "asset_manifest": root / "asset_manifest.json",
                "layout_manifest": layout,
            }
            write_json(
                root / "visual_review.json",
                {
                    "status": "passed",
                    "checks": {
                        name: "pass"
                        for name in (
                            "overall_fidelity",
                            "asset_completeness",
                            "border_integrity",
                            "alpha_or_chroma",
                            "text_layout",
                            "residual_review",
                        )
                    },
                    "files": {
                        name: {
                            "path": path.relative_to(root).as_posix(),
                            "sha256": file_hash(path),
                        }
                        for name, path in review_files.items()
                    },
                },
            )

            result = run_script("validate_delivery.py", "--root", root, check=False)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            report = json.loads(
                (root / "validation_report.json").read_text(encoding="utf-8")
            )
            self.assertEqual("passed", report["status"], result.stdout)
            self.assertTrue(all(gate["status"] == "pass" for gate in report["gates"]))

            make_image(root / "assets" / "icon.png", (24, 24), (200, 40, 20, 255))
            stale = run_script("validate_delivery.py", "--root", root, check=False)
            self.assertEqual(2, stale.returncode)
            stale_report = json.loads(
                (root / "validation_report.json").read_text(encoding="utf-8")
            )
            self.assertIn("asset_manifest_traceability", stale_report["failures"])


if __name__ == "__main__":
    unittest.main()
