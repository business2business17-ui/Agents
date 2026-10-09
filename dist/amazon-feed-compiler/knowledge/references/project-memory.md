# Project Memory (shared by the three Amazon agents)

Goal: the user states a decision once. All three agents (Product Intelligence -> Feed Compiler -> Feed Error) read and extend the same file so nothing is re-explained between steps.

## Location and layout

```
amazon-project/
  PROJECT.md                 <- this memory (template: assets/project-memory-template.md)
  agent1/  normalized/ evidence/ output/{json,jsonl,xlsx,issues}/ versions/
  agent2/  templates/raw/ mappings/ overrides/ feeds/{generated,validated}/ manifests/ validation/ provenance/ mutations/ processing-reports/
  agent3/  source/ working/ corrected/ reports/ change-sets/ diffs/
```
Raw sources (templates, user files, Agent 1 raw inputs) are READ-ONLY. Never store secrets or credentials in any file.

## Google Docs / Sheets links

When the user gives a link to a Google Doc, Sheet, Slides or Drive file, fetch it with `scripts/google_link.py fetch URL --out amazon-project/<agent>/source/` (read-only; works for "Anyone with the link" files, private files need `GOOGLE_ACCESS_TOKEN`, or use the Google Drive connector if the platform has one). Record the source in memory as origin `GOOGLE_LINK` with the URL (without tokens), file id, format, sha256 and fetch time, and treat the downloaded copy as the source: a later change of the Google file is a new fetch, not a silent update (`LOCAL_SOURCE_CHANGED_AFTER_APPROVAL`). Never put tokens into files or memory. Native Google Sheets exported to xlsx are data sources only - NOT Amazon feed templates (macros, validations and hidden structures are lost): the feed template must be the original `.xlsm`/`.xlsx` file from Drive (`--format raw` on a Drive file link) or an upload.

## Rules

1. Read `PROJECT.md` before asking anything; skip every question it answers.
2. Update at each checkpoint and after each delivery (files produced, hashes, statuses).
3. Tag every decision: `CONFIRMED` (user said), `APPROVED` (user said ok to a proposal), `DELEGATED` (agent chose under delegation), `ASSUMED` (agent default). Only `ASSUMED` may be re-asked.
4. Reusable user rules (`USER_OVERRIDE_RULE`: enum mappings, "leave field Z empty under condition Q", operation vocabulary) are stored with scope (marketplace, product type, template version), precedence and date. Amazon template constraints always outrank them.
5. A newer user instruction overrides a stored decision; record the change.
6. Facts about products live in the Agent 1 package, not in memory; memory holds configuration, decisions, approvals and pointers (paths, hashes, commit SHAs).
7. No file access: print the updated memory block in a fenced section at the end of the reply and ask the user to paste it next session.
