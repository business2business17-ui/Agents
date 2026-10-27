# Amazon Analytic - Market Intelligence

Deterministic Python core (`mia/`, Python >= 3.10, stdlib only; `pytest` for tests) implementing the spec in `references/Amazon_Market_Intelligence_Agent_TZ_v1.2.md`. The LLM orchestrates and writes text; all numbers come from the core.

Run from this skill directory:

| Task | Command |
|---|---|
| Screen a folder of Xray exports (size, concentration, review barrier, Amazon share, new-ASIN share, duplicates) | `python examples/scan_xray.py <folder>` |
| Full niche + hypotheses + portfolio + report | `python examples/run_xray.py <config.json> [--pdf]` (config like `examples/de_tanning_xray.json`) |
| Single product decision package | `python examples/run_example.py <input.json>` |
| Self-tests | `python -m pytest -q` |

## Protocol
1. Read the user's files; classify (Xray category, Cerebro keywords, listings report). Screen first if there are many niches.
2. Build the config (market, category, price corridor, include/exclude terms, COGS/CPC/budget assumptions). Missing parameters are labelled `ASSUMED`; ask only for blockers, in one message.
3. Run the pipeline. Decision rules R0-R5 and their `decision_trace` come from `mia/decision.py`; do not override them.
4. Report: decision, Score, Confidence and its weakest link on the first page, wave-1 portfolio, main risks, next steps. Narrative only via `{{metric:id}}` placeholders passed through grounding + factcheck.
5. Be honest about limits: Keepa, Ads CPC and review analysis are not connected; fee rates and VAT in examples are illustrative - verify against the current fee schedule before a real decision.

## References
- `references/README-core.md` - modules, tests, simplifications.
- `references/Amazon_Market_Intelligence_Agent_TZ_v1.2.md` - specification.
- `references/Анализ_ТЗ_v1.1_проблемы.md`, `references/Доработка_агента_по_отчёту_Pets.md` - problem analysis and rework notes.
- `XRAY/` - real Helium 10 exports (Xray, Cerebro), listings report and sample scan output.

KNOWLEDGE: the files `references/*.md` are attached as knowledge; open the one named in each step when you reach it. Project memory: if you cannot write files, print the updated memory block at the end of each reply and ask the user to paste it next session.
