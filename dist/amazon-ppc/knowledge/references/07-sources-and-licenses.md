# 07 - Sources and licenses

The PPC agent is built from these public skills. MIT-licensed ones are vendored in `skills/` (license texts in `../../../licenses/`):

| Source | Used for | License |
|---|---|---|
| zerlinpi/amazon-ads-skills | 15 skills + playbooks, references, schemas, scripts (plugin root) | MIT |
| nospicyplease/amazon-ppc-advanced-skills | growth, drop diagnosis, harvest planner, Rocketcart live review | MIT |
| nexscope-ai/Amazon-Skills `amazon-ppc-campaign` | campaign build / optimize protocol, `fetch-competitor.sh` | MIT |
| MarketplaceAdPros/skill-amazon-ads | MCP usage guide (`amazon-ads`) | MIT |
| ehsanmqn/amz-ppc-optimizer, amandeepsharma07/amazon-ppc-optimizer | feature set reviewed only (campaign summary, bid recommendations, negatives, harvest from search term reports). These repositories carry no license, so no code or text was copied; `scripts/ppc_search_terms.py` is an independent implementation | none |

Benchmarks and thresholds inside companion skills are defaults, not Amazon facts: verify with the user's own data and current official documentation (`live-research.md`).
