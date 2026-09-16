# Reference reconstruction

Use this guide for an image-to-PPTX replica or for matching the style of an existing deck.

## Read the reference

Identify the canvas proportions, reading order, major alignments, text hierarchy, colors, and foreground/background layers. Transcribe the supplied text carefully; do not silently invent illegible words. A working object list is useful for a dense infographic, but a formal JSON inventory is not necessary for a simple slide.

For a style reference rather than an exact replica, retain its visual system while adapting the composition to the new content. Do not copy obsolete numbers or unrelated text.

## Reconstruct with appropriate objects

Choose the representation independently for each element:

| Content | Usually useful representation |
| --- | --- |
| Titles, labels, body text | Native text boxes |
| Panels, timelines, simple icons, flowcharts | Native shapes or grouped objects |
| Process relationships | Native connectors and arrowheads |
| Tables or charts with supplied source data | Native tables/charts or data-driven plots |
| Logos and detailed line art | Supplied/licensed vector assets when supported |
| Photographs, microscopy, complex paper figures | Supplied images with appropriate attribution |
| Illustrative artwork missing from the sources | Generated or licensed assets when helpful |

Exact vector editability and editable image placement are different deliverables. If only a screenshot of a chart is supplied, preserve it as a sourced image or explain what data is needed for an exact editable chart. Do not infer numerical values beyond the available evidence.

Keep independently edited labels and components separate when practical. Group a simple icon's shapes for convenient editing. Do not fragment a photograph into arbitrary objects.

## Review

Compare the rendered result at full-slide scale and zoom into dense regions. Check text, object coverage, relative size, baseline alignment, border completeness, and image aspect ratios. For a multi-slide reference deck, also check consistency with its masters and theme.

Fix visible defects before delivery. A successful save or parser check does not prove visual fidelity. If a source detail cannot be reproduced with the available material, state the specific approximation.

The optional strict asset workflow adds per-asset manifests and residual tracking. Use it only when those artifacts and constraints are part of the user's requested result.
