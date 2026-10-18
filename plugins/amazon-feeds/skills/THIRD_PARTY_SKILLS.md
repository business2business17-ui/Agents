# Companion skills of the amazon-feeds agent

Установлены рядом с основными скиллами `amazon-feed-compiler` и `amazon-feed-error-agent`. Основной протокол главный; при противоречии (факты владельца, `VERIFY_IN_UI`, запрет выдумывать данные, read-only работа со ссылками Amazon) побеждает он. Скиллы дают методику; данные из них (объёмы поиска, комиссии, цены) считать непроверенными, пока не подтверждены источником пользователя или живой проверкой.

| Скилл | Источник | Лицензия |
|---|---|---|
| `amazon-variation-strategy` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-product-compliance` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-international-listings` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-backend-keywords` | nexscope-ai/Amazon-Skills | MIT |
| `sp-api-reference` | см. `sp-api-reference/LICENSE.Apache-2.0.txt` | Apache-2.0 |

Скрипты `fetch-listing.sh`, `fetch-competitor.sh`, `research.sh` (где есть) тянут HTML Amazon через `curl`; правило проекта «без скрейпинга», запускать только по явной просьбе пользователя.
Тексты лицензий: `../licenses/`.
