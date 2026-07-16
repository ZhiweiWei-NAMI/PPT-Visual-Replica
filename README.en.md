# PPT Visual Replica

[中文 README](README.md)

Transform flat infographics into auditable, editable PowerPoint slides. Keep text and structural layout native to PowerPoint; decompose icons, devices, charts, screens, and other semantic visuals into independent transparent assets; and require the residual, asset trace, object metadata, and rendered preview to pass closed-loop validation.

## Recommended Prompt

```text
Use $ppt-visual-replica to recreate the local reference. Keep text and structural geometry native to PowerPoint, and generate every semantic non-text visual with IMAGE GEN as a minimum semantic unit. Subtract an anchor from the residual only after its asset passes identity, border, alpha/chroma, and style checks; deliver only after rendered comparison and fail-closed validation.
```

## Project Main Visual

![Hero visual placeholder](assets/readme/hero-visual.png)

## Quick Start

The core feature of this project is intelligently reconstructing the page through an AI agent based on these guidelines:

* **Text Content:** Utilize native PPT text boxes for easy future edits.
* **Layout:** Employ native PPT elements such as panels, separators, arrows, and connectors.
* **Semantic Visual Elements:** Extracted as transparent PNG files using IMAGE GEN or other image-capable APIs.
* **Minimal Semantic Units:** Icons, screens, charts, and devices correspond individually selectable PPT objects.
* **Strict Boundary:** Icons are not “basic PPT elements”; process arrows use native connector arrowhead metadata.
* **Fail-Closed Delivery:** Missing evidence, `pending`, `to_verify`, residual/red-box disagreement, dead assets, or stale QA records fail validation.

## v1.1.0: Residual and Validation Closure

This release tightens the workflow around failure modes observed in real replica and review tasks, and formally clarifies the residual-cycle semantics raised in [issue #1](https://github.com/ZhiweiWei-NAMI/PPT-Visual-Replica/issues/1):

* Define the residual as the batch and coverage ledger for unresolved semantic units, not an automatic enhancement loop for accepted assets.
* Subtract only `accepted` assets whose identity, isolation, border integrity, alpha/chroma cleanliness, and style fidelity gates pass.
* Cut only declared grid cells and report empty assets, boundary clipping, and color-key residue.
* Embed `semantic_unit_id` metadata in every PowerPoint picture, enforce uniform contain scaling, and preserve native editable connector arrowheads.
* Add `validate_delivery.py` to check JSON/JSONL integrity, crop/asset references, dead files, residual closure, current evidence hashes, PPTX object metadata, and accidental reference-image embedding.

Run the final validator with:

```text
python skill/ppt-visual-replica/scripts/validate_delivery.py --root <output-root>
```

## Workflow Visualization

![Workflow visual placeholder](assets/readme/workflow-visual.png)

## Example Showcase: Satellite Network Diagram

Below is a representative primary example. The left image is the original reference, while the right shows the fully selected editable elements in the PPT replica. Shown results represent the first-pass generation (Pass@1), accurately capturing the overall structure but may require slight adjustments in icons, details, and text alignment.

| Original Reference                                                         | Editable PPT Objects Selected                                                 |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| ![Satellite reference](examples/satellite-network/reference/reference.png) | ![Satellite selected elements](assets/readme/satellite-selected-elements.png) |

## Additional Examples

| Example                                                        | Description                                                              |
| -------------------------------------------------------------- | ------------------------------------------------------------------------ |
| [`satellite-network`](examples/satellite-network/)             | Heterogeneous satellite network architecture, typical academic use case. |
| [`medical-ai-pipeline`](examples/medical-ai-pipeline/)         | Multimodal medical AI-assisted diagnostic workflow.                      |
| [`manufacturing-scheduler`](examples/manufacturing-scheduler/) | Intelligent manufacturing multi-robot scheduling example.                |

## Known Issues and Recommendations

* When the reference contains many small icons, automated cutting and background removal can introduce damaged edges, clipping, key-color residue, or semantic mismatches. Do not accept those assets; regenerate or recut them until the complete silhouette and borders are clean.
* Slight alignment discrepancies may occur in Chinese text rendering, primarily due to font, size, line spacing differences, and PowerPoint rendering mechanisms. For higher fidelity, manual adjustments in PPT are recommended, or clearly specifying font sizes and line spacing for further agent optimization.

Suggested replacement prompt:

```text
I have placed authorized replacement icons in assets/user-icons/. Replace only the corresponding semantic units database_stack, server_rack, and monitor_dashboard. Preserve their anchor boxes and minimum-unit editability; record source_type=user_asset, provenance, and user approval in asset_manifest.json; then rerun rendering and the complete validation suite.
```

## Skill Installation

Recommended installation through Codex Skill Installer from the GitHub repository path:

```text
$skill-installer install https://github.com/ZhiweiWei-NAMI/PPT-Visual-Replica/tree/main/skill/ppt-visual-replica
```

Manual clone-and-copy installation is also supported:

**Windows:**

```powershell
git clone https://github.com/ZhiweiWei-NAMI/PPT-Visual-Replica.git
Copy-Item -Recurse .\PPT-Visual-Replica\skill\ppt-visual-replica "$env:USERPROFILE\.codex\skills\"
```

**macOS/Linux:**

```bash
git clone https://github.com/ZhiweiWei-NAMI/PPT-Visual-Replica.git
mkdir -p ~/.codex/skills
cp -R PPT-Visual-Replica/skill/ppt-visual-replica ~/.codex/skills/
```

Restart Codex after installation so the new skill is loaded.

---
