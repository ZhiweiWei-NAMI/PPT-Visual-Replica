# PPT Visual Replica

[中文说明](README.md)

Recreate reference images as editable PowerPoint slides, or develop scientific talks, teaching decks, and thesis defenses from papers, data, and notes. The skill integrates scientific-slides planning principles with visual reconstruction, selecting native objects, supplied assets, vectors, or generated illustrations as appropriate.

## Example requests

```text
Use $ppt-visual-replica to recreate this reference as an editable PPTX.
Keep text editable and use native shapes and connectors for simple diagrams.
Match the reference's proportions, hierarchy, and colors, then inspect a render.
```

```text
Use $ppt-visual-replica to develop a 15-minute research talk from these papers
and experimental figures. Explain the question, methods, results, and limits.
Preserve real data and citations; deliver an editable PPTX.
```

## Supported work

| Task | Approach |
| --- | --- |
| Reference reconstruction | Match the supplied visual while choosing object types for the requested editability |
| Scientific and teaching decks | Organize content around the audience, time, evidence, figures, equations, and sources |
| Existing deck edits | Preserve the theme and inspect changed slides plus slides affected by shared styles |

No particular image-generation provider, fixed illustration quota, slide-image PDF workflow, or skill named research-lookup is required. An editable picture object does not make its internal geometry editable; disclose that distinction when relevant.

## Optional strict asset workflow

The original generated-asset, residual, hash, and object-metadata pipeline remains available when explicitly requested. Its script interfaces remain compatible.

- [Skill entrypoint](skill/ppt-visual-replica/SKILL.md)
- [Reference reconstruction](skill/ppt-visual-replica/references/reference-reconstruction.md)
- [Scientific presentations](skill/ppt-visual-replica/references/scientific-presentations.md)
- [Strict workflow and artifact contracts](skill/ppt-visual-replica/references/strict-asset-workflow.md)

`build_pptx.py` is a single-slide strict-mode builder. `validate_delivery.py` validates that mode's specialized artifact directory. They are not general multi-slide authoring or validation tools. Use an appropriate presentation library/application for ordinary decks and inspect the render and editability.

Strict-mode validation:

```text
python skill/ppt-visual-replica/scripts/validate_delivery.py --root <output-root>
```

## Optional asset review wall (#2)

For image batches or complex replicas, `asset_review.py` displays reference/candidate pairs and reports missing items against an independent inventory. The agent normally reviews and continues; user confirmation is required only when requested.

The tool does not detect lost green details automatically or infer approval from rendering. Unchanged evidence retains review decisions; changed pixels or reference context invalidate them. Exact path maps replace unsafe basename fallback.

See the [workflow guide](skill/ppt-visual-replica/references/asset-review.md) and [example wall](examples/satellite-network/audit/asset_review_wall.png). The wall was regenerated; its assets remain unreviewed and do not constitute revalidation of the original example.

## Installation

Use the Codex Skill Installer:

```text
$skill-installer install https://github.com/ZhiweiWei-NAMI/PPT-Visual-Replica/tree/main/skill/ppt-visual-replica
```

Alternatively, copy `skill/ppt-visual-replica` into your skills directory. Preserve personal changes before updating an existing installation.

The bundled Python helpers use Python 3.10+, Pillow, and python-pptx. The skill validator also needs PyYAML. Ordinary deck-authoring dependencies depend on the selected tool; visual review needs PowerPoint, LibreOffice, or another renderer.

## Verification

```text
python -m unittest discover -s tests -v
python skill/ppt-visual-replica/scripts/audit_skill.py --root skill/ppt-visual-replica
```

Script tests do not replace visual review of a final deck. If rendering is unavailable, state what remains unverified.

## Existing examples

These examples predate the merge and illustrate the strict workflow. They were not regenerated or revalidated as part of the skill update.

- [Satellite network](examples/satellite-network/)
- [Medical AI pipeline](examples/medical-ai-pipeline/)
- [Manufacturing scheduler](examples/manufacturing-scheduler/)

| Reference | Selected PowerPoint objects |
| --- | --- |
| ![Satellite reference](examples/satellite-network/reference/reference.png) | ![Satellite selected elements](assets/readme/satellite-selected-elements.png) |

## License

See [LICENSE](LICENSE). The scientific presentation guidance consolidates and rewrites narrative, figure adaptation, and talk-planning concepts from scientific-slides. Its external generation scripts, templates, and mandatory image-generation workflow are not included.
