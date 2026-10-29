# Brand Store playbook (Amazon US) + worked brief: Trendy Aesthetic

Use for any Brand Store task (sitemap, content matrix, wireframes, tiles, hero, ASIN routing, QA). Pixel boxes for Store modules: `amazon-specs.md` section 6 (`VERIFY_IN_UI` per module). Header image / tile rules there override any size in the brief.

## Generic rules (apply to every Brand Store)

1. **Architecture before banners.** Confirm the compatibility/ASIN matrix and the shopper path first (type -> model -> print/variant -> ASIN); only then design.
2. **Placeholders, not inventions:** `[BRAND_NAME]`, `[ASIN_REQUIRED]`, `[PHOTO_REQUIRED]`, `[URL_REQUIRED]`, `[PRINT_NAME]`. Never invent ASINs, prices, claims, compatibility, reviews, stars, discounts or Amazon/Apple badges.
3. **Do not fake a filter** the Store builder does not support; use tiles and product collections.
4. **Never Submit/Publish** without the owner's explicit approval; no passwords in briefs.
5. **Master table** (sku, asin, family, device_generation, compatible_model, print_id, print_name, listing_url, is_active, store_page, image_status); do not rename existing SKUs; Store does not replace correct variations in listings.
6. **Deliverables:** sitemap, content matrix (page, module, EN copy, image asset, target URL/ASIN, status), design directions, desktop+mobile mockups, asset list (sizes from the current Builder), ASIN routing map, QA + publish checklist, post-launch plan (Store Insights).
7. Native Store text over text baked into images; no small text on banners; safe areas for adaptive crop (`amazon-specs.md` section 6).

# Worked brief (verbatim from the owner)

# Agent Brief — Amazon US Brand Store | Trendy Aesthetic

> **Статус:** рабочее ТЗ для AI-агента / дизайнера / Amazon Store Builder.  
> **Язык коммуникации с владельцем:** русский.  
> **Язык контента для Amazon US:** английский (US).  
> **Результат:** подготовленный к сборке и проверке Amazon Brand Store, связанный с ассортиментом и A+ Content.

## 1. Роль агента и задача

Ты — специалист по Amazon US Brand Stores, e-commerce UX, бренд-дизайну и структуре каталога. Разработай **Trendy Aesthetic** Brand Store для бренда чехлов iPhone и AirPods с разными принтами. Работай с реальными данными бренда и требованиями Amazon. Не придумывай ASIN, факты о товарах, цены, преимущества, совместимости и обещания защиты.

**Главная бизнес-цель:** превращать посетителей Store в покупателей, одновременно помогая находить чехол для конкретной модели устройства и открывать связанные коллекции.

**UX-приоритет:** `выбрать тип чехла → выбрать модель устройства → выбрать принт → открыть подходящий ASIN`.

## 2. Исходные данные

- Маркетплейс: **Amazon.com (US)**.
- Бренд: зарегистрирован в **Amazon Brand Registry**.
- Ассортимент:
  - **Matte iPhone Cases** — матовые чехлы с разными принтами.
  - **Clear iPhone Cases** — прозрачные чехлы с принтами.
  - **AirPods Cases** — чехлы с принтами для AirPods Pro / Pro 2 и AirPods 4.
- Модели iPhone: линейка **iPhone 13–18**, включая варианты Pro Max там, где они реально существуют и товар доступен. Не предполагается, что у каждого поколения есть одинаковые модели (Standard, Plus, Pro, Pro Max и т. д.). Проверяй конкретные совместимости по исходной SKU/ASIN-матрице.
- Принты могут различаться между устройствами и покрытиями — подтверждать по каталогу.
- Выбранная творческая концепция: **B — Trendy Aesthetic**.

### Отсутствующие исходные материалы (запросить или явно обозначить как TODO)

1. Название бренда, логотип, брендбук (если есть).
2. Экспорт каталога: SKU, ASIN, parent/child, title, model compatibility, finish, print ID/name, listing status, stock status, product page URL.
3. Фотографии реальных чехлов в достаточном разрешении, исходники принтов, разрешения на изображения.
4. Подтверждённые характеристики: материал, текстура, особенности бортика камеры, совместимость с зарядкой и т. п.
5. Список бестселлеров и новых запусков, если есть данные.
6. Доступы/права на работу с Stores в Amazon Ads; никаких паролей в ТЗ.

При отсутствии данных используй пометки `[BRAND_NAME]`, `[ASIN_REQUIRED]`, `[PHOTO_REQUIRED]`, а не выдуманные значения. Не публикуй магазин без согласования владельца.

## 3. Позиционирование и дизайн-система

**Образ:** colorful, playful, trendy, expressive, fashion-accessories brand; продукт и принты в центре внимания. Не делать абстрактный «девчачий» дизайн в ущерб читаемости и покупке.

**Направление текстов (черновики, не финальные обещания):**
- Hero: **Your Case. Your Vibe.**
- Supporting: **Fresh Prints. Everyday Style.**
- Category: **Pick Your Style**
- Prints: **Find Your Print Crush**
- Cross-sell: **The Perfect Match**
- Buttons/tiles: **Shop Matte Cases**, **Shop Clear Cases**, **Shop AirPods Cases**, **Shop by Print**.

