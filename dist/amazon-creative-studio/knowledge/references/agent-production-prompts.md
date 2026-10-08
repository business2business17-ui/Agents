# Agent-to-Agent Production Prompts

Use this reference when the final creative work will be executed by another AI image/video/content agent rather than a human designer.

## Purpose

Convert the approved creative plan and layout into a production-ready prompt that another agent can execute with minimal interpretation.

Always separate the job into one or more of these modes:

1. `TEXT_COMPOSITING` — place approved text onto an existing image without altering the protected product.
2. `LIFESTYLE_BACKGROUND_GENERATION` — create or replace background/environment/decor around the protected product.
3. `BACK_VIEW_OR_REAR_SCENE` — create a rear-view/lifestyle scene only when a valid rear product reference exists, or generate only the surrounding environment while preserving the supplied rear product image.
4. `INFOGRAPHIC_COMPOSITING` — add icons, callouts, arrows, dimensions, ingredient/material cues, or technical labels around the protected product.
5. `VIDEO_ENVIRONMENT` — create motion/background/decor while maintaining product identity frame-to-frame.

Never ask another agent to invent a missing physical side, label, package text, logo, back panel, or product geometry from guesswork. If a required product angle is missing, request that source angle from the user or create the environment only and leave a placeholder/compositing instruction for the protected product layer.

## Mandatory prompt structure

Every agent-to-agent prompt must include:

### A. Task
- target Amazon placement;
- marketplace/locale;
- output type;
- exact canvas size/aspect ratio;
- one-sentence creative objective.

### B. Source assets
- exact source image/video/file/link identifiers;
- which source contains the protected product;
- which source is optional style/reference only.

### C. Product Fidelity Lock
State explicitly:

`The supplied product is a protected immutable layer. Do not redraw, regenerate, reshape, stretch, relabel, recolor, replace the logo, modify packaging text, invent missing packaging details, alter proportions, or morph the product. Preserve the product exactly as supplied.`

If compositing is supported, require masking/cutout/compositing rather than regeneration.

### D. Scene / environment
Describe:
- background type;
- surface/material;
- environment/decor;
- lighting direction and softness;
- shadow/reflection behavior;
- depth of field;
- scene realism level;
- props allowed/prohibited;
- color palette if approved;
- empty zones reserved for text.

### E. Product placement
Describe:
- left/center/right/foreground;
- approximate canvas share;
- scale;
- permitted rotation/crop;
- vertical alignment;
- no-cover zones for logo/label/package text.

### F. Text compositing
For every text block specify:
- exact approved copy;
- target language;
- hierarchy: H1/H2/body/callout;
- zone: top-left/top-center/right-third/etc.;
- alignment;
- max lines;
- relative size priority;
- contrast requirement;
- whether text may overlap background elements;
- prohibited overlap with product;
- native Amazon text vs baked-in text.

Never let a generative model rewrite approved copy. Require exact verbatim text rendering when embedded text is requested. If the model is poor at typography, instruct the executing agent to generate the visual without text first, then composite text in a deterministic text layer.

### G. Supporting graphics
Specify:
- icon count/type;
- callouts;
- arrows/lines;
- ingredient/material cues;
- comparison markers;
- decorative elements;
- whether graphics are illustrative or factual.

### H. Reading order
State what the shopper should notice 1st, 2nd, 3rd.

### I. Negative instructions
Include at minimum:
- no product redraw;
- no logo changes;
- no packaging-text changes;
- no proportion changes;
- no extra products unless approved;
- no unsupported claims;
- no fake certifications/awards;
- no random text;
- no watermark;
- no UI-like CTA unless approved for that placement;
- no cropping of mandatory product parts;
- no invented rear label/back panel.

### J. Output / QA
Specify:
- dimensions;
- file format;
- quality level;
- background requirements;
- mobile legibility requirement;
- exact-text verification;
- product-vs-source fidelity verification;
- final status expected.

## Text insertion prompt template

Use when the visual already exists and only text/layout must be added.

```text
TASK: Add approved Amazon marketing text to the supplied visual for [PLACEMENT], [MARKETPLACE/LOCALE].
CANVAS: [SIZE / ASPECT RATIO].
SOURCE: [FILE/LINK].

PRODUCT FIDELITY LOCK:
Treat the product as an immutable protected layer. Do not alter its shape, proportions, logo, packaging text, color, label, cap, typography, or visible details.

TEXT TO PLACE — render exactly, do not rewrite:
1. H1: "[COPY]"
   Zone: [ZONE]
   Alignment: [ALIGN]
   Max lines: [N]
   Priority: [HIGH]
2. H2: "[COPY]"
   Zone: [ZONE]
   Alignment: [ALIGN]
   Max lines: [N]
3. CALLOUTS: [EXACT COPY]
   Zone/grouping: [DETAILS]

LAYOUT:
[VERBAL WIREFRAME]

TEXT RULES:
- Keep all text outside protected product areas.
- Preserve clear contrast and mobile readability.
- Do not generate or paraphrase any additional text.
- If exact typography cannot be rendered reliably, output the image without text and provide a text-layer placement map for deterministic compositing.

NEGATIVE:
[NEGATIVE INSTRUCTIONS]

OUTPUT:
[FORMAT / SIZE / QA]
```

## Lifestyle environment prompt template

Use when the product is supplied and only the world around it should be generated.

```text
TASK: Create a lifestyle environment around the supplied protected product for [PLACEMENT], [MARKETPLACE].
CANVAS: [SIZE / ASPECT].
SOURCE PRODUCT: [FILE/LINK].

PRODUCT FIDELITY LOCK:
Do not regenerate the product. Use the supplied product exactly as-is via compositing/masking. Preserve proportions, shape, logo, package copy, colors, materials, and all visible details.

SCENE:
- Environment: [DESCRIPTION]
- Surface: [DESCRIPTION]
- Background/decor: [DESCRIPTION]
- Lighting: [DESCRIPTION]
- Props: [DESCRIPTION]
- Palette: [DESCRIPTION]
- Depth: [DESCRIPTION]
- Empty text zone: [ZONE]

PRODUCT POSITION:
[POSITION / SCALE / CANVAS SHARE / PERMITTED CROP]

SUPPORTING ELEMENTS:
[ICONS / INGREDIENTS / DECOR / NONE]

READING ORDER:
1. [FIRST]
2. [SECOND]
3. [THIRD]

NEGATIVE:
- Do not change or re-create the product.
- Do not invent extra packaging, labels, rear panels, ingredients, accessories, or claims.
- Do not place decor over logo or essential package text.
- Do not add random typography or watermarks.

OUTPUT:
[FORMAT / SIZE / QA]
```

## Rear-view / back-side rule

If the user wants a lifestyle visual featuring the back/rear of the product:

- Prefer a real rear-view source image from the user.
- Preserve that rear view exactly with Product Fidelity Lock.
- Generate only the environment/decor/background around it.
- If no rear-view source exists, do not hallucinate the back of the product.
- Ask for the rear-view photo or propose a front/three-quarter composition instead.

## Prompt output languages

Generate production prompts in the language requested by the user. If not specified, default to English for external AI tools while keeping the approved consumer-facing copy in the target Amazon marketplace language.

## Approval rule

Do not output a FINAL production prompt until the user has approved:
- the asset purpose;
- text copy;
- layout scheme;
- product angle/source;
- lifestyle/background direction when applicable.

If the user delegates creative decisions to the agent, record that delegation and proceed with the recommended option.
