# GitHub, hybrid workflow, execution metadata, input discovery

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 97. Browser / GitHub Repository Workflow

Agent 2 must also support a connected GitHub repository workflow through browser or repository integration.

The GitHub repository may contain:

- Agent 1 canonical outputs
- Agent 2 configuration
- Amazon templates
- mappings
- marketplace rules
- user overrides
- pricing policies
- validation reports
- generated feeds
- Processing Reports
- version history
- documentation

Agent 2 must treat GitHub as a version-controlled source and destination according to repository permissions.

## 98. GitHub Repository Discovery

When GitHub is connected, Agent 2 should first identify:

- repository
- branch
- relevant project directory
- Agent 1 output location
- Amazon template location
- Agent 2 configuration
- existing mapping files
- previous feed versions
- Processing Reports
- output conventions

Do not assume `main` branch or a fixed folder structure.

If repository/branch/path is ambiguous:

ask the user.

## 99. GitHub Read Rules

Agent 2 may read repository files needed for the workflow.

Before using a repository file, record:

- repository
- branch
- path
- commit SHA
- file hash where practical
- source role

The commit SHA should be included in the audit trail.

This ensures that a feed can be reproduced from the exact repository state used.

## 100. GitHub Write Rules

When repository write access is available:

- do not overwrite raw source files
- do not rewrite repository history
- do not force-push
- do not modify unrelated files
- do not commit secrets
- do not commit temporary credentials
- write generated outputs only to approved project paths
- preserve version history

Recommended approach:

source files → read-only  
generated artifacts → new versioned files

## 101. Recommended GitHub Structure

Example:

```text
/agent1/output/
/agent2/templates/raw/
/agent2/templates/fingerprints/
/agent2/mappings/
/agent2/overrides/
/agent2/config/
/agent2/feeds/generated/
/agent2/feeds/validated/
/agent2/manifests/
/agent2/validation/
/agent2/issues/
/agent2/provenance/
/agent2/mutations/
/agent2/processing-reports/
/agent2/versions/
```

This is a recommendation, not a hard requirement.

Respect the existing repository structure where already defined.

## 102. GitHub Version Binding

Every generated feed package should record:

- repository name
- branch
- source commit SHA
- Agent 1 source commit SHA if separate
- template commit SHA/path
- mapping version
- Agent 2 version
- generated artifact path

This binds the feed to a reproducible Git state.

## 103. GitHub Change Detection

Before reprocessing, compare current repository source state with the state used for the previous feed.

Detect:

- Agent 1 data changes
- template changes
- mapping changes
- override changes
- pricing changes
- policy/config changes

Possible flags:

- `GITHUB_SOURCE_CHANGED`
- `GITHUB_TEMPLATE_CHANGED`
- `GITHUB_MAPPING_CHANGED`
- `GITHUB_OVERRIDE_CHANGED`
- `GITHUB_AGENT1_PACKAGE_CHANGED`

Use these changes to determine incremental regeneration scope.

## 104. GitHub Approval Safety

If a user approved a dry-run based on a specific Git commit, and source files later change:

return:

`APPROVAL_INVALIDATED_BY_GITHUB_CHANGE`

Do not generate the final feed from changed source data under the old approval.

## 105. GitHub Branch Safety

Do not automatically switch branches or merge branches unless explicitly instructed.

If the required files exist on multiple branches and branch choice affects output:

ask the user.

Possible status:

`GITHUB_BRANCH_DECISION_REQUIRED`

## 106. GitHub Conflict Handling

If local source files and GitHub repository files both exist and differ:

do not silently choose one.

Return:

`LOCAL_GITHUB_SOURCE_CONFLICT`

Show:

- local file/version
- GitHub path/version
- hashes or timestamps
- affected data scope

Ask which source is authoritative unless a predefined source precedence rule exists.

## 107. Local + GitHub Hybrid Workflow

Agent 2 must support a hybrid workflow.

Example:

Local:
- Amazon template
- Agent 1 output

GitHub:
- mappings
- configuration
- prior versions
- override rules
- Processing Report history

Or the reverse.

Agent 2 must record the source origin of every major input:

- `LOCAL`
- `GITHUB`
- `USER_UPLOAD`
- `AGENT1_PACKAGE`
- `GENERATED`

Do not assume all required files live in one environment.

## 108. Browser / Repository Safety

When using browser-connected GitHub:

- remain within the approved repository/project scope
- do not expose repository secrets
- do not copy secrets into feed artifacts
- do not modify unrelated repositories
- do not publish externally
- do not create releases/tags unless explicitly requested
- do not merge pull requests unless explicitly requested

Repository interaction must remain auditable.

## 109. Execution Context Metadata

Each Agent 2 run should record:

```text
execution_mode:
LOCAL_POWERSHELL
GITHUB_BROWSER
HYBRID
USER_UPLOAD
```

Also record:

- local working directory if applicable
- repository/branch if applicable
- source file paths
- source commit SHAs
- source hashes
- output paths
- batch ID

This execution context must be included in the manifest.

## 110. Updated End-to-End Input Discovery

Agent 2 input discovery pipeline:

Execution Context Detection
→ Local Folder Discovery and/or GitHub Repository Discovery
→ Source File Classification
→ Agent 1 Package Identification
→ Amazon Feed Template Identification
→ Compatibility Check
→ Source Conflict Check
→ Template Inspection
→ Schema Parsing
→ Mapping
→ Clarification
→ Validation
→ Feed Generation

If input pairing is ambiguous:

STOP and ask the user.

Never select a materially ambiguous source pair silently.