**Предварительная палитра (уточнить под реальные товары):**

| Цвет | HEX | Роль |
|---|---|---|
| Pink | `#F8ACCE` | Акценты, CTA-плитки |
| Lilac | `#C8B0F5` | Фоны коллекций |
| Butter Yellow | `#FDE7A2` | Вторичный акцент |
| Coral | `#FF8D76` | Микроакценты |
| Cream | `#FFF8F1` | Основной светлый фон |

Текст и активные элементы должны быть достаточно контрастными. Придерживайся единых фото-фонов и композиции, не допускай мелкого текста на баннерах; обеспечь хорошие мобильные обрезки.

## 4. Архитектура Brand Store

### Основные страницы

```text
HOME
├── Matte iPhone Cases
│   └── [навигационные плитки по поколениям/моделям при наличии товаров]
├── Clear iPhone Cases
│   └── [навигационные плитки по поколениям/моделям при наличии товаров]
├── AirPods Cases
│   ├── AirPods Pro / Pro 2
│   └── AirPods 4
└── Shop by Print
    ├── [Print Collection 01]
    ├── [Print Collection 02]
    └── [остальные реально существующие принты]
```

Если ограничения Amazon Stores или количество товара не позволяют создать глубокие страницы, реализовать навигацию через доступные плитки и product collections. **Не изображать наличие динамического фильтра моделей, если Store его не поддерживает.**

### Главная страница — порядок блоков

1. **Hero:** lifestyle-фото реальных iPhone + AirPods, слоган *Your Case. Your Vibe.* и заметная дорога в каталог.
2. **Pick Your Style:** три визуальные плитки Matte / Clear / AirPods, каждая ведёт на собственную страницу.
3. **Shop by Print:** 4–6 наиболее узнаваемых коллекций принтов с соответствующими ASIN/страницами.
4. **The Perfect Match:** сочетания одного принта на iPhone и AirPods; shoppable image, если поддерживается и корректно настроена.
5. **Best Sellers:** товарная подборка из подтверждённых SKU/ASIN и по возможности фактических данных продаж.
6. **New Arrivals:** только реальные новинки, если они есть.
7. **Brand Signature:** короткая фирменная фраза/визуал без неподтверждённых заявлений.

### Matte / Clear

- В верхней части: фотография серии и её подтверждённое отличие.
- Блок **Choose Your iPhone** с доступными поколениями.
- Дальше — доступные модели и продуктовые подборки, не показывающие несовместимые чехлы как подходящие.
- Не объединять матовые и прозрачные изделия под одним названием товара без явного обозначения материала/покрытия.
- При большом каталоге важнее разделить выбор модели, чем показать все принты на одном экране.

### AirPods

- Две хорошо различимые группы: **Pro / Pro 2** и **AirPods 4**.
- Pro / Pro 2 показывать совместно **только если каждый конкретный чехол совместим с обеими моделями**.
- Указывать совместимость корректно и явно, не путать название устройства и самого чехла.

### Shop by Print

- Названия принтов из каталога, а не придуманные.
- В каждой подборке показывать доступные версии Matte, Clear и AirPods.
- Если принт существует только для части моделей, нельзя намекать на универсальную совместимость.

## 5. Требования к визуальным материалам

Создай спецификацию и дизайн-макеты для следующих блоков:

| Материал | Первоначальное количество | Содержание |
|---|---:|---|
| Home hero | 1 desktop + mobile adaptation | 2–3 реальных изделия, заметный принт, слоган |
| Category tiles | 3 | Matte, Clear, AirPods |
| Print collections | 4–6 | Реальные принты, названия, корректные ссылки |
| Matching look | 1–2 | Один принт в нескольких категориях, если есть |
| Series banners | 3 | По баннеру на Matte, Clear, AirPods |
| Model-navigation tiles | по факту каталога | Устройства и поколения только с активными ASIN |

**Размеры экспорта:** брать из текущих спецификаций используемых модулей в Amazon Stores builder (в т. ч. desktop/mobile), а не считать заранее предложенные размеры универсальными. Подготовить изображения с безопасными полями под адаптивный crop.

**Требования:**
- Использовать реальные товары; визуально изменённые концепты не должны искажать продаваемый продукт.
- Права на изображения и принты должны принадлежать бренду или быть лицензированы.
- Не добавлять фиктивные отзывы, звёзды, скидки, цены, значки Amazon/Apple и недоказанные технические заявления.
- Избегать мелкого текста внутри графики; основной текст по возможности — нативными блоками Store.
- Фотографии показывают отличия Matte vs Clear, а не только разные цветные фоны.

## 6. Каталог, ASIN и связи

Подготовь master-таблицу с обязательными логическими полями:

