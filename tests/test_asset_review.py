from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "skill/ppt-visual-replica/scripts/asset_review.py"
spec = importlib.util.spec_from_file_location("asset_review", SCRIPT)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class AssetReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.assets = self.root / "assets.json"
        self.inventory = self.root / "inventory.json"
        self.wall = self.root / "wall.png"
        self.out = self.root / "review.json"
        Image.new("RGBA", (30, 20), (0, 160, 0, 255)).save(self.root / "green.png")
        Image.new("RGB", (100, 100), (40, 60, 80)).save(self.root / "reference.png")
        self.write(self.assets, {"assets": [{"asset_id": "green", "path": "green.png"}]})

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def generate(self, **kwargs):
        return review.generate_review(self.assets, self.root, self.wall, self.out, **kwargs)

    def approve(self, data):
        row = data["assets"][0]
        row.update(review_status="approved", notes="Keep green details",
                   reviewer="agent", reviewed_at="2026-09-16", action="keep")
        self.write(self.out, data)

    def test_expected_missing_and_unlisted_assets_are_visible(self):
        self.write(self.inventory, {"items": [
            {"id": "green", "classification": "imagegen_asset", "bbox": [0, 0, 25, 25]},
            {"id": "omitted", "classification": "imagegen_asset"},
            {"id": "title", "classification": "text"},
        ]})
        data = self.generate(inventory_path=self.inventory, reference=self.root / "reference.png")
        self.assertEqual(data["coverage"]["missing_asset_ids"], ["omitted"])
        self.assertEqual(data["integrity"]["status"], "failed")
        self.assertEqual(data["assets"][1]["availability"], "missing")
        self.assertEqual(data["assets"][0]["reference_status"], "available")
        self.assertEqual(len(data["assets"]), 2)
        with Image.open(self.wall) as wall:
            self.assertGreater(wall.width, 500)
        self.write(self.inventory, {"items": [{"id": "omitted", "role": "imagegen_asset"}]})
        data = self.generate(inventory_path=self.inventory)
        self.assertEqual(data["coverage"]["unlisted_asset_ids"], ["green"])

    def test_no_basename_fallback_and_explicit_mapping(self):
        self.write(self.assets, [{"id": "green", "path": "another_folder/green.png"}])
        data = self.generate()
        self.assertEqual(data["assets"][0]["availability"], "missing")
        data = self.generate(path_map={"another_folder/green.png": "green.png"})
        self.assertEqual(data["assets"][0]["availability"], "available")
        self.assertEqual(data["assets"][0]["path"], "green.png")

    def test_unchanged_decision_preserved_and_changed_pixels_invalidate(self):
        data = self.generate()
        self.approve(data)
        data = self.generate()
        self.assertEqual(data["assets"][0]["review_status"], "approved")
        self.assertEqual(data["assets"][0]["reviewer"], "agent")
        Image.new("RGBA", (30, 20), (0, 40, 0, 255)).save(self.root / "green.png")
        data = self.generate()
        row = data["assets"][0]
        self.assertEqual(row["review_status"], "needs_review")
        self.assertEqual(row["notes"], "Keep green details")
        self.assertEqual(row["previous_review"]["review_status"], "approved")
        self.assertNotIn("reviewer", row)

    def test_reference_change_invalidates_approval(self):
        self.write(self.inventory, [{"id": "green", "role": "imagegen_asset", "bbox": [0, 0, 20, 20]}])
        kwargs = dict(inventory_path=self.inventory, reference=self.root / "reference.png")
        self.approve(self.generate(**kwargs))
        Image.new("RGB", (100, 100), (180, 30, 0)).save(self.root / "reference.png")
        row = self.generate(**kwargs)["assets"][0]
        self.assertEqual(row["review_status"], "needs_review")
        self.assertEqual(row["notes"], "Keep green details")

    def test_duplicate_ids_and_invalid_crop_rejected(self):
        self.write(self.assets, [{"id": "same", "path": "green.png"},
                                 {"id": "same", "path": "green.png"}])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.generate()
        self.write(self.assets, [{"id": "green", "path": "green.png"}])
        self.write(self.inventory, [{"id": "green", "role": "imagegen_asset", "bbox": [90, 90, 20, 20]}])
        data = self.generate(inventory_path=self.inventory, reference=self.root / "reference.png")
        self.assertEqual(data["assets"][0]["reference_status"], "error")
        self.assertEqual(data["integrity"]["status"], "failed")

    def test_unreadable_candidate_and_review_not_overwritten(self):
        (self.root / "green.png").write_text("not a PNG")
        data = self.generate()
        self.assertEqual(data["assets"][0]["availability"], "error")
        self.assertEqual(data["integrity"]["status"], "failed")
        self.out.write_text("{broken")
        with self.assertRaises(ValueError):
            self.generate()
        self.assertEqual(self.out.read_text(), "{broken")

    def test_outputs_cannot_destroy_source(self):
        original = self.assets.read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            review.generate_review(self.assets, self.root, self.wall, self.assets)
        self.assertEqual(self.assets.read_bytes(), original)

    def test_cli_approval_is_optional_but_missing_files_fail(self):
        command = [sys.executable, str(SCRIPT), "--assets", str(self.assets),
                   "--wall-out", str(self.wall), "--review-out", str(self.out)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(command + ["--require-reviewed"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.approve(json.loads(self.out.read_text()))
        result = subprocess.run(command + ["--require-reviewed"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.write(self.assets, [{"id": "missing", "path": "missing.png"}])
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_source_crop_and_long_labels(self):
        self.write(self.assets, [{"id": "long_" * 30, "path": "green.png",
                                 "source_crop": "reference.png"}])
        data = self.generate(columns=1, cell_size=96)
        self.assertEqual(data["assets"][0]["reference_status"], "available")
        self.assertIsNotNone(data["assets"][0]["reference_sha256"])
        self.assertFalse(data["coverage"]["inventory_supplied"])


if __name__ == "__main__":
    unittest.main()
