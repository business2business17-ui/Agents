# Companion skills of the Design agent

Установлены рядом с основным скиллом `amazon-creative-studio`. Основной протокол (план, чекпоинт, Product Fidelity Lock, preflight) главный; компаньоны дают методику и промпты для конкретных типов картинок. Если компаньон противоречит `product-fidelity.md` или `amazon-specs.md`, побеждает основной скилл.

| Скилл | Источник | Лицензия | Для чего |
|---|---|---|---|
| `product-shots`, `product-shots-main-image`, `-multi-angle`, `-detail-page`, `-ad-creative`, `-social-post`, `-image-gen` | motiful/product-shots | MIT | MAIN-картинка, ракурсы, A+ модули, реклама, соцсети, генерация |
| `amazon-a-plus`, `amazon-white-background`, `selling-point-infographic`, `multi-angle-set`, `lifestyle-scene`, `size-chart`, `batch-background-swap`, `model-try-on`, `sale-banner`, `ecommerce-listing-suite` | xianyu110/ecommerce-image-skills | MIT | промпты и скрипты по типам картинок (Taobao/Xiaohongshu не взяты) |
| `amazon-image-design` | misty1999sd/amazon-image-design-skill | в репозитории лицензия не указана, проверить у автора | дизайн-процедура и требования к картинкам Amazon |
| `canvas-design`, `brand-guidelines`, `theme-factory` | anthropics/skills | Apache-2.0 | визуальная философия, бренд-стили, темы |

Не установлено: `clawnify/OpenListingStudio` (веб-приложение на Cloudflare, не скилл). Из него можно брать `agent.md`/`DESIGN.md` как референс.

Скрипты `generate.py` в `product-shots-image-gen` и `ecommerce-image-skills` ходят во внешний OpenAI-совместимый API и требуют ваш ключ в переменных окружения (`GPTIMAGE_API_KEY`, `OMNIMAAS_API_KEY` и т.п.); сам агент ключей не придумывает. `online_link.py` лишь собирает ссылку на сторонний сайт с промптом; не использовать, если промпт конфиденциален.

Тексты лицензий: `../licenses/`.

## Добавлено вторым пакетом

| Скилл | Источник | Лицензия | Для чего |
|---|---|---|---|
| `amazon-a-plus-content`, `amazon-enhanced-brand-content`, `amazon-listing-images`, `amazon-product-photography`, `amazon-storefront-design`, `amazon-display-ads` | nexscope-ai/Amazon-Skills | MIT | A+/EBC, картинки листинга, фотосъёмка, Store, display-реклама |
| `amazon-listing-skill` | OnestarQQ/amazon-listing-skill | лицензия не указана, уточнить у автора | по фото товара: тексты листинга и промпты套图 (на китайском) |

`liangdabiao/Amazon-Skills-Liang` - китайский вариант тех же 50 скиллов nexscope (имена совпадают), поэтому взята английская версия nexscope; из Liang берутся только уникальные скиллы (см. реестр Amazon-агентов, у Design их нет). `omishagupta/amazon-aplus-content-generator` - AWS-приложение (Bedrock, CDK, React), не скилл: не установлено. `xianyu110/.../amazon-a-plus` уже стоит у Design полностью.

Скрипты `fetch-listing.sh`/`fetch-competitor.sh`/`research.sh` у nexscope-скиллов тянут HTML Amazon через `curl`. Правило проекта: ссылки Amazon только read-only через `amazon_link.py`, без скрейпинга; эти скрипты запускать только по явной просьбе пользователя.
