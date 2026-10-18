# Companion skills of the amazon-product-intelligence

Установлены рядом с основным скиллом `amazon-product-intelligence`. Основной протокол главный; при противоречии (факты владельца, `VERIFY_IN_UI`, запрет выдумывать данные, read-only работа со ссылками Amazon) побеждает он. Скиллы дают методику; данные из них (объёмы поиска, комиссии, цены) считать непроверенными, пока не подтверждены источником пользователя или живой проверкой.

| Скилл | Источник | Лицензия |
|---|---|---|
| `amazon-listing-optimization` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-backend-keywords` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-keyword-research` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-search-optimization` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-product-research` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-competitor-analysis` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-review-analyzer` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-profit-analyzer` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-fba-calculator` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-shipping-calculator` | nexscope-ai/Amazon-Skills | MIT |
| `tariff-calculator-amazon` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-international-listings` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-global-selling` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-variation-strategy` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-product-compliance` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-product-bundling` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-sales-estimator` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-brand-analytics` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-category-ungating` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-a-plus-content` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-category-research`, `amazon-one-shot` | liangdabiao/Amazon-Skills-Liang (уникальные, на китайском) | MIT (Nexscope AI) |
| `amazon-listing-skill` | OnestarQQ/amazon-listing-skill | лицензия не указана, уточнить у автора |
| `amazon-a-plus` (только SKILL.md)` | xianyu110/ecommerce-image-skills | MIT |

Скрипты `fetch-listing.sh`, `fetch-competitor.sh`, `research.sh` (где есть) тянут HTML Amazon через `curl`; правило проекта «без скрейпинга», запускать только по явной просьбе пользователя.
Тексты лицензий: `../licenses/`.
