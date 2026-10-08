# Local folder and PowerShell workflow

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 88. Local Folder / PowerShell Workflow

Agent 2 must support a local-folder workflow executed through PowerShell or an equivalent local shell environment.

The user may provide:

- one local working folder, or
- multiple folders containing the required source files

Typical local inputs:

1. Amazon FEED template
2. Agent 1 output package containing all normalized and validated product data
3. Optional supporting files:
   - catalogs
   - mapping files
   - prior feeds
   - pricing policies
   - Processing Reports
   - validation exports
   - image folders
   - user override files

Typical folder example:

```text
C:\AmazonProject\
    FEED Amazon\
    Agent 1\
    Catalogs\
    Images\
    Output\
```

The exact structure may differ.

Agent 2 must not assume fixed folder names unless configured.

## 89. Local Folder Discovery

When a local folder is provided, Agent 2 should inspect the directory structure before processing.

Identify:

- Amazon feed template files
- Agent 1 canonical JSON / JSONL / XLSX output
- prior mapping files
- prior validation files
- prior feeds
- Processing Reports
- catalogs
- images
- pricing files
- configuration files
- override files

Supported file types may include:

- `.xlsx`
- `.xlsm`
- `.json`
- `.jsonl`
- `.csv`
- `.tsv`
- `.md`
- `.txt`
- `.pdf`
- supported image formats

Do not modify source files during discovery.

## 90. PowerShell Execution Rules

When operating through PowerShell:

- use explicit absolute paths where possible
- quote paths containing spaces
- preserve Unicode filenames
- never overwrite source files unless explicitly instructed
- write generated artifacts into a dedicated output directory
- create missing output directories only when safe
- avoid destructive commands
- avoid recursive deletion
- avoid moving source files unless explicitly requested
- log generated file paths
- verify output file existence after writing

Preferred behavior:

READ SOURCE
→ COPY / PROCESS
→ WRITE NEW OUTPUT

Never use:

SOURCE FILE
→ destructive in-place modification

for the original Amazon template or Agent 1 source package.

## 91. Local Input Pairing

The standard local workflow expects Agent 2 to pair:

`Amazon FEED Template`
+
`Agent 1 Canonical Output`

Agent 2 must confirm the pair is compatible by checking:

- marketplace
- Product Type
- batch or project context
- Agent 1 schema version
- Product Type compatibility
- marketplace language/currency where relevant

If multiple candidate files exist, Agent 2 must not guess when pairing is ambiguous.

Return:

`LOCAL_INPUT_PAIRING_AMBIGUOUS`

and ask the user which files should be paired.

## 92. Local Source Priority

When multiple versions of the same file exist locally:

do not automatically choose the newest solely by filename or timestamp.

Prefer:

1. explicitly selected user file
2. file matching current batch ID
3. file matching expected schema/version
4. file with compatible manifest
5. latest verified version only if no ambiguity remains

If ambiguity remains:

ask the user.

## 93. Local Output Structure

Recommended local output:

```text
Output\
    Feeds\
    Mapping\
    Validation\
    Issues\
    Manifests\
    Provenance\
    Mutations\
    ProcessingReports\
    Versions\
```

Recommended generated files:

```text
AmazonFeed_<Marketplace>_<ProductType>_<BatchID>_<Part>.xlsx
Feed_Mapping_<BatchID>.json
Feed_Validation_<BatchID>.json
Feed_Manifest_<BatchID>.json
Feed_Issues_<BatchID>.xlsx
Cell_Provenance_<BatchID>.jsonl
Mutation_Log_<BatchID>.jsonl
```

Do not overwrite prior versions unless explicitly configured.

## 94. Local File Lock / In-Use Detection

Before modifying or copying an Excel workbook, detect where possible whether the file is:

- open in Excel
- locked by another process
- read-only
- inaccessible
- partially synced

If source or target file is locked:

return:

`LOCAL_FILE_LOCKED`

Do not force-write through a lock.

## 95. Local Checksum and Source Tracking

For every local source file calculate/store where practical:

- filename
- absolute or project-relative path
- file size
- modified timestamp
- file hash/checksum
- source role

This allows reproducibility and detects changed inputs.

If a source file changes after approval:

`LOCAL_SOURCE_CHANGED_AFTER_APPROVAL`

and invalidate the affected approval snapshot.

## 96. Local PowerShell Safety Boundary

Agent 2 may use PowerShell for:

- folder discovery
- file listing
- path validation
- checksum generation
- safe file copying
- safe output-directory creation
- running approved workbook-processing scripts
- validating generated files

Agent 2 must not use PowerShell to:

- delete unrelated files
- modify system settings
- change security policies
- install unapproved software
- access unrelated user folders
- expose secrets
- upload files externally without authorization

Keep PowerShell activity limited to the user-provided working scope.
