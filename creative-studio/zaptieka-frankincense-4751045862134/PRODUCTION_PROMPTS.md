# ZAptieka Frankincense Soap Bar — Amazon UK (B0GVSWRBWV, GTIN 4751045862134)

Пакет: карусель 7 картинок + A+ Basic (3) + A+ Premium (3). Стиль: минимализм, нишевая премиальная косметика.
Источник ТТХ/текстов: `designer-tz-amazon.xlsx` (лист «ТЗ по товарам», строка UK / WJ-9EH3-NUHN) + Google Sheet пользователя. ТТХ: 8 x 5 x 2.5 cm / 100 g, 100 g.

## 0. Статус и блокеры (прочитать первыми)

Статус: `NOT READY FOR AMAZON CREATIVE UPLOAD` — картинки здесь не сгенерированы (в среде нет генератора изображений, сторонним API товар не отправляется). Готов полный пакет промптов для вашего ИИ-генератора + правила проверки.

| # | Блокер | Что нужно | Рекомендация |
|---|---|---|---|
| B1 | В репозитории нет **второго референса** (брусок без этикетки). `images/4751045862134.png` — брусок в белой плёнке с этикеткой (3762x3762, RGBA). | Фото голого бруска (желательно 2 ракурса: верх + 2 грани) | Загрузите как `images/4751045862134_2.png`. Без него Image 2 и 7 нельзя делать как «брусок без этикетки» — генератор выдумает брусок, а это запрещено в вашем же промте. |
| B2 | Нет **эталонного баннера** («1 баннер пример») | Файл баннера | Загрузите как `images/brand/reference_banner.jpg`. Промты ниже ссылаются на него как на «Reference 1». |
| B3 | **Состав**: на этикетке — `Cocos Nucifera (Coconut) Oil, Butyrospermum Parkii (Shea) Butter, Aqua, Sodium Hydroxide, Boswellia Serrata (Frankincense) Extract`. В ТТХ — `Boswellia carterii oil`. Это разные виды/формы. | Подтвердить | Для Image 5 и A+ использовать формулировку **с этикетки** (Boswellia serrata, extract). Пока не подтверждено — ингредиентные картинки `VERIFY`. |
| B4 | Image 4 «How to use»: шаги в ТЗ помечены «verified against pack label», но на этикетке инструкции нет. | Подтвердить | Шаги нейтральные, оставляем; помечено `ASSUMED`. |
| B5 | Image 6: «Complete your routine: Milk & Honey / Goat Milk / Turmeric» — нужны packshot'ы этих GTIN | GTIN трёх мыл | Взять из `images/`; пока `PLACEHOLDER`. |

Принятые допущения (`ASSUMPTIONS`): рынок UK, язык EN; бренд ZAptieka; цвет текста deep forest green `#1F3D2B`; фон ivory/limestone `#EFE6D6…#D9CBB3`; claims только мягкие («calm», «soft», «sensitive-feeling») — без лечебных (acne/eczema/psoriasis из RU-ТТХ не используются, риск MEDIUM).

## 1. Общие блоки (вставлять в каждый промт)

**FIDELITY (брусок):**
`Use the real soap bar from Reference 2 as a protected layer. Keep its exact rectangular shape, proportions, thickness, edge wear, pores, warm ivory/milky-white colour and matte-satin surface. Do not redraw it as a generic bar, do not smooth it, do not add a label, logo, engraving or packaging. Contact shadow must match the scene light. If it cannot be preserved, output the scene without the soap and a mask area for compositing.`

**LOOK:**
`Photorealistic luxury skincare editorial photography, niche minimalist brand. Warm light-beige fine-grained limestone surface blending into a soft blurred background. Soft sunlight from upper left, long but light shadows, physically believable contact shadows, natural highlights and subtle imperfections, refined warm-neutral grade. No glow, no plastic or CGI look, no dark/orange/yellow background.`

