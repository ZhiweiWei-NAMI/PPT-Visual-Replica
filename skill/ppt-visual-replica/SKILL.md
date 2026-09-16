---
name: ppt-visual-replica
description: Create and edit editable PowerPoint decks, recreate slides or infographics from reference images, and develop scientific talks, teaching slides, and thesis defenses by generating slide drafts with imagegen first and then reconstructing editable PPTX. Choose visual fidelity, scientific evidence, and editability according to the user's requested deliverable.
---

# PPT Visual Replica

Produce the requested presentation with readable content, faithful visuals where a reference is supplied, and the requested level of editability. This skill combines visual reconstruction with scientific presentation planning.

## Choose the task

- **Reference reconstruction:** Match the supplied image or deck's hierarchy, proportions, typography, colors, and meaningful objects. See [reference reconstruction](references/reference-reconstruction.md).
- **Scientific or teaching presentation:** Organize the supplied papers, data, notes, and figures; use the `imagegen` skill to generate a visual draft of every slide first; then reconstruct those drafts as editable PPTX. This order is required. Follow [scientific presentations](references/scientific-presentations.md).
- **Existing deck edit:** Preserve its theme, master layouts, content order, and unmodified slides unless the requested change requires otherwise.
- **Strict generated-asset reconstruction:** Use [strict asset workflow](references/strict-asset-workflow.md) only when the user explicitly requests its per-asset generation, residual tracking, and full audit artifacts. It is a specialized compatibility mode, not a prerequisite for ordinary delivery.

These modes can be combined: for example, recreate the visual style of a reference while writing a scientific talk. Load only the relevant references.

## Scope and source material

Use the user's format, template, language, slide count, duration, and supplied sources. Infer routine choices from the material; ask only when missing information materially changes the result. A PPTX request means an editable deck, not a PDF assembled from slide images.

For new decks without a specified size, 16:9 is a reasonable starting point. Respect an existing deck's dimensions. Use installed fonts that support the content language, and report substitutions that affect fidelity.

## Required order for new scientific and teaching decks

Source material → slide content plan → `imagegen` full-slide visual drafts → editable reconstruction → rendered comparison and source verification.

Every planned slide needs a generated draft before reconstruction. Do not substitute a cover image, a few generated icons, or direct PowerPoint coding for this stage. Save the selected drafts with the project. Generated figures and text must not override real data, equations, or citations. Native shapes, vectors, and supplied assets remain valid choices during reconstruction. This requirement applies to new decks from source material; existing-image reconstruction and targeted edits retain their own routes.

## Choose the simplest suitable representation

- Keep titles, labels, equations where supported, tables, and explanatory text editable.
- Use native shapes, grouped objects, and connectors for diagrams and simple icons when they reproduce the intended appearance.
- Build charts from real data when it is available. Never manufacture measurements to imitate a chart.
- Reuse supplied figures and suitable licensed assets. Preserve sources and attribution where required.
- Use vector artwork when the target application supports it reliably. If conversion to a bitmap is necessary, disclose the resulting editability limit.
- For new scientific and teaching decks, use the installed `imagegen` skill for full-slide drafts before reconstruction. Additional isolated illustrations are optional. Follow imagegen's built-in-tool and fallback rules; do not silently skip the required generation stage.
- Treat an imported picture as an editable picture object, not editable internal geometry. State this distinction when it matters.
- Do not flatten a whole slide into an image when the user expects editable text and components. A supplied photograph or complex scientific figure may remain a single image if that fits the request.

Use uniform scaling for images. Keep process arrows as connectors where practical. Group objects according to how the user will edit them, not according to a universal one-asset-per-symbol rule.

## Build and review

Choose an available PowerPoint library, application automation, or presentation tool that supports the requested features. The bundled builder is a single-slide strict-mode helper; it is not a general multi-slide presentation engine.

Use visual hierarchy, spacing, contrast, and legible labels to support the message. Avoid fixed quotas for images, bullets, colors, or slides. A text-only slide can be appropriate.

Render the completed deck with an available renderer and inspect each created or modified slide for clipping, overlap, font substitution, unreadable equations, and distorted images. Compare reference reconstructions against the supplied reference. Check native object types when editability matters. After a small correction, recheck affected slides; broaden review if shared layouts or fonts changed.

If rendering or application verification is unavailable, report that limitation and the checks actually performed. Do not describe an unrendered deck as visually verified.

Deliver the requested presentation and useful previews or source assets. Keep manifests, residuals, and diagnostic files only when they support the requested audit or continued editing. Do not make a large evidence package a condition of ordinary delivery.

## Optional asset review

For a batch of image assets, use [asset review](references/asset-review.md) to compare reference crops and candidates, identify missing inventory items, and keep content-bound review records. The agent can review and continue; require user confirmation only when the user requested it or a material ambiguity needs their decision. Generating a wall is not approval.

## Bundled tools

Run scripts with `--help` for their arguments. Paths below are relative to this skill's root.

- `scripts/crop_reference.py`: crop regions for inspection or asset generation.
- `scripts/asset_review.py`: optional reference/candidate preview wall and persistent review records; see the asset review guide.
- `scripts/grid_cut.py`: split a generated asset grid and inspect transparency/borders.
- `scripts/align_from_redboxes.py`, `scripts/balance_text_lines.py`: adjust manifests used by the strict builder.
- `scripts/generate_prompt_pack.py`, `scripts/subtract_assets.py`, `scripts/build_pptx.py`, `scripts/validate_delivery.py`: the strict generated-asset pipeline described in its reference. Their narrow schemas and validation rules apply only to that mode.
- `scripts/audit_skill.py`: check this skill for hard-coded local paths and unwanted domain residue.

For ordinary native diagrams or multi-slide decks, use an appropriate presentation tool directly; do not force their contents into the strict pipeline's image-only semantic schema.
