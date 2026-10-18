---
name: sp-api-reference
description: Offline reference of official Amazon Selling Partner API models (Swagger JSON from amzn/selling-partner-api-models) - Listings Items 2021-08-01, Product Type Definitions 2020-09-01, Feeds 2021-06-30, Catalog Items 2022-04-01. Use to check exact field names, required attributes, enums, request/response shapes and error codes of SP-API endpoints when preparing or diagnosing listing data, feeds and processing reports. Not a live connection; no credentials.
---

# SP-API reference (offline)

Files in `models/` are the official OpenAPI/Swagger definitions, unmodified:

| File | Use for |
|---|---|
| `listingsItems_2021-08-01.json` | putListingsItem / patchListingsItem payloads, issue objects (`severity`, `code`, `attributeNames`), `requirements` (LISTING / LISTING_PRODUCT_ONLY / LISTING_OFFER_ONLY) |
| `definitionsProductTypes_2020-09-01.json` | searchDefinitionsProductTypes / getDefinitionsProductType: how product-type schemas and `requirements`, `locale`, `marketplaceIds` are requested |
| `feeds_2021-06-30.json` | createFeed / createFeedDocument, feed types, processing status and result document |
| `catalogItems_2022-04-01.json` | searchCatalogItems / getCatalogItem: identifiers, `includedData` sets (attributes, identifiers, images, productTypes, relationships, salesRanks, summaries) |

Rules:
1. Query the JSON (`python3 -c`/`jq`) for the exact name; do not recall field names or enums from memory.
2. This is the interface contract, not marketplace data: it contains no category attributes, limits or fees. For those use the project's feed template and `live-research.md`.
3. Other models (Orders, Reports, Product Fees, FBA, ...) are not bundled; fetch them from `github.com/amzn/selling-partner-api-models` on request.
4. Never ask for or store SP-API credentials here. Live calls belong to an MCP server the user configured themselves (see `docs/MCP_SERVERS.md`).
