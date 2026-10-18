# Companion skills of the amazon-ppc agent

Установлены рядом с основным скиллом `amazon-ppc`. Основной протокол главный; при противоречии (экономика из реальных затрат, достаточность данных, запрет выдумывать данные, запись в рекламный кабинет только после подтверждения строк) побеждает он. Скиллы дают методику; пороги и бенчмарки из них считать значениями по умолчанию, пока они не подтверждены данными пользователя или живой проверкой. Какой скилл для какой задачи: `amazon-ppc/references/02-skill-routing.md`.

| Скилл | Источник | Лицензия |
|---|---|---|
| `amazon-ads-optimizer`, `amazon-ads-audit`, `anomaly-detection`, `bid-optimization`, `budget-optimization`, `campaign-health-monitor`, `experiment-planner`, `growth-opportunity-finder`, `keyword-optimization`, `negative-targeting`, `performance-drop-diagnosis`, `placement-optimization`, `post-change-review`, `profitability-analysis`, `search-term-analysis` (+ `playbooks/`, `references/`, `schemas/`, `scripts/` в корне плагина, на них ссылаются эти скиллы) | zerlinpi/amazon-ads-skills | MIT |
| `amazon-account-growth-operating-system`, `amazon-ads-performance-drop-diagnosis`, `amazon-growth-opportunity-finder`, `amazon-search-term-harvest-planner`, `rocketcart-amazon-ads-live-review` | nospicyplease/amazon-ppc-advanced-skills | MIT |
| `amazon-ppc-campaign` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-ads` (Marketplace Ad Pros MCP) | MarketplaceAdPros/skill-amazon-ads | MIT |

Репозитории ehsanmqn/amz-ppc-optimizer и amandeepsharma07/amazon-ppc-optimizer лицензии не имеют: код и тексты не копировались, функциональность независимо реализована в `scripts/ppc_search_terms.py` (см. `amazon-ppc/references/07-sources-and-licenses.md`).

Скрипт `amazon-ppc-campaign/scripts/fetch-competitor.sh` тянет HTML Amazon через `curl`; правило проекта «без скрейпинга», запускать только по явной просьбе пользователя.
Тексты лицензий: `../licenses/`.
