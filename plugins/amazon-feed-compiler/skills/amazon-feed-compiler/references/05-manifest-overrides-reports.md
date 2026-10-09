# Manifest, artifacts, template diff/cache, overrides, precedence, processing report support, repository naming, audit, readiness

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 35. Feed Manifest

Create for every output:

- feed filename
- marketplace
- template hash
- template version
- template language
- template Product Type
- batch ID
- part number
- SKU count
- CREATE count
- UPDATE count
- PARTIAL_UPDATE count
- CONTENT_ONLY count
- PRICE_ONLY count
- OFFER_ONLY count
- blocked count
- generated timestamp
- Agent 2 version
- Agent 1 source version
- handoff schema version

## 36. Output Artifacts

Minimum:
1. Amazon_Feed.xlsx or .xlsm
2. Feed_Mapping.json
3. Feed_Validation.json
4. Feed_Manifest.json

Recommended:
5. Feed_Validation.xlsx
6. Feed_Issues.xlsx
7. Cell_Provenance.jsonl
8. Mutation_Log.jsonl

## 37. Template Difference Detector

If a prior template exists, compare old vs new:

Detect:
- added columns
- removed columns
- renamed columns
- changed definitions
- changed requirement status
- changed valid values
- changed validations
- changed occurrence limits
- changed operation values
- changed formatting rules

Do not reuse stale mappings for changed fields.

## 38. Template Mapping Cache

Reusable mapping may be stored by:
- marketplace
- Product Type
- template version
- template hash

Reuse only when fingerprint is compatible.

New hash/version requires reinspection of affected structure.

## 39. User Override Rules

User may define reusable rules.

Store:
- rule_id
- scope
- marketplace
- Product Type
- effective version/date
- source = USER
- precedence

Examples:
- canonical enum X always maps to Amazon value Y
- leave field Z empty under condition Q
- use a specific operation type in a defined workflow

Amazon hard template constraints remain authoritative.

## 40. Rule Precedence

1. Amazon template constraints
2. Data Definitions / validation
3. Agent 1 verified product meaning
4. Explicit user override
5. Existing approved mapping
6. Agent inference

Inference has the lowest priority.

## 41. Processing Report Support

Future workflow:

Amazon Processing Report
→ error parser
→ SKU
→ row
→ Amazon field
→ cell
→ Agent 1 source
→ error reason
→ suggested fix

Do not regenerate unrelated fields.

Safe formatting/enum corrections may be automated.

Meaning-changing corrections require user approval.

## 42. Incremental Regeneration

Use:
- Agent 1 changed_fields
- source hash
- content hash
- pricing hash
- record hash
- template mapping
- prior row mapping

If only a subset changed, regenerate only those records where safe.

## 43. Repository Structure

Recommended:

/agent2/templates/raw/
/agent2/templates/fingerprints/
/agent2/mappings/
/agent2/overrides/
/agent2/feeds/generated/
/agent2/feeds/validated/
/agent2/manifests/
/agent2/validation/
/agent2/provenance/
/agent2/mutations/
/agent2/processing-reports/
/agent2/errors/
/agent2/versions/

Never overwrite original Amazon templates.

## 44. Recommended File Naming

AmazonFeed_<Marketplace>_<ProductType>_<BatchID>_<Part>.xlsx

Example:
AmazonFeed_DE_HEADPHONES_B20261006_001.xlsx

Preserve .xlsm where applicable.

## 45. Audit Trail

Track:
- source template
- template fingerprint
- Agent 1 package version
- mapping version
- user overrides
- clarification questions
- user answers
- transformations
- generated files
- validation results
- Processing Report results
- timestamps

## 46. Clarification Output Format

Questions must be concise, grouped and actionable.

Example:

### BLOCKER — Country of Origin

47 SKUs require Country of Origin, but Agent 1 has no verified value.

Affected SKUs:
[reference/list]

Required action:
Provide origin data or a source file containing it.

Do not continue affected rows until resolved.

## 47. Ready-for-Upload Criteria

A feed is READY_FOR_UPLOAD only if:

- template inspected
- schema parsed
- required mappings resolved
- required attributes populated
- no unresolved hard blockers
- enums valid
- identifiers valid
- pricing valid
- operation intent mapped
- workbook integrity preserved
- file successfully reopened
- written values verified
- manifest created
- mapping report created
- validation report created

## 48. Final Architecture

Agent 2 pipeline:

Receive Agent 1 Package
→ Inspect Workbook
→ Reveal/Analyze Full Structure
→ Fingerprint Template
→ Detect Localized Sheet Roles
→ Parse Instructions
→ Parse Data Definitions
→ Resolve Valid Values / Dropdowns / Named Ranges
→ Build Amazon Template Schema
→ Map Agent 1 Fields
→ Evaluate Mapping Confidence
→ Run Clarification Engine
→ Resolve Operation Intent
→ Dry-Run Validate
→ Write Feed
→ Reopen
→ Verify Workbook
→ Generate Manifest
→ Generate Mapping
→ Generate Validation Report
→ READY_FOR_UPLOAD

Future error loop:

Amazon Processing Report
→ Error Parser
→ Field Provenance
→ Safe Correction or User Question
→ Incremental Feed Regeneration
