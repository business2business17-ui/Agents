# XLSX Production Plan

Create an XLSX production plan when the user asks for a complete content package or when the workflow reaches Step 5 (Production package, after checkpoint C1).

One row = one asset.

Accept the source reference in any of these forms:
- real public or private URL accessible to the workflow;
- Google Drive link;
- file path / attached filename / connector file ID;
- textual source description when the asset does not exist yet.

Never invent a URL.

## Required columns

Use at minimum these columns, in this order:

1. Project ID
2. Product Row ID
3. Marketplace
4. Language
5. Category (Row Level)
6. Category Status / Confidence
7. Product Type (Row Level)
8. Product Type Status / Confidence
9. Brand
10. Product / Variant
11. ASIN
12. SKU / EAN / GTIN
13. Content Type
14. Placement
15. Asset No.
16. Module / Surface
17. Objective
18. Conversion Goal
19. Priority
20. Source Type
21. Source Image / File / URL / Drive Link
22. Source Video / File / URL / Drive Link
23. Source TTX / Facts
24. Normalized TTX / Facts
25. Shopper Question / Objection
26. Recommended Content Angle
27. Proposed Benefit
28. Proof / Supporting Fact
29. Content Improvement Recommendation
30. Reference / Inspiration
31. Output Format
32. Dimensions
33. Aspect Ratio
34. Requirement Status
35. Background
36. Product Position / Scale
37. Product Fidelity Lock
38. Visual Concept / Scene
39. Graphic Elements / Icons
40. Text Position
41. Headline
42. Subheadline
43. Body / Supporting Copy
44. Feature 1
45. Feature 2
46. Feature 3
47. Feature 4
48. Feature 5
49. CTA / Native CTA Note
50. Alt Text
51. Safe Zone / Crop Notes
52. Mobile / Responsive Notes
53. Amazon Rules
54. Internal Production Rules
55. Claim Risk
56. Missing Input / Dependency
57. User Approval Required
58. User Approval Status
59. Revision Round
60. Production Status
61. Designer Brief Status
62. QA / Preflight Result
63. Notes

## Workbook structure

Use these sheets when useful:
- `ASSET_PLAN` - one row per asset; mandatory.
- `PRODUCT_TTX` - one row per product/SKU with row-level category, product type, raw TTX, normalized facts, units, evidence/source, and classification status.
- `CONTENT_INTELLIGENCE` - one row per proposed content angle: source fact, shopper benefit, proof point, recommended placement, copy direction, risk, and user approval status.
- `LOCALIZATION` - source text + localized versions by marketplace/language.
- `PROJECT_SETTINGS` - category, product type, marketplaces, production presets, approval status.
- `ISSUES` - missing inputs, Amazon compliance issues, claim risks, QA failures.

The workbook must remain usable even if some assets are only concepts and have no URL yet.

If multiple categories/types are present, never collapse them into a single project-level value. Preserve category and product type on every relevant row.

Use explicit values such as `DESCRIPTION ONLY - ASSET NOT CREATED` rather than fake paths or links.

## Designer layout columns

For designer-ready projects, extend `ASSET_PLAN` with these layout fields after `Text Position` or equivalent:

- `Layout Scheme / Verbal Wireframe`
- `Product Zone`
- `Product Canvas Share %`
- `Headline Zone`
- `Subheadline Zone`
- `Body / Supporting Copy Zone`
- `Callout / Icon Zones`
- `Supporting Visual Zone`
- `Reading Order`
- `Whitespace / Exclusion Zones`
- `Do Not Cover Areas`
- `Layout Option A`
- `Layout Option B`
- `Recommended Layout`
- `Layout Approval Required`
- `Layout Approval Status`

The purpose is to let a designer understand the asset without reinterpreting the creative strategy.

A row is not designer-ready if it states only generic instructions such as `text left / product right` without defining which text, hierarchy, supporting elements, and protected areas.
