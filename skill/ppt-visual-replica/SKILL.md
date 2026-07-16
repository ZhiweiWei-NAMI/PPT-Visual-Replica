---
name: ppt-visual-replica
description: Recreate a user-provided flat infographic, diagram, or presentation image as a visually faithful, object-level editable PowerPoint deck. Use for image-to-PPTX visual replicas that require minimum semantic-unit decomposition, imagegen/API-generated semantic assets, native editable text and layout geometry, native connector arrowheads, residual coverage cycles, artifact traceability, render comparison, and fail-closed delivery validation. Every semantic non-text visual must be an independent generated or explicitly approved user asset; icons and other meaningful graphics are never “basic PPT elements.”
---

# PPT Visual Replica

Build an editable PowerPoint replica from a reference image. Keep text and structural layout native to PowerPoint. Generate semantic visuals as isolated assets and place every visible occurrence as an independently selectable object.

## Work Fail-Closed

Do not claim completion because the PPTX opens, renders, or resembles the reference at a glance. Mark the delivery as passed only after every required artifact parses, every semantic unit is traceable, every gate is explicitly `pass`, and the rendered slide has been visually compared with the reference.

Treat `pending`, `to_verify`, missing evidence, an empty red-box file that contradicts the residual image, or a stale QA record as failure.

## Classify Every Visible Unit Explicitly

Inventory every visible occurrence with a stable `id`, exact `bbox`, and exactly one `classification`:

- `text`: editable PowerPoint text.
- `layout_native`: background, panel, frame, divider, connector, structural arrow, text container, or alignment-only geometry.
- `imagegen_asset`: every semantic non-text visual.

Do not infer the classification from keywords in an identifier. Reject missing, unknown, or ambiguous classifications. If uncertain, use `imagegen_asset`.

“Basic PPT element” means structural geometry only. It never includes an icon, chart icon, network icon, pictogram, device, screen, dashboard, gauge, shield, user group, logo-like mark, illustration, or other meaning-bearing graphic.

## Preserve Minimum Semantic Units

Represent each independently meaningful occurrence as its own final object:

- one semantic visual occurrence = one asset record and one PowerPoint picture;
- one text block = one editable text box with deliberate line breaks;
- one panel, frame, divider, connector, or structural arrow = one native object;
- one panel/process arrowhead = native arrowhead metadata on a connector line, never a standalone triangle, polygon, picture, or generated asset.

Do not merge multiple semantic visuals into one final raster, even when they share a card, row, cluster, legend, scene, or temporary generation grid. Do not reuse one asset path for different meanings. Permit intentional reuse only when the occurrences have the same semantic identity and the manifest records an explicit `reuse_group`.

### Composite Scene Exception

Use one `generated_scene_background` only when it allows text overlay and contains no reasonably separable semantic foreground objects.

When the user explicitly authorizes a specific hero or scene to remain composite, record:

```json
{
  "asset_role": "generated_scene_background",
  "allows_text_overlay": true,
  "composite_exception": {
    "approved_by": "user",
    "scope": "specific hero or scene",
    "reason": "user-authorized composite"
  }
}
```

Do not generalize one exception to other regions.

## Use the Residual as a Coverage Ledger

Treat the residual cycle primarily as batch and coverage tracking, not as a loop that automatically improves already accepted assets.

- Start cycle 0 from `reference.png`.
- Generate a fresh batch for unresolved anchors.
- Review each cut asset before subtraction.
- Mark an anchor `accepted` only after identity, minimum-unit isolation, border completeness, chroma/alpha cleanliness, and style fidelity pass.
- Subtract only accepted anchors from the current residual.
- Leave rejected or unresolved anchors visible in the next residual and regenerate those assets as needed.
- Do not feed accepted assets through later cycles for generic refinement.
- Finish when the residual contains no unresolved semantic visuals; native text and layout geometry may remain visible.

Regenerating a rejected asset is asset-level quality refinement. It does not change the residual’s role as the authoritative ledger of unresolved coverage.

## Core Workflow

1. Create one clean output root and copy the input image to `reference.png`.
2. Build `visual_inventory.json` at minimum-semantic-unit granularity. Reject composite crops masquerading as one unit.
3. Crop each `imagegen_asset` anchor separately. Record optional context crops separately from exact anchor crops.
4. Generate prompt packs from explicit classifications. Include the full reference and the corresponding crop for every requested unit.
5. Generate isolated white/chroma-key grids. Declare rows, columns, object order, used cell count, margins, gaps, background, and “no text.”
6. Cut only declared cells. Reject empty cells, clipped foregrounds, incomplete borders, chroma residue, stray marks, or semantic mismatches. Keep transparent padding around accepted assets.
7. Write `asset_match_cycle_<n>.json` with `resolution_status` and explicit QA gates for every attempted anchor.
8. Subtract only `accepted` matches from the current residual. Inspect the new residual and red-box every remaining semantic visual.
9. Repeat generation, acceptance, and subtraction until the unresolved set is empty.
10. Build the PPTX from accepted assets plus native text/layout objects. Use uniform contain scaling and write semantic metadata into every picture object.
11. Render the PPTX through PowerPoint or LibreOffice. Compare the rendered slide with the reference at full-slide and zoomed asset regions.
12. Run the bundled validators. Remove unused assets, crops, generated cells, stale QA files, and one-off scripts before delivery.

## Required Artifacts

Keep these under one output root:

