# Companion skills of the amazon-feed-compiler

Установлены рядом с основным скиллом `amazon-feed-compiler`. Основной протокол главный; при противоречии (факты владельца, `VERIFY_IN_UI`, запрет выдумывать данные, read-only работа со ссылками Amazon) побеждает он. Скиллы дают методику; данные из них (объёмы поиска, комиссии, цены) считать непроверенными, пока не подтверждены источником пользователя или живой проверкой.

| Скилл | Источник | Лицензия |
|---|---|---|
| `amazon-variation-strategy` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-product-compliance` | nexscope-ai/Amazon-Skills | MIT |
| `amazon-international-listings` | nexscope-ai/Amazon-Skills | MIT |

Скрипты `fetch-listing.sh`, `fetch-competitor.sh`, `research.sh` (где есть) тянут HTML Amazon через `curl`; правило проекта «без скрейпинга», запускать только по явной просьбе пользователя.
Тексты лицензий: `../licenses/`.
