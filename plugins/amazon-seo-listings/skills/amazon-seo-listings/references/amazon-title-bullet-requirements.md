# Amazon: requirements for product titles, bullet points and Item Highlights

Source: Seller Central help text supplied by the user (file `Amazon_Product_Title_and_Bullet_Point_Requirements.md`, 2026-10-20) plus the user's own working limits (section "Дополнительные требования"). Status: `USER_SUPPLIED`, not re-checked on the live page. The Product Type rule in the feed template / Seller Central for the marketplace always wins; check `live-research.md` when this file is older than 90 days.

How the agent uses it: `scripts/content_check.py` enforces the machine-checkable rules (codes `TITLE_SPECIAL_CHARS`, `TITLE_RESTRICTED_PHRASE`, `BULLET_NO_CAPITAL`, `BULLET_SPECIAL_CHARS`, `BULLET_PLACEHOLDER`, `BULLET_ASIN`, `BULLET_PROHIBITED_CLAIM`, `BULLET_GUARANTEE`, `BULLET_EXTERNAL_INFO`, `BULLET_ALL_CAPS`, `BULLET_ABBREVIATION`, `BULLET_UNIT_SPACE`, `BULLET_NO_HEADER`, `BULLET_NUMBER_DIGIT`, `BULLETS_TOO_FEW`, `HIGHLIGHTS_TOO_SHORT`); the rest (claims need evidence, no dedicated-field content such as fabric, care, origin; unique information per bullet; variant consistency) is judged by the agent when writing and reviewing copy. Marketplaces outside the scope of the title rule (Saudi Arabia, Egypt, Türkiye, UAE) follow their own template.

---

## Product title requirements

