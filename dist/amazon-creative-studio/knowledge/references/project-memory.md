# Project Memory

Goal: the user explains something once. The agent persists it and re-reads it at the start of every task.

## Location

`creative-studio/PROJECT.md` in the workspace (create from `assets/project-memory-template.md`). Workbooks and briefs go next to it under `creative-studio/out/`. Never store secrets or credentials.

## Rules

1. Read it before asking any question; skip every question it answers.
2. Update it at C1 (approved plan, assumptions), after production (produced files), and after C3 (statuses, open issues).
3. Decisions carry a tag: `CONFIRMED` (user said), `APPROVED` (user said ok to a proposal), `DELEGATED` (agent chose by delegation), `ASSUMED` (agent default, not yet confirmed). Only `CONFIRMED`/`APPROVED`/`DELEGATED` are not re-asked.
4. Brand-level entries (colors, fonts, tone, prohibited elements) apply to all SKUs; SKU-level entries apply to that SKU only. Never promote a SKU-level choice to brand level without the user's say.
5. If a new user instruction contradicts a stored decision, the newest instruction wins; update the file and note the change.
6. No file access on the platform: print the updated memory block in a fenced section at the end of the reply and ask the user to paste it back next session.
