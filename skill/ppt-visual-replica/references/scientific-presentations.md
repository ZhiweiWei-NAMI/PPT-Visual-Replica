# Scientific and teaching presentations

Create scientific and teaching decks through imagegen-generated slide drafts followed by editable PowerPoint reconstruction. The planning, evidence, and speaking guidance below supports that required workflow.

## Required imagegen-first workflow

For a new scientific, teaching, or thesis-defense deck made from papers, data, or notes, follow this sequence:

1. Ground the slide content in the supplied material: outline each page's message, exact text, equations, data, and sources.
2. Read and use the installed `imagegen` skill. Generate a full-slide visual draft for every planned page with its built-in image generation tool, using consistent style references and the supplied scientific figures where appropriate. A cover image or a few decorative assets do not satisfy this step.
3. Inspect each generated page against the source material, correct visual/content problems, and save the selected slide drafts in the project. Keep original data and figures authoritative: generated text, plots, and numbers are not new evidence.
4. Use those generated pages as the visual references for [editable reconstruction](reference-reconstruction.md). Rebuild titles, body text, equations where supported, tables, simple diagrams, and connectors as editable PPT objects; use real data or original figures for scientific results.
5. Render the PPTX and compare each reconstructed slide with its generated draft. Check the source material again for text, values, equations, citations, and scientific meaning.
6. Deliver the editable PPTX and the generated reference drafts needed to review or continue editing it.

Do not skip slide-draft generation by going directly from an outline to PowerPoint code. Do not use an image-only slide deck as the editable deliverable. Native shapes and supplied assets are reconstruction choices after generation, not substitutes for the required first stage.

Use imagegen's built-in tool by default. If it is unavailable, report the limitation and follow the imagegen skill's fallback rules; do not silently bypass generation or switch providers. Inspect and proceed autonomously unless the user explicitly requested draft approval or a material content ambiguity requires their input.

## Plan around the audience and evidence

Identify the audience's background, the presentation's purpose, the available speaking time, and the claims supported by the supplied material. Use an existing outline if the user has provided one. For a new talk, a short slide map can record each slide's point, supporting evidence, visual, and approximate speaking time; it need not become a separate deliverable.

Choose a structure appropriate to the occasion rather than imposing one narrative on every deck:

- **Conference talk:** Establish the research question, explain only the methods needed to interpret the main findings, then discuss implications and limits.
- **Seminar:** Provide additional context, method detail, and opportunities for discussion.
- **Thesis defense:** Make contributions and the evidence for each contribution explicit. Explain methodological choices and limitations; prepare supporting detail in backup slides where useful.
- **Journal club:** Separate the paper's claims from your assessment of its methods, confounders, uncertainty, and generalizability.
- **Grant pitch:** Connect the problem to the proposed approach, available preliminary evidence, feasibility, and the requested next step.
- **Course or tutorial:** Sequence prerequisite concepts, explanation, worked examples, and practice or discussion. Do not force a research-results narrative onto teaching material.

Slide count follows content and speaking time. Dense methods or equations may need more explanation time than an introductory visual. Reserve time for questions when applicable and shorten the core talk if rehearsal exceeds the limit.

## Make scientific claims traceable

Use the user's papers, datasets, figures, and notes first. Look up additional sources only when needed for missing context, verification, or a requested literature review; use available research tools without requiring a specifically named skill.

Distinguish measurements, estimates, hypotheses, and illustrations. Preserve qualifications and negative findings that affect the interpretation. Do not invent sample sizes, performance gains, significance, citations, or references.

Put a concise source near a borrowed figure or factual claim, with fuller details in notes or a references slide when useful. Verify the source actually supports the claim and preserve permissions/attribution requirements. A generated illustration can explain a mechanism, but cannot serve as experimental evidence.

## Adapt figures for projection

Prefer original figure files or redraw from real data. Simplify busy journal figures for the room: split panels across slides, enlarge labels, and keep the data and conclusions unchanged. Use direct labels when they reduce legend lookup.

Preserve units, scale, sample size, relevant uncertainty, and distinctions between groups. Identify what error bars represent. Explain axis truncation or transformations when they affect interpretation. Do not remove an inconvenient series or crop evidence in a misleading way.

For dense heatmaps, networks, or microscopy, show an overview and selected details when the audience needs both. Choose accessible colors and use shape, position, or labels so color is not the only distinction.

## Compose for understanding

Give a slide a clear point without making every title an exaggerated claim. Prefer an informative finding in a results title when the evidence supports it.

Use readable type and simplify content rather than shrinking it to fit. For projected slides, body text around 24–28 pt and titles around 32–44 pt are useful starting points, not universal requirements. Respect the template, viewing distance, language, and slide density. Check equations, subscripts, Chinese text, and references in the actual render.

Use whitespace, alignment, and consistent visual encodings across the deck. A diagram is useful when it explains structure or causality; a short statement or equation may be clearer without decorative imagery. Use progressive disclosure only when it helps explain the material.

## Review the argument and delivery

Check that each conclusion follows from the displayed evidence and that the sequence can be followed without reading an accompanying paper. Explain unfamiliar notation before using it. Separate the user's contribution from prior work.

For an oral presentation, notes can hold supporting explanation and transitions without crowding slides. Prepare backup detail for likely questions when requested or useful. Do not require a fixed rehearsal count or unrelated supporting artifacts.

Use the rendering and editability checks in SKILL.md. For a scientific deck, also check units, figure captions, citations, equation symbols, and consistency of reported numbers.
