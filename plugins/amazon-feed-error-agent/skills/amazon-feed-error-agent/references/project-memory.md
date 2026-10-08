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

## Rules

1. Read `PROJECT.md` before asking anything; skip every question it answers.
2. Update at each checkpoint and after each delivery (files produced, hashes, statuses).
3. Tag every decision: `CONFIRMED` (user said), `APPROVED` (user said ok to a proposal), `DELEGATED` (agent chose under delegation), `ASSUMED` (agent default). Only `ASSUMED` may be re-asked.
4. Reusable user rules (`USER_OVERRIDE_RULE`: enum mappings, "leave field Z empty under condition Q", operation vocabulary) are stored with scope (marketplace, product type, template version), precedence and date. Amazon template constraints always outrank them.
5. A newer user instruction overrides a stored decision; record the change.
6. Facts about products live in the Agent 1 package, not in memory; memory holds configuration, decisions, approvals and pointers (paths, hashes, commit SHAs).
7. No file access: print the updated memory block in a fenced section at the end of the reply and ask the user to paste it next session.
