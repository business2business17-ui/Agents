"""Compliance Gate — структурированный чек-лист (ТЗ v1.2 §16).

Закрывает проблему P15 (и часть P1): пункты выбираются по marketplace, категории и
бизнес-модели; непроверенный пункт = REVIEW REQUIRED, а не PASS. Агент не даёт
юридическое заключение — только статус чек-листа и список документов.
Применимость требований нужно периодически сверять (rules_version).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .claims import CLAIMS_CHECK_ID, CLAIMS_VERSION, check_claims, claims_group, claims_status

RULES_VERSION = "2026.10-rules3"

EU = {"DE", "FR", "IT", "ES", "NL", "PL", "SE", "BE", "IE"}
UK = {"UK", "GB"}
US = {"US"}
ALL = EU | UK | US

COSMETICS = {"cosmetics", "beauty", "personal_care", "fragrance", "skincare"}
HAZMAT_CATEGORIES = {"fragrance", "aerosol"}
ELECTRONICS = {"electronics"}
# Корма и кормовые добавки для животных (complementary / dietetic feed), не ветпрепараты.
PET_FEED = {"pet_supplements", "pet_feed", "pet_food"}
FOOD = {"food", "grocery", "food_supplements"}          # продукты и пищевые добавки для людей
TOYS = {"toys"}
CHILDREN = {"toys", "baby"}
KITCHEN = {"kitchen"}                                   # плюс флаг food_contact для любой категории
APPAREL = {"apparel"}

PASS, REVIEW, BLOCKED, NA = "PASS", "REVIEW REQUIRED", "BLOCKED", "N/A"
_SEVERITY = {NA: 0, PASS: 1, REVIEW: 2, BLOCKED: 3}


@dataclass(frozen=True)
class Rule:
    check_id: str
    title: str
    markets: frozenset
    documents: tuple
    categories: frozenset | None = None     # None — любые категории
    flag: str | None = None                 # нужен флаг товара (hazmat, batteries, ...)
    models: frozenset = frozenset({"private_label", "resale"})
    exclude_categories: frozenset = frozenset()
    require_flag: str | None = None         # дополнительно к категории (И), например dietetic_feed


def _r(cid, title, markets, docs, categories=None, flag=None, models=None, exclude=None,
       require_flag=None):
    return Rule(cid, title, frozenset(markets), tuple(docs),
                frozenset(categories) if categories else None, flag,
                frozenset(models) if models else frozenset({"private_label", "resale"}),
                frozenset(exclude or ()), require_flag)


RULES = [
    # Общие
    _r("brand_rights", "Право продавать бренд", ALL,
       ["Регистрация товарного знака / Brand Registry"], models={"private_label"}),
    _r("resale_authorization", "Право перепродажи бренда", ALL,
       ["Письмо-авторизация дистрибьютора", "Инвойсы цепочки поставок"], models={"resale"}),
    _r("category_ungating", "Category / brand approval (gating)", ALL,
       ["Статус approval в Seller Central"]),
    _r("dangerous_goods", "Dangerous Goods / hazmat review FBA", ALL,
       ["SDS (паспорт безопасности)", "Результат hazmat review"],
       categories=HAZMAT_CATEGORIES, flag="hazmat"),
    _r("ip_content", "Права на контент и товарные знаки", ALL,
       ["Права на фото/тексты", "Проверка конфликтов ТЗ"]),
    _r("variation_policy", "Соответствие variation policy", ALL,
       ["План вариаций против правил категории"], models={"private_label"}),
    _r("supply_chain_docs", "Документы поставщика и происхождение", ALL,
       ["Инвойсы", "Сертификат происхождения (если нужен)"]),
    # EU / UK
    _r("vat_registration", "Регистрация НДС в странах продаж и хранения (Pan-EU/OSS)", EU | UK,
       ["VAT-номера стран хранения/продаж"]),
    _r("epr_packaging", "EPR: упаковка (регистрационный номер)", {"DE", "FR", "ES"},
       ["Регистрационный номер EPR упаковки"]),
    _r("epr_weee", "EPR: электрооборудование (WEEE)", EU, ["Регистрационный номер WEEE"],
       categories=ELECTRONICS),
    _r("epr_batteries", "EPR: батареи", EU, ["Регистрационный номер по батареям"], flag="batteries"),
    # GPSR не распространяется на корма (Reg. (EU) 2023/988, ст. 2(2)) — для них свои правила ниже.
    _r("gpsr", "GPSR: ответственный экономический оператор в EU и маркировка", EU,
       ["Данные ответственного лица в EU", "Маркировка производителя/импортёра"], exclude=PET_FEED),
    _r("cosmetics_rp_cpnp", "Косметика EU: Responsible Person, CPNP, PIF", EU,
       ["Responsible Person", "Номер уведомления CPNP", "PIF / отчёт о безопасности"],
       categories=COSMETICS),
    _r("cosmetics_scpn", "Косметика UK: Responsible Person, SCPN", UK,
       ["UK Responsible Person", "Уведомление SCPN"], categories=COSMETICS),
    _r("cosmetics_labeling", "Маркировка косметики (INCI, язык страны)", EU | UK,
       ["Макет этикетки с INCI на языке рынка"], categories=COSMETICS),
    # US
    _r("mocra", "Косметика US: MoCRA (регистрация предприятия, листинг продукта)", US,
       ["Регистрация предприятия", "Product listing"], categories=COSMETICS),
    _r("prop65", "California Prop 65 (при применимости)", US, ["Оценка применимости / предупреждение"]),
    # Все рынки, косметика
    _r("cosmetic_claims", "Claims соответствуют требованиям к косметике", ALL,
       ["Перечень claims и подтверждения"], categories=COSMETICS),
    # Электроника
    _r("electronics_ce", "Электроника EU: CE (LVD 2014/35/EU, EMC 2014/30/EU, RED 2014/53/EU), RoHS 2011/65/EU",
       EU, ["EU DoC", "Протоколы испытаний", "Маркировка CE"], categories=ELECTRONICS),
    _r("electronics_ukca", "Электроника UK: UKCA/CE, UK DoC", UK, ["UK DoC", "Маркировка"], categories=ELECTRONICS),
    _r("electronics_fcc", "Электроника US: FCC (Part 15 / ID)", US, ["FCC SDoC или FCC ID"], categories=ELECTRONICS),
    # Игрушки и детские товары
    _r("toy_safety", "Игрушки EU: Toy Safety Directive 2009/48/EC — CE, EN 71, предупреждения", EU,
       ["Протоколы EN 71", "EU DoC", "Маркировка CE и предупреждения на языке рынка"], categories=TOYS),
    _r("toy_safety_uk", "Игрушки UK: Toys (Safety) Regulations 2011 — UKCA/CE", UK,
       ["Протоколы испытаний", "UK DoC", "Маркировка"], categories=TOYS),
    _r("cpsia_children", "US: CPSIA — Children's Product Certificate, испытания в аккредитованной "
       "лаборатории, tracking label", US, ["CPC", "Протоколы CPSC-аккредитованной лаборатории"],
       categories=CHILDREN),
    # Контакт с пищей
    _r("food_contact", "Материалы для контакта с пищей (Reg. (EC) 1935/2004; пластик — Reg. (EU) 10/2011)",
       EU | UK, ["Декларация соответствия", "Протоколы миграции"], categories=KITCHEN, flag="food_contact"),
    # Продукты и пищевые добавки для людей
    _r("food_business_registration", "Регистрация пищевого бизнеса (Reg. (EC) 852/2004)", EU | UK,
       ["Регистрация производителя/импортёра"], categories=FOOD),
    _r("food_labelling", "Маркировка пищевых продуктов (Reg. (EU) 1169/2011), язык рынка", EU | UK,
       ["Макет этикетки"], categories=FOOD),
    _r("food_supplement_notification", "Пищевые добавки: уведомление национального органа "
       "(Directive 2002/46/EC)", EU | UK, ["Номер/подтверждение уведомления"], categories=FOOD,
       require_flag="food_supplement"),
    _r("food_claims", "Claims продуктов: только разрешённые nutrition/health claims (Reg. (EC) 1924/2006), "
       "без заявлений о лечении/профилактике болезней", EU | UK,
       ["Матрица claims со ссылками на EU Register"], categories=FOOD),
    _r("fda_food", "US: FDA food facility registration и маркировка (для добавок — DSHEA)", US,
       ["FDA registration number", "Макет этикетки"], categories=FOOD),
    # Текстиль
    _r("textile_labelling", "Маркировка состава текстиля (Reg. (EU) 1007/2011)", EU,
       ["Этикетка состава волокон"], categories=APPAREL),
    _r("textile_labelling_us", "US: Textile Fiber Products Identification Act (FTC)", US,
       ["Этикетка: состав, страна, идентификатор"], categories=APPAREL),
    # EU / UK, корма для животных
    _r("feed_business_registration", "Регистрация оператора кормового бизнеса (Reg. (EC) 183/2005)",
       EU | UK, ["Номер регистрации FBO производителя", "Номер регистрации импортёра/дистрибьютора в EU"],
       categories=PET_FEED),
    _r("feed_ingredients", "Ингредиенты разрешены: Catalogue of feed materials (Reg. (EU) 68/2013) "
       "или Register of feed additives (Reg. (EC) 1831/2003)", EU | UK,
       ["Спецификация рецептуры с правовым статусом каждого ингредиента"], categories=PET_FEED),
    _r("feed_labelling", "Маркировка корма (Reg. (EC) 767/2009): тип корма, состав, аналитические "
       "компоненты, добавки, дозировка, язык страны продаж", EU | UK,
       ["Макет этикетки на языке рынка"], categories=PET_FEED),
    _r("feed_claims", "Claims корма без лечебных/профилактических заявлений (Reg. (EC) 767/2009, ст. 13)",
       EU | UK, ["Матрица claims (листинг, этикетка, изображения, A+) и подтверждения"],
       categories=PET_FEED),
    _r("feed_dietetic", "Dietetic feed (PARNUTS, Reg. (EU) 2020/354): назначение, обязательные "
       "характеристики, срок применения, рекомендация ветеринара", EU | UK,
       ["Обоснование соответствия назначению из списка 2020/354"], categories=PET_FEED,
       require_flag="dietetic_feed"),
]


@dataclass
class CheckResult:
    check_id: str
    title: str
    status: str
    removable: bool
    required_documents: list
    evidence_ref: str | None = None
    note: str | None = None


@dataclass
class ComplianceResult:
    overall: str                     # PASS | REVIEW REQUIRED | BLOCKED
    hard_block: bool                 # есть неустранимый BLOCKED → NO-GO (R1)
    items: list = field(default_factory=list)
    rules_version: str = RULES_VERSION
    claim_findings: list = field(default_factory=list)

    def open_items(self):
        return [i for i in self.items if i.status in (REVIEW, BLOCKED)]

    def as_dict(self) -> dict:
        return {"overall": self.overall, "hard_block": self.hard_block,
                "rules_version": self.rules_version, "claims_version": CLAIMS_VERSION,
                "items": [i.__dict__ for i in self.items],
                "claim_findings": self.claim_findings}


def applicable_rules(marketplace: str, category: str, business_model: str, flags: dict) -> list:
    mp, cat = marketplace.upper(), category.lower()
    out = []
    for r in RULES:
        if mp not in r.markets or business_model not in r.models or cat in r.exclude_categories:
            continue
        if r.require_flag and not flags.get(r.require_flag):
            continue
        cat_hit = r.categories is not None and cat in r.categories
        flag_hit = r.flag is not None and bool(flags.get(r.flag))
        if r.categories is None and r.flag is None:
            out.append(r)
        elif cat_hit or flag_hit:
            out.append(r)
    return out


def run_compliance(marketplace: str, category: str, business_model: str,
                   flags: dict | None = None, statuses: dict | None = None,
                   claims: list | None = None) -> ComplianceResult:
    """statuses: {check_id: {"status": PASS|REVIEW REQUIRED|BLOCKED|N/A, "removable": bool,
    "evidence_ref": str, "note": str}}. Отсутствующий пункт → REVIEW REQUIRED.
    claims: тексты claims листинга/этикетки. Находки стоп-листа (claims.py) перекрывают статус
    пункта claims своей группы (feed_claims / cosmetic_claims / food_claims), даже если он PASS."""
    flags, statuses = flags or {}, statuses or {}
    findings = check_claims(claims or [], category, bool(flags.get("dietetic_feed")))
    claim_status, claim_note = claims_status(findings)
    claim_check = CLAIMS_CHECK_ID.get(claims_group(category))
    items = []
    for r in applicable_rules(marketplace, category, business_model, flags):
        s = statuses.get(r.check_id, {})
        status = s.get("status", REVIEW)
        if status not in (PASS, REVIEW, BLOCKED, NA):
            raise ValueError(f"{r.check_id}: unknown status {status}")
        removable = bool(s.get("removable", True))
        if r.check_id == claim_check and claim_status and _SEVERITY[claim_status] > _SEVERITY[status]:
            status, note, removable = claim_status, claim_note, True   # устраняется переформулировкой
        elif status == PASS and not s.get("evidence_ref"):
            status, note = REVIEW, "PASS без evidence_ref не принимается."
        else:
            note = s.get("note")
        items.append(CheckResult(r.check_id, r.title, status, removable,
                                 list(r.documents), s.get("evidence_ref"), note))
    unknown = set(statuses) - {i.check_id for i in items}
    if unknown:
        items.append(CheckResult("_unknown", "Статусы для неприменимых пунктов", NA, True, [],
                                 note=f"Проигнорированы: {sorted(unknown)}"))
    hard = any(i.status == BLOCKED and not i.removable for i in items)
    if any(i.status == BLOCKED for i in items):
        overall = BLOCKED
    elif any(i.status == REVIEW for i in items):
        overall = REVIEW
    else:
        overall = PASS
    return ComplianceResult(overall, hard, items, claim_findings=[f.__dict__ for f in findings])