| Поле | Пример | Примечание |
|---|---|---|
| `sku` | `MAT-IP16PM-FLR01` | Внутренний SKU |
| `asin` | `[ASIN_REQUIRED]` | Реальный ASIN |
| `family` | `MAT` / `CLR` / `AP` | Линейка |
| `device_generation` | `iPhone 16` | Для навигации |
| `compatible_model` | `iPhone 16 Pro Max` | Точная совместимость |
| `print_id` | `FLR01` | Единый ключ дизайна |
| `print_name` | `[PRINT_NAME]` | Название в Store |
| `listing_url` | `[URL_REQUIRED]` | Проверенная ссылка |
| `is_active` | `true/false` | Доступность листинга |
| `store_page` | `Matte` | Целевая страница |
| `image_status` | `approved/missing` | Статус контента |

Примерная система SKU:

- `MAT-IP16PM-FLR01` — матовый чехол iPhone 16 Pro Max, Floral 01.
- `CLR-IP16PM-FLR01` — прозрачный чехол той же модели и принта.
- `AP-PRO12-FLR01` — AirPods Pro/Pro 2 при подтверждённой общей совместимости.
- `AP-4-FLR01` — AirPods 4.

Существующие SKU **не переименовывать без отдельного анализа последствий** для учёта, фулфилмента и связей; схема применяется к новым SKU или как реестр псевдокодов. Parent–Child relationships и доступные variation themes отдельно сверять с текущим product-type template Amazon US. Brand Store не заменяет правильные вариации в товарных листингах.

## 7. Связь с A+ Content

Запланировать **три базовых A+ направления**:

1. Matte iPhone.
2. Clear iPhone.
3. AirPods (при необходимости отдельные фотографии/версии для Pro/Pro 2 и AirPods 4).

И **единый Brand Story** для бренда, если доступен в интерфейсе.

Связать страницы Store и A+ через предусмотренные Amazon механизмы, не обещать произвольные интерактивные переходы там, где продукт их не предоставляет. Общие шаблоны A+ могут применяться к нескольким ASIN только при совпадении релевантных характеристик, конструкций и совместимостей. Не показывать на A+ изделие другой модели как текущий продаваемый товар.

## 8. Реализация в Amazon Ads / Stores

1. Проверить бренд, права доступа, актуальные правила Amazon US, доступные шаблоны/модули Store и размеры для каждого выбранного блока.
2. Провести аудит каталога: реальные активные ASIN, совместимость, серии, принты, наличие фотографий.
3. Подготовить sitemap, customer journey и wireframes desktop/mobile.
4. Составить контент-матрицу с английскими заголовками, целевыми страницами и ASIN для всех плиток.
5. Собрать дизайн-систему и изображения; показать владельцу на согласование.
6. Собрать draft Store в Builder или сформировать подробные инструкции сборки, если доступа нет.
7. Протестировать все ссылки, карточки ASIN, совместимости, mobile preview, читаемость и crop.
8. Проверить соблюдение Store policies, отсутствие запрещённых заявлений и корректность прав на изображения.
9. Подготовить checklist публикации и передать проект владельцу на утверждение. **Не нажимать Submit/Publish без явного согласия владельца.**
10. После публикации предложить план оценки Store Insights и итераций.

## 9. Проверка качества / Definition of Done

- [ ] Все основные страницы логично связаны и работают на мобильном устройстве.
- [ ] С главной можно попасть в Matte / Clear / AirPods максимум за один очевидный переход.
- [ ] Для покупателя очевидно, как найти **свою** модель iPhone или AirPods.
- [ ] Каждый магазинный product tile ведёт к фактическому доступному ASIN, без фиктивных ссылок.
- [ ] Нет ложных утверждений о защите, MagSafe, совместимости, скидках и характеристиках.
- [ ] Visual identity единая, но продукт различим на фото.
- [ ] Принты и продукты представлены строго по реальному каталогу.
- [ ] Изображения соответствуют требованиям выбранного модуля Stores.
- [ ] Проверены desktop/mobile preview и адаптивная обрезка.
- [ ] Все тексты написаны на естественном английском для Amazon US.
- [ ] Список незакрытых вопросов и отсутствующих материалов передан владельцу.
- [ ] Ничего не опубликовано без подтверждения.

## 10. Ожидаемые артефакты от агента

1. **Store sitemap** — дерево страниц и связей.
2. **Content matrix** — таблица блоков: page, tile/module, copy (EN), image asset, target URL/ASIN, status.
3. **Design directions** — цвет, типографика, стиль фотографий и 1–2 направления главного hero.
4. **Desktop + mobile mockup** главной и шаблонов трёх категорий.
5. **Asset list** — требуемые фотографии/экспорты, формат и размер по текущему Amazon Builder.
6. **ASIN routing map** — какие реальные товары связаны с каждой категорией, моделью и принтом.
7. **QA + publish checklist** — что проверить до и после модерации.
8. **Post-launch measurement plan** — Store Insights: visits, page views, attributed sales, performance по страницам/источникам и улучшения на основе фактических данных.

## 11. Ключевая инструкция агенту

**Не начинай с красивых баннеров, пока не подтверждена матрица совместимостей и не определён путь покупателя до правильного товара.** Сначала продуктовая архитектура, затем дизайн и сборка. Если материалы отсутствуют — используй placeholders и передай список пробелов. Если текущие правила Amazon или Store Builder отличаются от этого документа, соблюдай актуальные официальные ограничения и фиксируй изменения.