Title requirements apply to all product types, except [media product types](https://sellercentral.amazon.com/help/hub/reference/GMF8CVX6S6CF8MM2), listed in all stores, except for Saudi Arabia, Egypt, Türkiye, and the United Arab Emirates. To list a product for the first time, your title must meet the requirements described below:

| Requirement type | Details |
| --- | --- |
| Character limit | Titles must not exceed 75 characters, including spaces. |
| Promotional content | Titles must not contain promotional phrases, such as "free shipping" or "100% quality guaranteed." |
| Special characters | Titles must not use the following special characters: !, $, ?, _, {, }, ^, ¬, ¦. Other special characters, such as ~, #, <, >, and *, are allowed only in specific contexts. For example, you may use these symbols as product identifiers ("Style #4301") or measurements ("<10 lb"). Decorative usage of special characters is not allowed. For example, the title “Paradise Towel Wear Co. Beach Coverup << Size Kids XXS >>” is non-compliant because of the excessive use of symbols around the size. |
| Content requirements | Titles must contain the minimum amount of information that can be used to clearly describe the product, such as "Amazon Essentials Dress," "Columbia Hiking Boots," or "Sony Headphones." Do not include restricted phrases, such as “FSA/HSA eligible.” |
| Word repetition | Titles must not contain the same word more than twice. For example, "Baby Boy Outfits Baby Boy fall Winter Clothes Baby Boy Long Sleeve Suspender Outfit Sets" is a non-compliant title. Prepositions, articles, and conjunctions may be used more than twice in a title. However, brand names are also subject to the two-instance limit. If part of a brand name appears in a different context (for example, "Old Navy and Navy Blue"), it's not considered a duplicate. |

**Note:** If your product is already listed and the title doesn't comply with these requirements or contains inaccurate information, the title might be automatically corrected or it might not appear in our search results. Policy-violating titles can be viewed directly in [Manage All Inventory](https://sellercentral.amazon.com/myinventory/inventory?fulfilledBy=all&page=1&pageSize=25&sort=date_created_desc&status=all&ref_=xx_invmgr_dnav_xx). Brand owners can also see these titles in [Review listing changes](https://sellercentral.amazon.com/myinventory/inventory/views/rlu). After you submit changes to your title or item highlights, allow 24 to 48 hours for updates to be processed and displayed on Amazon stores.

## Bullet point guidelines

Writing guidelines for high-quality bullet points:

| Component | Best practices |
| --- | --- |
| **Capitalization** | Begin with a capital letter. |
| **Bullet point count** | Include at least three bullet points. |
| **Character length** | Bullet point character limits vary by product type. |
| **Formatting** | Format as a sentence fragment, and don't use end punctuation. Use semicolons to separate phrases within a single bullet point. |
| **Numbers** | Write numbers one to nine in full, excluding names, model numbers, and measurements. |
| **Measurements** | Include a space between digit and unit (example: "60 ml"). |
| **Structure** | Add a header with a colon followed by a description (example: "Cotton fabric: Made from 100% cotton"). |
| **Content focus** | Highlight product features, benefits, and how the product meets customer needs. Avoid brand marketing stories. |
| **Content consistency** | Maintain data consistency across product variants. Minimize duplication with other product attributes such as title, product description, or product overview. |
| **Claims** | Avoid subjective, performance, or comparative claims unless they’re verifiable on packaging. Avoid unsubstantiated award claims or consumer survey results. |
| **References** | Do not divert or refer to other products not included under the ASIN. Do not compare your product to competitor brands. |

**Examples of high-quality bullet points:**

- Cotton fabric: Made from 100% cotton for softness and breathability
- Long sleeve: Long sleeves add coverage and style
- Loose fit: Relaxed fit allows for easy movement and comfort
- Machine washable: Durable construction allows for easy care
- Versatile style: Perfect for dance practice, playtime, or outdoor activity

## Дополнительные требования к Item Highlights и буллитам

Рабочие ограничения, указанные пользователем:

| Параметр | Требование |
| --- | --- |
| Item Highlights | Максимум 125 символов, включая пробелы |
| Длина одного буллита | От 10 до 255 символов |
| Лимит индексации для SEO | Алгоритм Amazon индексирует только первые 1000 байт суммарно по всем пяти буллитам |
| Эмодзи и спецсимволы | Категорически запрещены в буллитах |
| Начало буллита | Каждый буллит начинается с заглавной буквы |
| Конец буллита | Без точки на конце; формат фрагмента предложения |

**Примечание к SEO:** 1000 байт — это около 1000 символов для английского текста с однобайтовыми символами. Отсутствие эмодзи само по себе не гарантирует такое соотношение: кириллица и другие многобайтовые символы занимают больше одного байта в UTF-8. При подготовке пяти буллитов проверяйте их суммарный размер в байтах.

**Применение лимитов:** Для Item Highlights соблюдайте максимум 125 символов, включая пробелы. Общий диапазон 10–255 символов на один буллит сохранён отдельно; для буллита в поле Item Highlights применяйте более строгий диапазон 10–125 символов.

## Prohibited content


**Note:** Bullet points that contain the following information may be removed or updated.

| Prohibited element | Examples |
| --- | --- |
| **Special characters** | ™, ®, €, …, †, ‡, o, ¢, £, ¥, ©, ±, ~, â |
| **Emojis** | ☺, ☹, ✅, ❌ |
| **Placeholder text** | "not applicable," "NA," "n/a," "N/A," "not eligible," "yet to decide," "to be decided," "TBD," "copy pending" |
| **ASINs** | B00UXG4WR5 |
| **Prohibited claims** | "eco-friendly," "environmentally friendly," "ecologically friendly," "anti-microbial," "anti-bacterial," "made from bamboo," "contains bamboo," "made from soy," "contains soy." For more information, go to [General listing restrictions](https://sellercentral.amazon.com/gp/help/G201707070). |
| **Guarantee information** | "Full refund," "If not satisfied, send it back," "Unconditional guarantee with no limit" |
| **External information** | Company information, website links, external hyperlinks, contact information |
| **Repetitive content** | Same information across multiple bullet points. Each bullet point must mention unique product information. |
| **All caps** | "ELEGANT DESIGN," "MACHINE WASHABLE" |
| **Abbreviations** | "qty," "pkg," "w/," "approx." |
| **Content for dedicated fields** | Fabric content, care instructions, and country of origin. These are populated in separate fields, so don't repeat them in bullet points. |