**TEXT (двухпроходно, обязательно):** сначала сгенерировать сцену **без текста**, затем текст наложить детерминированно (Figma/Photoshop/скрипт). Шрифты: заголовок — контрастный display-serif (Playfair Display / Cormorant Garamond), подзаголовок — тот же serif *italic*, описание — humanist sans (Inter / Avenir) ≥ 5% высоты кадра для мобильного. Цвет `#1F3D2B`. Тонкие горизонтальные линии между блоками. Текст — буква в букву, без новых слов, без смены пунктуации.

**NEGATIVE:** `no flowers, leaves, towels, dishes, candles, shells, decorative stones, water, watermarks, borders, extra text, packaging on the soap, dark background, artificial light effects, unnatural shadows, symmetric gem-like resin pieces.`

**ТЕХ:** карусель 4000x4000 px, 1:1, JPG, sRGB, < 10 MB. A+ Basic 970x600, A+ Premium 1464x600, JPG/PNG RGB < 2 MB (рабочий размер — 2x, экспорт в точный).

## 2. Карусель (7 изображений)

### Image 1 — MAIN
Только подтверждённый packshot `images/4751045862134.png` (или фото бруска из B1 — решение по MAIN: на белом фоне товар в реальной упаковке/виде, как продаётся). Без генерации: вырезать по альфа-каналу, центр, 85–90% кадра, чисто-белый `#FFFFFF`, мягкая контактная тень. Текста нет. Экспорт 4000x4000.

### Image 2 — Hero proposition (ваш утверждённый промт)
**Раскладка:** верх-лево — пустое светлое пространство; верх-право — типографика; низ-лево — брусок крупно под естественным углом (видны верх и две боковые грани), стоит на камне; низ-право — кусочки ладана (небольшие, янтарно-медовые, полупрозрачные, непринуждённо, не симметрично). Мыло не перекрывает текст.
**Текст (verbatim):**
- `NATURAL SOAP BAR` — малый uppercase, широкий трекинг, тонкий шрифт; под ним короткая тонкая линия
- `Frankincense` — очень крупный контрастный serif (главный акцент)
- `soap for calm,` / `soft skin` — крупный italic serif, 2 строки
- `Soothing daily cleanse.` / `Comfort for` / `sensitive-feeling skin.` — sans, меньше заголовка
- тонкие линии между блоками, как в Reference 1

**Промт сцены (проход 1, без текста):**
```
Amazon UK secondary image 2, 1:1, 4000x4000. Match Reference 1 composition, lighting and palette exactly; do not invent a new design.
Reference 2 = the real soap bar (no label). {FIDELITY}
Bottom-left: the soap bar, large, natural angle, top and two side faces visible, standing on the stone with a realistic contact shadow.
Bottom-right and right of the bar: 5–8 small irregular natural frankincense resin pieces, translucent honey-amber, rough surface, warm highlights, individual contact shadows, casually scattered.
Top-left: free light space. Top-right: leave empty clean area for typography (no objects).
{LOOK} {NEGATIVE}
```
**Проход 2:** наложить текст по шаблону Reference 1.

### Image 3 — Key benefits
Слева брусок (тот же ракурс/свет), справа 4 тонких line-иконки (deep green, единый штрих) друг под другом, сверху заголовок.
Текст: `Key benefits` · 1) `Soothing daily cleanse` · 2) `Comfort for sensitive-feeling skin` · 3) `Soft, never tight` · 4) `Suits all skin types`.
Фон и свет — как Image 2, но спокойнее (больше воздуха). Иконки: капля/пена, мягкая волна, ладонь, круг-«все типы кожи» — без лишнего декора.

### Image 4 — How to use
Сверху заголовок; середина — 3 карточки слева направо; брусок в правом нижнем углу.
Текст: `How to use` · 1) `Wet hands and the soap bar` · 2) `Lather and massage gently over face or body` · 3) `Rinse well; let the bar dry between uses`.
Фото карточек: руки с пеной, без обрезанных пальцев; нейтральный тон кожи, тот же тёплый свет. (`ASSUMED` — см. B4.)

