"""Amazon Market Intelligence Agent — детерминированное расчётное ядро (ТЗ v1.2).

Модули:
    economics   — налоговая база, комиссии, юнит-экономика, break-even, запасы (§10, §11)
    cashflow    — помесячный cash-flow, сценарии, стресс-тесты, разгон (§11.3, §11.4, §12.1)
    contestable — Contestable Market Engine и когорты новых входов (§5.1, §5.2)
    buybox      — Buy Box Engine для Resale (§5.3)
    compliance  — Compliance Gate (§16)
    claims      — стоп-лист claims (корма EU) для Compliance Gate (§9, §16)
    factcheck   — проверка сравнений и состава конкурентов в тексте, моделей в карточках (§20.3)
    confidence  — уверенность по слабому звену (§15.2)
    score       — Niche Opportunity Score (§14.2)
    decision    — Decision Engine R0–R5 (§15.3)
    grounding   — числовое заземление LLM-текста (§20.3)
    pipeline    — сквозной анализ → Decision Package (§22.3)
    importers   — чтение Helium 10 Xray / Cerebro (§17)
    niche       — определение ниши, контроль качества, метрики, вход для pipeline (§3, §18)
    xray_run    — прогон ниши и продуктовых гипотез по выгрузкам (§13, §14.1)
    categories  — профили категорий: распознавание, compliance-ключ, стартовый referral (§11.1, §16)
    scan        — скрининг папки выгрузок Xray по всем категориям (§14)
    evidence    — правила доказательности продуктовой гипотезы (§5.2, §7, §13)
    portfolio   — минимальный работающий набор SKU, волны, каннибализация (§13, §14.1)
    report      — отчёт HTML/PDF: решение на первой странице, заземлённый текст (§19, §20.3)
"""
__version__ = "0.1.0"
