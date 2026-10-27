"""Helium 10: Xray (продукты) и Cerebro (ключевые слова) → нормализованные записи.

Особенности экспорта, которые здесь учтены:
- числа в Xray — текст с локалью: «13 138», «29 471,08», «2,45»; N/A и пустые → None;
- валюта только в заголовке («Price  €», «Fees  £»), marketplace — по домену URL;
- «Fees» — сумма комиссий Amazon (referral + FBA) при текущей цене;
- «Recent Purchases» — бейдж Amazon «X+ bought in past month»: наблюдаемая НИЖНЯЯ граница
  продаж от самого Amazon, а не оценка Helium;
- Xray категории — это верх выдачи/BSR (обычно не больше 100 строк), а не вся ниша;
- Cerebro бывает с колонками ABA Total Click/Conv. Share и без них; колонки с ASIN —
  органические позиции этих ASIN по запросу.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .xlsx import read_table

MARKETPLACE_BY_DOMAIN = {
    "amazon.de": "DE", "amazon.co.uk": "UK", "amazon.fr": "FR", "amazon.it": "IT",
    "amazon.es": "ES", "amazon.nl": "NL", "amazon.com": "US", "amazon.pl": "PL", "amazon.se": "SE",
    "amazon.com.be": "BE",
}
CURRENCY_BY_SIGN = {"€": "EUR", "£": "GBP", "$": "USD", "zł": "PLN", "kr": "SEK"}
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_ASIN = re.compile(r"^B0[A-Z0-9]{8}$")
_SPACES = re.compile(r"[\s  ]")

# Ступени бейджа «X+ bought in past month» (порядок важен: верхняя граница — следующая ступень).
BADGE_LADDER = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900,
                1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000,
                10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000]


def parse_number(v, decimal: str = ","):
    """Число из ячейки экспорта; None для пустых, N/A, «-»."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = _SPACES.sub("", str(v)).replace("%", "").replace("€", "").replace("£", "").replace("$", "")
    if s in ("", "N/A", "n/a", "-", "--", ">", "<"):
        return None
    s = s.lstrip("><+")
    if decimal == ",":
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def detect_decimal(samples) -> str:
    """Разделитель дроби по образцам цен/выручки: ',' (EU-локаль экспорта) или '.'."""
    comma = dot = 0
    for v in samples:
        if not isinstance(v, str):
            continue
        s = _SPACES.sub("", v)
        if re.search(r",\d{1,2}$", s) or ("," in s and "." in s and s.rfind(",") > s.rfind(".")):
            comma += 1
        elif re.search(r"\.\d{1,2}$", s) or ("," in s and "." in s and s.rfind(".") > s.rfind(",")):
            dot += 1
    return "." if dot > comma else ","


