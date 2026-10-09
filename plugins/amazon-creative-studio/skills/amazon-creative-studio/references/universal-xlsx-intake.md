# Universal XLSX Intake

Use this reference whenever the user's product data comes from XLSX or CSV.

## Principle

Treat the user's workbook as a universal project data source, not as a fixed Amazon-creative template.

Do not require the user to rename columns, reorder sheets, or conform to the Skill's internal workbook structure before analysis.

## Column discovery

Inspect every relevant sheet and infer the semantic role of each column from:
- header text;
- neighboring values;
- repeated patterns;
- units;
- identifier formats;
- language;
- known product attributes.

Map discovered columns into the Skill's internal normalized fields, such as:
- project_id
- product_id / sku
- asin
- ean / gtin / upc
- brand
- product_name
- variant
- category
- product_type
- source_language
- marketplace
- ttx / technical_characteristics
- dimensions
- material
- ingredients
- usage
- claims
- certifications
- source_asset_link
- notes

Never assume exact column names.

## Mixed projects and mixed categories

The workbook may contain multiple projects, categories, product types, brands, marketplaces, or locales.

Classify and normalize per product row. Do not apply workbook-level category/type unless every relevant row clearly shares it.

If multiple projects are detectable, create or infer a project grouping field and keep outputs separated by project.

## Ambiguity handling

For every inferred mapping or classification, keep a confidence state:
- CONFIRMED
- HIGH_CONFIDENCE_INFERRED
- NEEDS_USER_CONFIRMATION
- UNKNOWN

Ask the user only about fields that materially affect content planning and cannot be resolved reliably from the data.

Prioritize clarification of:
1. category;
2. product type;
3. identity/SKU mapping;
4. ambiguous TTX meanings or units;
5. marketplace/language when project-level targeting is unclear.

Do not ask the user to repeat data already present in the workbook.

## Output separation

Never overwrite or restructure the user's source workbook unless explicitly requested.

Use the source XLSX as read-only input by default.

Create a separate normalized working/output workbook using the Skill's production schema when needed.

Keep traceability back to the original source using:
- source_file
- source_sheet
- source_row
- source_column / source_header where useful

## Translation

TTX can be present in Russian or any Amazon marketplace language.
Normalize meaning first, then localize to the target marketplace language. Do not translate ambiguous technical terms before resolving their meaning.
