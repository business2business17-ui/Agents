"""Профили категорий Amazon (ТЗ v1.2 §11.1, §16).

Агент не привязан к одной категории: категория ниши определяется по колонке Category
выгрузки (или задаётся пользователем) и выбирает:
- ключ для Compliance Gate и стоп-листа claims;
- стартовую ставку referral, если пользователь не передал fee schedule.

Ставки referral здесь — СТАРТОВЫЕ значения для отсутствующей fee schedule, а не
сверенные данные: у них нет checked_at, поэтому pipeline предупреждает «fee schedule не
сверялась». Перед решением их заменяют актуальной таблицей marketplace.
"""
from __future__ import annotations

import re
from collections import Counter

DEFAULTS_VERSION = "DEFAULT-UNVERIFIED-2026-10"
EU_UK = {"DE", "FR", "IT", "ES", "NL", "PL", "SE", "BE", "IE", "UK"}

# Внутренний ключ → (названия категорий Amazon / Helium на разных языках, в нижнем регистре)
_ALIASES = {
    "cosmetics": ["beauty", "luxury beauty", "kosmetik", "beauté et parfum", "beauté", "bellezza",
                  "belleza", "beauty & personal care", "premium beauty"],
    "personal_care": ["health & personal care", "drogerie & körperpflege", "drogerie",
                      "hygiène et santé", "salute e cura della persona", "salud y cuidado personal",
                      "health & household"],
    "pet_supplies": ["pet supplies", "haustier", "haustierbedarf", "animalerie", "prodotti per animali",
                     "productos para mascotas"],
    "grocery": ["grocery", "grocery & gourmet food", "lebensmittel & getränke", "lebensmittel",
                "epicerie", "alimentari e cura della casa", "alimentación y bebidas"],
    "baby": ["baby", "baby products", "baby-produkte", "bébé et puériculture", "prima infanzia", "bebé"],
    "toys": ["toys", "toys & games", "spielzeug", "jeux et jouets", "giochi e giocattoli", "juguetes y juegos"],
    "kitchen": ["kitchen", "home & kitchen", "küche, haushalt & wohnen", "küche & haushalt",
                "cuisine et maison", "casa e cucina", "hogar y cocina"],
    "home": ["home", "home improvement", "baumarkt", "garden", "garten", "bricolage", "fai da te",
             "bricolaje y herramientas", "patio, lawn & garden"],
    "electronics": ["electronics", "elektronik & foto", "elektronik", "high-tech", "elettronica",
                    "electrónica", "computers", "computer & zubehör", "cell phones & accessories"],
    "sports": ["sports", "sports & outdoors", "sport & freizeit", "sports et loisirs", "sport e tempo libero",
               "deportes y aire libre"],
    "apparel": ["clothing", "fashion", "clothing, shoes & jewelry", "bekleidung", "vêtements",
                "abbigliamento", "ropa", "moda"],
}
_INDEX = {name: key for key, names in _ALIASES.items() for name in names}

# Внутренний ключ → категория для Compliance Gate (compliance.py)
COMPLIANCE_CATEGORY = {
    "cosmetics": "cosmetics", "personal_care": "personal_care", "pet_supplies": "pet_supplements",
    "grocery": "food", "baby": "baby", "toys": "toys", "kitchen": "kitchen", "home": "home",
    "electronics": "electronics", "sports": "sports", "apparel": "apparel",
}

# Стартовые ставки referral (доля от gross-цены). kind=whole: ставка ступени применяется ко всей цене.
# Ключ рынка: "EU" (включая UK) или "US". None — стартового значения нет, нужна fee schedule.
_REFERRAL = {
    "cosmetics":     {"EU": [[10, 0.08], [None, 0.15]], "US": [[10, 0.08], [None, 0.15]]},
    "personal_care": {"EU": [[10, 0.08], [None, 0.15]], "US": [[10, 0.08], [None, 0.15]]},
    "baby":          {"EU": [[10, 0.08], [None, 0.15]], "US": [[10, 0.08], [None, 0.15]]},
    "grocery":       {"EU": [[10, 0.08], [None, 0.15]], "US": [[15, 0.08], [None, 0.15]]},
    "pet_supplies":  {"EU": [[None, 0.15]], "US": [[None, 0.15]]},
    "toys":          {"EU": [[None, 0.15]], "US": [[None, 0.15]]},
    "kitchen":       {"EU": [[None, 0.15]], "US": [[None, 0.15]]},
    "home":          {"EU": [[None, 0.15]], "US": [[None, 0.15]]},
    "sports":        {"EU": [[None, 0.15]], "US": [[None, 0.15]]},
    "electronics":   {"EU": [[None, 0.07]], "US": [[None, 0.08]]},
    "apparel":       None,     # ступени зависят от цены и рынка — только из fee schedule
}


def normalize_category(name: str | None) -> str:
    """Название категории Amazon/Helium → внутренний ключ; неизвестное → 'other'."""
    if not name:
        return "other"
    n = re.sub(r"\s+", " ", name.strip().lower())
    if n in _INDEX:
        return _INDEX[n]
    if n in _ALIASES:
        return n
    for alias, key in _INDEX.items():
        if alias in n:
            return key
    return "other"


def detect_category(category_names: list) -> tuple:
    """Мода категорий выгрузки → (ключ, доля строк, все категории). Пустые не считаются."""
    keys = Counter(normalize_category(c) for c in category_names if c)
    if not keys:
        return "other", 0.0, {}
    key, n = keys.most_common(1)[0]
    return key, n / sum(keys.values()), dict(keys)


def compliance_category(key: str) -> str:
    return COMPLIANCE_CATEGORY.get(key, key)


def default_referral(key: str, marketplace: str) -> dict | None:
    """Стартовое правило referral для fees.referral или None."""
    table = _REFERRAL.get(key)
    if not table:
        return None
    region = "US" if marketplace.upper() == "US" else "EU" if marketplace.upper() in EU_UK else None
    tiers = table.get(region) if region else None
    if tiers is None:
        return None
    return {"kind": "whole", "tiers": tiers, "min_fee": 0.30}
