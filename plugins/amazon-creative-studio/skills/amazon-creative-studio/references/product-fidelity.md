# Product Fidelity Lock

## Protected product principle

Treat every real user-provided product as an immutable protected layer.

### Never change without explicit authorization

- aspect ratio or proportions of the product;
- silhouette, packaging geometry, bottle/box shape, cap, dispenser, closure, handle, edges;
- logo shape, color, position, scale, spacing;
- printed product name, packaging text, typography, icons, EAN/barcode, marks, symbols;
- product color, packaging color, transparency, material identity;
- number of units or included parts;
- variant, size, flavor, shade, fragrance, model, or package version;
- real labels, stickers, regulatory marks, or distinguishing details.

Do not replace the product with a newly generated "similar" product.

## Allowed surrounding edits

Allowed when they do not modify the product:

- remove/replace background;
- create lifestyle environment;
- add external graphic elements;
- add compliant marketing text outside the product;
- create natural contact shadows or reflections that do not distort the product;
- resize the whole product uniformly;
- reposition or rotate the whole product only when requested and perspective remains truthful;
- crop canvas around the product without cropping the product itself unless explicitly approved.

## Safe compositing model

Use this conceptual layer order:

1. BACKGROUND / ENVIRONMENT
2. EFFECTS BEHIND PRODUCT
3. PROTECTED PRODUCT LAYER
4. CONTACT SHADOW / PHYSICALLY PLAUSIBLE REFLECTION
5. EXTERNAL TEXT / GRAPHICS / UI-SAFE ELEMENTS

Do not use generative fill inside the protected product mask.

## Video consistency

For video created from a real product image:

- prevent morphing of logo, label, cap, packaging text, silhouette, and proportions;
- prefer 2.5D/compositing, camera movement, environment animation, particles, light, shadow, and background motion;
- if an AI video model cannot preserve packaging identity, output a designer/VFX brief rather than a misleading render.

## Preflight comparison

Compare source and output for:

- silhouette;
- width/height proportions;
- logo;
- label placement;
- packaging text;
- cap/closure;
- color;
- orientation;
- included parts;
- distinctive design details.

Any unauthorized mismatch => `NOT READY FOR AMAZON CREATIVE UPLOAD`.
