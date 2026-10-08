# SEO engine and content generation

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 25. Stage 4 — SEO Engine

Analyze marketplace-specific SEO data.

Normalize:

- Case
- Punctuation
- Duplicate phrases
- Singular/plural
- Spelling variants
- Semantic duplicates
- Long-tail phrases
- Competitor terms
- Prohibited terms
- Unsupported claim terms

Do not blindly use all keywords.

## 26. SEO Classification

Classify into:

- `TIER_1_PRIMARY`
- `TIER_2_SECONDARY`
- `TIER_3_LONG_TAIL`
- `TIER_4_SEMANTIC`
- `EXCLUDE`

Keyword priority concept:

`Relevance × Purchase Intent × Search Demand × Product Match`

Product relevance has the highest priority.

## 27. SEO Marketplace Isolation

Each marketplace requires its own semantic dataset.

Examples:

- US SEO ≠ DE SEO
- DE SEO ≠ FR SEO
- FR SEO ≠ IT SEO

Never simply translate a US Cerebro export into another market's SEO strategy.

If source SEO belongs to the wrong marketplace:

`SEO_MARKETPLACE_MISMATCH`

## 28. SEO Sanitization Report

Before generating content, report:

- Total keywords
- Usable keywords
- Irrelevant keywords
- Competitor terms
- Prohibited terms
- Unsupported claims
- Exact duplicates
- Semantic duplicate clusters
- Tier 1 count
- Tier 2 count
- Tier 3 count
- Excluded count

## 29. Stage 5 — Content Generation

Generate marketplace-specific:

- Title
- Item Highlights
- Bullet Points
- Product Description
- Backend Search Terms

Content must be:

- Localized
- Factual
- Natural
- Indexable
- Readable
- Original
- Conversion-oriented
- Compliant

## 30. Marketplace Localization

Do not merely translate.

Localize:

- Keywords
- Shopping terminology
- Spelling
- Units
- Search phrase order
- Category conventions
- Customer vocabulary

Each marketplace uses its own SEO dataset whenever possible.

## 31. Title

For current Amazon non-media workflow:

Target maximum:

`75 characters including spaces`

If Product Type rules specify another applicable requirement, use the Product Type rule.

Preferred structure:

`Brand + Product Name/Model + Product Type + Key Attribute + Size/Count`

Do not keyword-stuff.

## 32. Title Word Repetition

A meaningful word must not appear more than two times in the title.

Before finalizing:

1. Lowercase internally
2. Tokenize
3. Normalize obvious grammatical variants
4. Count meaningful words
5. Rewrite if >2 occurrences

Do not circumvent this rule through:

- capitalization
- punctuation
- singular/plural manipulation
- unnecessary hyphens

## 33. Title Prohibitions

Do not include:

- Price
- Discounts
- Shipping
- Seller information
- URLs
- Email
- Phone
- Reviews
- Promotional language
- Unsupported claims
- Competitor brands
- Emojis
- Excessive punctuation
- Keyword stuffing

## 34. Item Highlights

Where supported:

Target maximum:

`125 characters including spaces`

Use for:

- Major differentiator
- Key feature
- Use case
- Material
- Compatibility
- Target application

Do not simply repeat the Title.

## 35. Bullet Points

Create up to 5 bullets unless Product Type rules require another structure.

Each bullet must provide unique information.

Default logic:

1. Core function / primary benefit
2. Key feature / material / technology
3. Use case / target user / compatibility
4. Technical / convenience feature
5. Size / package / care / included contents

Adapt to category.

## 36. Product Description

Expand rather than repeat the title/bullets.

Possible structure:

1. What the product is
2. Intended use
3. Key verified features/specifications
4. Compatibility/application
5. Package/size details

Use secondary and long-tail terms naturally.

No keyword stuffing.

## 37. Backend Search Terms

Target:

`<250 UTF-8 bytes`

Safe maximum:

`249 bytes`

Prioritize:

- Synonyms
- Alternate terminology
- Long-tail components
- Abbreviations
- Marketplace-local search variants
- Relevant terms not efficiently covered in visible content

Do not include:

- Competitor brands
- ASINs
- Promotional terms
- Unsupported claims
- Irrelevant traffic
- Duplicate spam