### Image 5 — What's inside (после B3)
Центр — брусок; вокруг 3 макро-круга с линиями-выносками (смола ладана, масло ши, кокосовое масло — реальные текстуры, без украшательства).
Текст: `What's inside` · `Frankincense (Boswellia serrata) extract - soothing aroma & care` · `Shea butter - softening` · `Coconut oil - mild cleansing`. Только ингредиенты из состава на этикетке. (Формулировка Boswellia — `VERIFY`, B3.)

### Image 6 — Size & volume
Сверху `Size & volume`, подзаголовок `8 x 5 x 2.5 cm / 100 g`; брусок с размерными стрелками (8 / 5 / 2.5 cm — масштаб соблюдать); внизу ряд из 3 packshot'ов `Complete your routine: Milk & Honey Soap Bar, Goat Milk Soap Bar, Turmeric Soap Bar` (B5). Строки: `Size: 8 x 5 x 2.5 cm / 100 g`, `Volume: 100 g`. Тонкие линии — единый стиль.

### Image 7 — Lifestyle / reassurance
Фон — минималистичная ванная/полка из светлого камня, мягкий дневной свет слева; брусок справа на переднем плане (в кадре — как в Image 2, без этикетки), слева сверху короткий заголовок `Frankincense soap for calm, soft skin`. Без декора, полотенец, цветов; допускается мягкий пар/влага на камне — не более.

## 3. A+ Basic (970 x 600, 3 слайда)

| Слайд | Модуль | Раскладка | Текст |
|---|---|---|---|
| B1 | Header image with text | лево 50% текст, право 33% брусок, угол — логотип ZAptieka, фон — Image 2 style | `Frankincense soap for calm, soft skin` / `Soothing daily cleanse. Comfort for sensitive-feeling skin.` |
| B2 | Standard image & text (benefits) | лево 35% брусок, право 65% — 3 колонки: иконка + заголовок + 1 строка | `Key benefits` · `Soothing daily cleanse` · `Comfort for sensitive-feeling skin` · `Soft, never tight` |
| B3 | Standard image & text (ingredients) | лево брусок, право 3 строки: макро-фото + название + описание | `What's inside` · ingredients как в Image 5 (после B3) |

Промт на каждый: `{FIDELITY} {LOOK} Canvas 970x600 (work at 1940x1200). Layout: <колонка выше>. Text is composited separately, leave clean zones. {NEGATIVE}`

## 4. A+ Premium (1464 x 600, 3 слайда)

| Слайд | Модуль | Раскладка | Текст |
|---|---|---|---|
| P1 | Full image — lifestyle hero | full-bleed светлый камень/свет, левая треть — слоган, правые 25% — брусок | `Frankincense soap for calm, soft skin` |
| P2 | Image with text — ingredient story | full-bleed макро смолы ладана (янтарь, тёплый свет), слева заголовок + 3 строки, справа 25% брусок | `Powered by Frankincense (Boswellia serrata) extract` · 3 строки ингредиентов как в Image 5 |
| P3 | Image with text — ritual, 4 колонки | сверху заголовок; ряд 4 колонок: фото + номер + подпись | `How to use` · 1) `Wet hands and the soap bar` · 2) `Lather and massage gently over face or body` · 3) `Rinse well; let the bar dry between uses` · 4) `Enjoy: Comfort for sensitive-feeling skin` |

Брусок — справа в правых 25% (P1, P2), не перекрывая текст; тот же свет слева сверху, что и в карусели — весь комплект должен читаться как одна серия.

## 5. QA перед загрузкой

1. Брусок сравнить с Reference 2 (форма, пропорции, цвет, поры) — не «вымышленный».
2. Весь текст сверить буква в букву с таблицами выше (особенно `sensitive-feeling`, точки, дефисы).
3. Мобильный просмотр: заголовок читается в 300 px.
4. Нет запрещённых объектов (NEGATIVE), нет лечебных claims.
5. Размеры/вес/sRGB: `scripts/validate_asset.py`.
6. Единый свет и палитра по всем 13 картинкам.

NEXT: загрузите фото бруска без этикетки (B1) и баннер-референс (B2), подтвердите состав (B3) — затем соберу сцены/композит и текстовые слои.
