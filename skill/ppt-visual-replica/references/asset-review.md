# Optional asset review wall

Use this workflow for batches of cut/generated images or reference reconstructions with enough assets that side-by-side inspection helps. It is not required for ordinary scientific slides or native-shape diagrams.

The agent normally reviews the wall and continues within the user's existing authorization. Pause for user approval only when the user requested it or a material ambiguity needs their decision. Never record a user's approval without their response.

## Prepare inputs

The asset manifest can be a list or an object containing `assets`, `minimum_semantic_units`, or `items`. Each image needs an explicit unique `asset_id`, `semantic_unit_id`, `id`, or `anchor_id`, plus `path` (or `asset_path`). Native text/shapes are excluded.

Optionally supply an independent inventory through `--inventory`. Image entries match candidates by stable ID. Expected IDs absent from the candidate manifest appear as missing tiles; extra candidates are reported as unlisted. The tool cannot discover objects absent from both lists: inspect the full reference too.

Reference context comes from each inventory item's `source_crop`, or its `bbox: [x, y, width, height]` with `--reference`. Boxes use reference-image pixels. Asset/crop paths are relative to `--root`, defaulting to the asset manifest's directory. Command-line file paths are relative to the current working directory.

No basename fallback is used. If an older manifest uses virtual paths, supply a `--path-map` JSON dictionary mapping each exact manifest path to its actual path, resolved against the same root.

## Generate and inspect

From the skill root:

```text
python scripts/asset_review.py --assets <asset-manifest.json> --inventory <inventory.json> --reference <reference.png> --root <input-root> --wall-out <asset_review_wall.png> --review-out <asset_review.json>
```

Add `--font <font-file>` for labels needing a specific language font. For large batches, use smaller groups; the tool refuses excessively large walls rather than exhausting memory.

Each tile shows reference and candidate on a checkerboard. Inspect object identity, silhouette, borders, fine details, and foreground colors accidentally removed by chroma keying. A wall helps comparison; it does not detect those defects automatically.

If a candidate lost foreground color, repair or regenerate that candidate with a suitable background color, then regenerate the wall. Do not default to green when the object itself contains green.

## Record actual review decisions

The JSON separates file integrity from visual decisions:

- `availability`: available, missing, or error.
- `reference_status`: available, not_supplied, missing, or error.
- `review_status`: needs_review, approved, or rejected.
- `notes`, `reviewer`, `reviewed_at`, `action`: reviewer-supplied context; identify agent review separately from user review.

After actual inspection, update the relevant records. Generating a wall never sets approval. A suggestion to regenerate or replace an asset is not approval.

Regeneration retains decisions and notes for unchanged candidate/reference pixels and inventory membership. Changed evidence resets the decision to needs_review while keeping notes and the previous review. Fingerprints use decoded image pixels and dimensions, not compressed file bytes, so lossless re-encoding alone does not invalidate approval. Corrupt previous review JSON causes an error instead of silently erasing records.

Output paths are relative to the review JSON for portability. `source_path` retains the manifest value for diagnosis.

## Exit status and integration

The default command exits nonzero for missing/unreadable candidates or explicitly supplied invalid reference crops. Needs_review alone does not cause failure. This checks availability, not visual correctness.

`--require-reviewed` is an opt-in check that also exits nonzero unless every current asset is explicitly approved. Use it only for a task that requires an approval record. It does not contact the user or certify the identity of a reviewer.

For strict-mode reconstructions, the wall can supplement per-asset and final-slide inspection. It does not replace `validate_delivery.py`, and that validator does not automatically impose an asset-review approval requirement.

The satellite-network example includes a regenerated, unapproved wall plus explicit input mapping. Its manually selected reference regions demonstrate asset-level inspection, not proof that all slide occurrences match. The composite background has no isolated source crop and is marked not_supplied.

Regenerate that example from the repository root:

```text
python skill/ppt-visual-replica/scripts/asset_review.py --assets examples/satellite-network/audit/asset_manifest.json --inventory examples/satellite-network/audit/asset_review_inventory.json --reference examples/satellite-network/reference/reference.png --path-map examples/satellite-network/audit/asset_review_paths.json --wall-out examples/satellite-network/audit/asset_review_wall.png --review-out examples/satellite-network/audit/asset_review.json
```
