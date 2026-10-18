---
name: amazon-feeds
description: Router for the Amazon Feeds agent. Use for any Amazon feed workbook task - filling a feed template, reading a Processing Report, analyzing feed errors or warnings, correcting an uploaded feed. Decides FILL vs ERRORS/CORRECTIONS and hands over to `amazon-feed-compiler` or `amazon-feed-error-agent`.
---

# Amazon Feeds - mode router

Read the user's request, the attached files and `amazon-project/PROJECT.md`, then pick the mode. State it in the first line.

| Signal | Mode | Skill to load |
|---|---|---|
| Feed template (.xlsm/.xlsx) + product package / sealed JSONL / XLSX with data, nothing uploaded yet; "fill", "compile", "regenerate the feed" | **FILL** | `amazon-feed-compiler` |
| Processing Report, "errors", "warnings", rejected listings, "fix the feed", "re-check after re-upload" | **ERRORS / CORRECTIONS** | `amazon-feed-error-agent` |
| Report + the feed it belongs to + new data to put in | ERRORS first (Change Plan), then FILL audit on the rebuilt file | both, in that order |
| Only titles / bullets / keywords / prices must be written or rewritten | not this agent | `amazon-seo-listings` |

Glossary: the protocols below still say "Agent 1" = the `amazon-seo-listings` agent (source of the sealed package), "Agent 2" = FILL mode, "Agent 3" = ERRORS / CORRECTIONS mode.

Rules:
1. The loaded skill is the operating protocol; this router adds nothing to it.
2. Project memory (`amazon-project/PROJECT.md`) is shared by both modes: category, product type, marketplace, language, decisions.
3. The FILL write boundary (Template rows 7+, nothing else) also holds for corrections: a corrected file is a clean rebuild from the source feed plus an approved change set, then the FILL audit (`workbook_guard.py`).
4. If the mode is unclear after reading the files, ask one question with a recommended answer.
