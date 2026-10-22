"""Отчёт: решение на первой странице, числа текста заземлены, LLM-текст проходит валидатор."""
from pathlib import Path

import pytest
from test_importers_niche import ROWS, _user, write_csv

from mia.report import build_report, money, write_report
from mia.xray_run import run_config

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def res(tmp_path):
    write_csv(tmp_path / "x.csv", ROWS)
    conf = {
        "as_of": "2026-10-20", "xray": "x.csv",
        "niche": {"niche_id": "t", "include_any": ["accelerat", "bräunungs", "tanning oil"]},
        "user": _user(),
        "hypotheses": [
            {"id": "h1", "name": "Ускоритель", "niche": {"include_any": ["accelerat"]}},
            {"id": "h2", "name": "Стик", "niche": {"include_any": ["stick"]}},
        ],
    }
    return run_config(conf, base_dir=tmp_path)


def test_report_structure_and_grounding(res):
    doc, audit = build_report(res)
    assert audit == []                                         # весь текст отчёта заземлён
    page1 = doc.split("<h2>")[0]                               # всё до первого раздела — первая страница
    assert 'class="badge' in page1 and "Волна 1 портфеля" in page1 and "Главные риски" in page1
    assert "Следующие шаги" in page1
    for section in ("Гипотезы", "Портфель", "Карточки гипотез", "Конкуренты ниши", "Чего не хватает", "Приложение"):
        assert f"<h2>{section}" in doc
    assert "WHITE SPACE" in doc and "B0AAAAAAA1" in doc
    assert "<code>niche.revenue</code>" in doc                 # метрики текста с metric_id в приложении


def test_llm_narrative_is_validated(res):
    narrative = ("Лидер продаёт {{cmp:b0aaaaaaa1.units|b0aaaaaaa2.units}}, чем второй бренд. "
                 "Новичок продаёт вдвое больше лидера. "
                 "Выручка ниши {{metric:niche.revenue}}.")
    doc, audit = build_report(res, narratives={"Комментарий аналитика": narrative})
    assert "в 3,3 раза больше" in doc                           # сравнение посчитал код
    body, appendix = doc.split('<section class="appendix">')
    assert "вдвое" not in body                                  # предложение со словесным сравнением выброшено…
    assert "вдвое" in appendix                                  # …и записано в журнал валидатора
    assert len(audit) == 1 and audit[0]["section"] == "Комментарий аналитика"
    assert "ungrounded_comparison" in audit[0]["violations"][0]


def test_html_escaping(res):
    res["results"][1]["name"] = "<script>alert(1)</script>"
    doc, _ = build_report(res)
    assert "<script>alert" not in doc and "&lt;script&gt;" in doc


def test_money_sign():
    assert money(-3790, "EUR") == "−€3 790".replace(" ", money(1000, "EUR")[2])
    assert money(None, "EUR") == "—"


def test_write_report_html(res, tmp_path):
    out = write_report(res, str(tmp_path / "r.html"))
    assert Path(out["html"]).read_text(encoding="utf-8").startswith("<!doctype html>")
    assert out["pdf"] is None