def parse_date(v):
    """«May 31, 2020» или ISO → date; иначе None."""
    if not v or str(v).strip() in ("N/A", "-"):
        return None
    s = str(v).strip()
    m = re.match(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),\s*(\d{4})", s)
    if m and m.group(1).lower() in _MONTHS:
        return date(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def badge_bounds(floor):
    """Бейдж «1K+» → (1000, 2000): нижняя граница и следующая ступень (верх не включён)."""
    if floor is None:
        return None
    above = [x for x in BADGE_LADDER if x > floor]
    return float(floor), float(above[0]) if above else None


@dataclass
class XrayRow:
    asin: str
    title: str
    brand: str
    marketplace: str
    currency: str
    price: float | None
    units: float | None                 # ASIN Sales, оценка Helium, шт./мес.
    revenue: float | None               # ASIN Revenue
    parent_units: float | None
    parent_revenue: float | None
    badge_floor: float | None           # Recent Purchases (Amazon), нижняя граница шт./мес.
    bsr: float | None
    rating: float | None
    reviews: float | None
    review_velocity: float | None
    images: float | None
    fees: float | None                  # referral + FBA при текущей цене
    active_sellers: float | None
    fulfillment: str                    # AMZ | FBA | MFN | N/A
    buy_box: str
    seller: str
    seller_country: str
    size_tier: str
    category: str
    dimensions_cm: list | None
    weight_kg: float | None
    created: date | None
    seller_age_months: float | None
    url: str
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def is_amazon_retail(self) -> bool:
        return self.fulfillment == "AMZ" or self.seller_country == "AMZ" or self.seller.lower() == "amazon"


@dataclass
class CerebroRow:
    phrase: str
    search_volume: float | None
    keyword_sales: float | None
    trend: float | None                 # Search Volume Trend, % к предыдущему периоду
    competing_products: float | None
    cpr: float | None                   # Cerebro Product Rank: продаж за 8 дней для топ-10
    title_density: float | None
    sponsored_asins: float | None
    aba_click_share: float | None
    aba_conv_share: float | None
    asin_ranks: dict = field(default_factory=dict)   # ASIN → органическая позиция (0/None — нет)


def _header(rows, prefix):
    for k in rows[0]:
        if k.startswith(prefix):
            return k
    return None


def _marketplace(url: str) -> str:
    host = (url or "").split("/")[2] if "//" in (url or "") else ""
    host = host.removeprefix("www.")
    return MARKETPLACE_BY_DOMAIN.get(host, "UNKNOWN")


LB_KG, OZ_KG, IN_CM = 0.45359237, 0.028349523, 2.54


def _dims(v, decimal, marketplace):
    """Габариты → см. Единица из строки («cm» / «in»); без единицы: US — дюймы, иначе см."""
    if not v or "N/A" in str(v):
        return None
    s = str(v).lower()
    nums = [n for n in (parse_number(x, decimal) for x in re.findall(r"\d[\d.,]*", s)) if n is not None]
    inches = bool(re.search(r"\b(in|inch|inches)\b|\"", s)) or ("cm" not in s and marketplace == "US")
    return [round(n * IN_CM, 2) for n in nums] if inches and nums else (nums or None)


def _weight_kg(v, header, decimal, marketplace):
    """Вес → кг. Единица из значения или заголовка («lb», «oz», «kg», «g»); без единицы: US — фунты."""
    n = parse_number(re.sub(r"[a-zA-Z]+", "", str(v)) if v is not None else None, decimal)
    if n is None:
        return None
    unit = (re.search(r"(kg|lbs?|oz|g)\b", f"{v} {header}".lower()) or [None, None])[1]
    if unit is None:
        unit = "lb" if marketplace == "US" else "kg"
    return round({"kg": n, "g": n / 1000, "lb": n * LB_KG, "lbs": n * LB_KG, "oz": n * OZ_KG}[unit], 4)


def read_xray(path: str) -> list:
    rows = read_table(path)
    if not rows or "ASIN" not in rows[0]:
        raise ValueError(f"{path}: не похоже на экспорт Helium 10 Xray (нет колонки ASIN)")
    price_col, fees_col, weight_col = _header(rows, "Price"), _header(rows, "Fees"), _header(rows, "Weight")
    sign = price_col.replace("Price", "").strip() if price_col else ""
    currency = CURRENCY_BY_SIGN.get(sign, sign or "UNKNOWN")
    dec = detect_decimal([r.get(price_col) for r in rows] + [r.get("ASIN Revenue") for r in rows])

    def num(r, k):
        return parse_number(r.get(k), dec)

    out = []
    for r in rows:
        asin = (r.get("ASIN") or "").strip()
        if not _ASIN.match(asin):
            continue
        mp = _marketplace(r.get("URL"))
        out.append(XrayRow(
            asin=asin, title=(r.get("Product Details") or "").strip(), brand=(r.get("Brand") or "").strip(),
            marketplace=mp, currency=currency,
            price=num(r, price_col), units=num(r, "ASIN Sales"), revenue=num(r, "ASIN Revenue"),
            parent_units=num(r, "Parent Level Sales"), parent_revenue=num(r, "Parent Level Revenue"),
            badge_floor=num(r, "Recent Purchases"), bsr=num(r, "BSR"), rating=num(r, "Ratings"),
            reviews=num(r, "Review Count"), review_velocity=num(r, "Review velocity"),
            images=num(r, "Images"), fees=num(r, fees_col), active_sellers=num(r, "Active Sellers"),
            fulfillment=(r.get("Fulfillment") or "N/A").strip(), buy_box=(r.get("Buy Box") or "").strip(),
            seller=(r.get("Seller") or "").strip(), seller_country=(r.get("Seller Country/Region") or "").strip(),
            size_tier=(r.get("Size Tier") or "").strip(), category=(r.get("Category") or "").strip(),
            dimensions_cm=_dims(r.get("Dimensions"), dec, mp),
            weight_kg=_weight_kg(r.get(weight_col), weight_col or "", dec, mp),
            created=parse_date(r.get("Creation Date")), seller_age_months=num(r, "Seller Age (mo)"),
            url=(r.get("URL") or "").strip(), raw=r))
    return out


def read_cerebro(path: str) -> list:
    rows = read_table(path)
    if not rows or "Keyword Phrase" not in rows[0]:
        raise ValueError(f"{path}: не похоже на экспорт Helium 10 Cerebro (нет Keyword Phrase)")
    asin_cols = [k for k in rows[0] if _ASIN.match(k)]
    dec = detect_decimal([r.get("ABA Total Click Share") for r in rows])

    def num(r, k):
        return parse_number(r.get(k), dec)

    out = []
    for r in rows:
        phrase = (r.get("Keyword Phrase") or "").strip()
        if not phrase:
            continue
        click, conv = num(r, "ABA Total Click Share"), num(r, "ABA Total Conv. Share")
        out.append(CerebroRow(
            phrase=phrase.lower(), search_volume=num(r, "Search Volume"), keyword_sales=num(r, "Keyword Sales"),
            trend=num(r, "Search Volume Trend"), competing_products=num(r, "Competing Products"),
            cpr=num(r, "CPR"), title_density=num(r, "Title Density"), sponsored_asins=num(r, "Sponsored ASINs"),
            # ABA Total Click/Conv. Share в экспорте всегда в процентах (22.2 = 22,2 %)
            aba_click_share=click / 100 if click is not None else None,
            aba_conv_share=conv / 100 if conv is not None else None,
            asin_ranks={a: num(r, a) for a in asin_cols}))
    return out