```text
reference.png
visual_inventory.json
reference_crops/
prompts/assets_cycle_<n>.jsonl
generated/
assets/
asset_match_cycle_<n>.json
residual_cycle_<n>.png
residual_cycle_<n>_redboxes.json
asset_manifest.json
layout_manifest.json
layout_rules.json
validation/slide_<n>.png
visual_review.json
validation_report.json
<delivery>.pptx
```

Do not keep ad hoc `qa*.txt`, obsolete manifests, unreferenced crops/assets, abandoned generated cells, or temporary build scripts.

## Artifact Contracts

Use UTF-8 JSON and JSONL. Make every JSON file parseable before continuing.

For each `imagegen_asset` inventory item, record:

```json
{
  "id": "stable_semantic_unit_id",
  "classification": "imagegen_asset",
  "bbox": [0, 0, 100, 100],
  "source_crop": "reference_crops/stable_semantic_unit_id.png",
  "semantic_unit_count": 1
}
```

For each attempted match, record `semantic_unit_id`, `bbox`, `asset_path`, `semantic_unit_count: 1`, `resolution_status`, and these QA gates:

```json
{
  "identity": "pass",
  "isolation": "pass",
  "border_integrity": "pass",
  "alpha_or_chroma": "pass",
  "style_fidelity": "pass"
}
```

Use `resolution_status: accepted` only when every gate passes. Use `rejected` or `unresolved` otherwise.

Record a current SHA-256 hash for every reference/crop input in each prompt row and for every final asset in `asset_manifest.json`. Treat a hash mismatch as stale provenance and fail validation.

Use each `residual_cycle_<n>_redboxes.json` as the unresolved set after that cycle. Record `unresolved_semantic_visuals` equal to the red-box count; require both to be zero in the final cycle.

For `visual_review.json`, record the current SHA-256 hashes of the reference, PPTX, preview, asset manifest, and layout manifest. Record explicit `pass` values for overall fidelity, asset completeness, border integrity, chroma cleanliness, text layout, and residual review. Regenerate the review after any referenced file changes.

## Script Map

- `scripts/crop_reference.py`: crop exact anchors or context regions from the reference/current residual.
- `scripts/generate_prompt_pack.py`: validate explicit inventory classes and create deterministic batch prompt rows.
- `scripts/grid_cut.py`: cut declared cells, transparentize the background, retain padding, and report clipping/empty-cell QA.
- `scripts/subtract_assets.py`: subtract accepted matches only and emit a cycle report.
- `scripts/align_from_redboxes.py`: align manifest elements by declared red-box groups.
- `scripts/balance_text_lines.py`: enforce expected line counts and group font sizes.
- `scripts/build_pptx.py`: build the editable PPTX, contain-scale images, and embed semantic metadata.
- `scripts/validate_delivery.py`: enforce traceability, file cleanliness, PPTX metadata, current review hashes, and fail-closed gates.
- `scripts/audit_skill.py`: scan the skill directory for hard-coded paths and domain residue.

Prefer these reusable scripts to one-off project scripts.

## Prompt Requirements

Include `reference.png` and at least one exact object crop or residual crop in every semantic-asset request. Use this structure:

```text
Create an isolated asset grid for a PowerPoint visual replica.
Use the full reference for style and the supplied crops/residuals for object identity.
Objects in row-major order: ...
Grid: <rows>x<cols>; use the first <count> cells; leave unused cells empty.
Margin: <px>. Gap: <px>. Center one object in each used cell.
Background: uniform <white/chroma-key color>; no texture, shadows, panels, labels, arrows, or surrounding slide context.
Text: no readable text, letters, numbers, or watermark.
Preserve the complete silhouette and every border; keep clear background space on all sides.
Output: one clean grid image for deterministic cell cutting.
```

## PPT Build Rules

- Use the inventory/red-box `bbox` as the anchor slot.
- Declare `semantic_unit_id` and `semantic_unit_count: 1` on every normal image element.
- Write the same semantic ID into the PowerPoint picture name and description.
- Fit every image with uniform contain scaling. Record `fitted_bbox`; never stretch one axis independently.
- Build panel/process arrows as `line` elements with `purpose: connector` or `purpose: structural_arrow` plus `begin_arrow` and/or `end_arrow`.
- Use `right_arrow` or `down_arrow` only when the reference visibly contains a filled block arrow.
- Preserve deliberate text line counts. Do not accept accidental one-character wraps, clipping, overlap, or unexplained font-size drift.
- Do not build while any semantic visual is classified as `layout_native`, `unknown`, `rejected`, or `unresolved`.

## Final Validation Gates

Require all of the following to pass:

- all JSON/JSONL artifacts parse as UTF-8;
- inventory classifications are explicit and IDs are unique;
- each semantic occurrence has one exact crop, prompt coverage, accepted match, manifest asset, layout image, and PPT picture metadata record;
- no final asset contains multiple semantic units unless a recorded composite exception permits it;
- no asset is empty, clipped, missing a border, contaminated by chroma/stray marks, or semantically mismatched;
- no accepted anchor remains visible as an unresolved semantic visual in the residual;
- no unresolved semantic anchor is omitted from the final red-box review;
- no reference bitmap is embedded in the PPTX;
- no process arrowhead is implemented as a triangle shape, polygon, or picture;
- no unreferenced asset/crop, unused generated cell, stale QA record, temporary script, or dead file remains;
- every validation gate is `pass`, never `pending` or `to_verify`;
- the current PPTX renders successfully and the current preview has been visually compared with the reference.

If any gate fails, report failure and continue repairing. Do not relabel the result as passed without new evidence.
