"""Проверка claims листинга и этикетки по стоп-листу (ТЗ v1.2 §9, §16).

Группы категорий со своими стоп-листами:
- pet_feed  — корма (Reg. (EC) 767/2009, ст. 13(3));
- cosmetics — косметика (Reg. (EC) 1223/2009 ст. 20, Reg. (EU) 655/2013);
- food      — продукты и пищевые добавки (Reg. (EU) 1169/2011 ст. 7(3), Reg. (EC) 1924/2006).
Заявления о лечении/профилактике/облегчении болезни («противовоспалительный», «лечит»,
«обезболивает») дают BLOCKED (устранимо переформулировкой), а не PASS. Заявления, требующие
доказательств или пограничные с лекарством («клинически доказано», SPF, рост волос),
дают REVIEW REQUIRED. Для категорий без стоп-листа проверка не выполняется.

Это стоп-лист, а не юридическое заключение: пустой результат не значит, что claim
разрешён, он только не попал в известные запрещённые формулировки.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

CLAIMS_VERSION = "2026.10-claims2"

PROHIBITED, NEEDS_EVIDENCE = "prohibited", "needs_evidence"

# (rule_id, severity, regex по RU/EN/ES/DE/FR/IT, безопасная альтернатива)
# Общие для всех групп: лечебные заявления запрещены и для кормов, и для косметики, и для продуктов.
_ANTI_INFLAMMATORY = (
    "anti_inflammatory", PROHIBITED,
    r"противовоспалит\w*|anti[\s-]?inflammator\w*|antiinflamatori\w*|entzündungshemmend\w*|"
    r"anti[\s-]?inflammatoire\w*|antinfiammatori\w*",
    "описать эффект без медицинского термина («успокаивает», «поддерживает»)")
_PAIN_RELIEF = (
    "pain_relief", PROHIBITED,
    r"обезбол\w*|снима\w* бол\w*|pain[\s-]?relie\w*|relieves? pain|analges\w*|"
    r"alivi\w* (el )?dolor|schmerzlinder\w*|soulage\w* (la )?douleur",
    "«для комфорта»")
_CLINICALLY_PROVEN = (
    "clinically_proven", NEEDS_EVIDENCE,
    r"клинически (доказан|изучен|протестирован)\w*|clinically (proven|tested|studied)|"
    r"clínicamente (probado|demostrado)|klinisch (getestet|bewiesen|erwiesen)",
    "нужны исследования именно этой рецептуры")
_TREATS_FULL = (
    "treats_cures", PROHIBITED,
    # «treats» без контекста не ловим: в EN это ещё и «лакомства» (Joint Treats).
    r"\bлеч(ит|ение|ебн\w*)|\bизлеч\w*|\bcures?\b|\btreats? (arthritis|joint pain|inflammation|disease)|"
    r"\btreatment\b|\bheals?\b|\bcurar?\b|\bcurativ\w*|\btratamiento\b|\bheilt\b|\bheilung\b|"
    r"\bguérit\b|\btraitement\b",
    "«для поддержки …»")
# В косметике «treatment» — обычное название формата (hair treatment, treatment mask), его не ловим.
_TREATS_COSMETIC = (
    "treats_cures", PROHIBITED,
    r"\bлечит\b|\bизлеч\w*|\bcures?\b|\bheals?\b|\bcurar?\b|\bcurativ\w*|\bheilt\b|\bguérit\b",
    "описать косметический эффект («ухаживает», «смягчает»)")

_PET_FEED_PATTERNS = [
    _ANTI_INFLAMMATORY, _TREATS_FULL, _PAIN_RELIEF,
    ("prevents_disease", PROHIBITED,
     r"предотвращ\w* (артрит|артроз|заболеван|болезн)\w*|профилакт\w* (артрит|артроз|заболеван)\w*|"
     r"prevents? (arthritis|disease|osteoarthritis)|previene (la )?(artritis|artrosis|enfermedad)|"
     r"vorbeug\w*",
     "«поддерживает хрящевую ткань»"),
    ("disease_name", PROHIBITED,
     r"артрит\w*|артроз\w*|дисплази\w*|\barthritis\b|osteoarthriti\w*|\barthrosis\b|\bdysplasia\b|"
     r"\bartritis\b|\bartrosis\b|\bdisplasia\b|\barthrose\b|\bdysplasie\b",
     "упоминание болезни допустимо только в формулировке dietetic feed (Reg. (EU) 2020/354)"),
    _CLINICALLY_PROVEN,
    ("vet_endorsement", NEEDS_EVIDENCE,
     r"разработан\w* ветеринар\w*|рекомендован\w* ветеринар\w*|vet(erinarian)?s?[\s-]recommended|"
     r"(created|developed|formulated) by (specialist )?veterinarians|recomendado por veterinarios|"
     r"tierärztlich empfohlen",
     "нужен документ: кто из ветеринаров и как участвовал"),
]

# Косметика (Reg. (EC) 1223/2009 ст. 20, критерии claims Reg. (EU) 655/2013): косметика не лечит.
_COSMETIC_PATTERNS = [
    _ANTI_INFLAMMATORY, _TREATS_COSMETIC, _PAIN_RELIEF, _CLINICALLY_PROVEN,
    ("skin_disease", NEEDS_EVIDENCE,
     r"экзем\w*|псориаз\w*|дерматит\w*|\beczema\b|\bpsoriasis\b|\bdermatitis\b|\bekzem\w*|\bschuppenflechte\b|"
     r"\bneurodermitis\b|\beczéma\b|\bpsoriasi\b|\bdermatite\b",
     "лечебное заявление запрещено; «для кожи, склонной к …» — проверить формулировку"),
    ("hair_regrowth", NEEDS_EVIDENCE,
     r"рост волос|выпадени\w* волос|hair (re)?growth|regrow\w*|stops? hair loss|anti[\s-]?hair[\s-]?loss|"
     r"haarwachstum|haarausfall|chute des cheveux|caduta dei capelli|caída del cabello",
     "пограничное с лекарством (borderline): косметике допустимо «против ломкости», не «восстанавливает рост»"),
    ("antimicrobial", NEEDS_EVIDENCE,
     r"антибактериальн\w*|противогрибков\w*|antibacterial|anti[\s-]?bacterial|antifungal|anti[\s-]?fungal|"
     r"antibakteriell|antimykotisch|antibactérien|antifongique",
     "лечебное/биоцидное заявление: нужны основания и проверка статуса продукта"),
    ("spf_claim", NEEDS_EVIDENCE,
     r"\bspf\s?\d+|\buva\b|\buvb\b|lichtschutzfaktor",
     "SPF/UVA — только по протоколам испытаний (ISO 24444 / 24443, Recommendation 2006/647/EC)"),
    ("dermatologist", NEEDS_EVIDENCE,
     r"dermatolog\w* (tested|recommended|getestet|empfohlen|testé|testato|probado)|"
     r"рекомендован\w* дерматолог\w*",
     "нужен протокол исследования/документ"),
]

# Продукты и пищевые добавки для людей (Reg. (EU) 1169/2011 ст. 7(3), Reg. (EC) 1924/2006).
_FOOD_PATTERNS = [
    _ANTI_INFLAMMATORY, _TREATS_FULL, _PAIN_RELIEF, _CLINICALLY_PROVEN,
    ("prevents_disease", PROHIBITED,
     r"предотвращ\w* (заболеван|болезн|рак|диабет)\w*|prevents? (disease|cancer|diabetes|illness)|"
     r"previene (la )?enfermedad|beugt (krankheiten|krebs) vor",
     "заявления о профилактике болезней для продуктов запрещены"),
    ("unauthorised_health", NEEDS_EVIDENCE,
     r"иммунитет\w*|\bimmun\w*|\bdetox\w*|детокс\w*|fat[\s-]?burn\w*|жиросжига\w*|fettverbrenn\w*",
     "только формулировки из EU Register of health claims с условиями применения"),
]

_GROUPS = {"pet_feed": _PET_FEED_PATTERNS, "cosmetics": _COSMETIC_PATTERNS, "food": _FOOD_PATTERNS}
# Пункт Compliance Gate, на который влияет стоп-лист группы
CLAIMS_CHECK_ID = {"pet_feed": "feed_claims", "cosmetics": "cosmetic_claims", "food": "food_claims"}


def claims_group(category: str) -> str | None:
    from .compliance import COSMETICS, FOOD, PET_FEED
    c = category.lower()
    if c in PET_FEED:
        return "pet_feed"
    if c in COSMETICS:
        return "cosmetics"
    if c in FOOD:
        return "food"
    return None

# Формулировки назначений dietetic feed (Reg. (EU) 2020/354), допустимые при флаге dietetic_feed.
_DIETETIC_ALLOWED = [
    r"support of (the )?(joint )?metabolism of joints in (the )?case of osteoarthritis",
    r"support of joint metabolism in (the )?case of osteoarthritis",
    r"поддержк\w* метаболизма суставов при остеоартрите",
    r"apoyo del metabolismo de las articulaciones en caso de osteoartritis",
]

_FLAGS = re.IGNORECASE | re.UNICODE
_COMPILED = {g: [(rid, sev, re.compile(rx, _FLAGS), alt) for rid, sev, rx, alt in pats]
             for g, pats in _GROUPS.items()}
_DIETETIC = re.compile("|".join(_DIETETIC_ALLOWED), _FLAGS)


@dataclass
class ClaimFinding:
    rule_id: str
    severity: str           # prohibited | needs_evidence
    claim: str              # исходный текст claim
    match: str              # что сработало
    suggestion: str


def check_claims(claims: list, category: str, dietetic_feed: bool = False) -> list:
    """claims: строки из листинга, этикетки, изображений, A+. Возвращает находки по стоп-листу.
    Категории, для которых стоп-листа нет, возвращают пустой список."""
    group = claims_group(category)
    if group is None:
        return []
    out = []
    for claim in claims:
        text = _DIETETIC.sub(" ", claim) if dietetic_feed and group == "pet_feed" else claim
        for rid, sev, rx, alt in _COMPILED[group]:
            mo = rx.search(text)
            if mo:
                out.append(ClaimFinding(rid, sev, claim, mo.group(0), alt))
    return out


def claims_status(findings: list) -> tuple:
    """→ (status, note) для пункта feed_claims Compliance Gate. None — находок нет."""
    from .compliance import BLOCKED, REVIEW
    if not findings:
        return None, None
    prohibited = [f for f in findings if f.severity == PROHIBITED]
    shown = prohibited or findings
    note = "; ".join(f"«{f.match}» ({f.rule_id}) → {f.suggestion}" for f in shown)
    if prohibited:
        return BLOCKED, "Запрещённые claims, переформулировать: " + note
    return REVIEW, "Claims требуют подтверждения: " + note
