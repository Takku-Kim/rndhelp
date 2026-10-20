"""핵심 로직 회귀 테스트:  python -m pytest -q"""
from datetime import date

import pandas as pd

from core import budget, checks, inkind, loader, mapper, search


def _hm():
    return mapper.HybridMapper(mapper.train_model(loader.load_csv("train_ledger.csv")))


def test_rule_and_ml_agree_on_analysis():
    r = _hm().map_one("5260", "PFAS 의뢰분석 10시료", "한국화학융합시험연구원")
    assert r.semok == "외부 전문기술 활용비" and r.status == "자동확정"


def test_alcohol_is_rejected():
    r = _hm().map_one("5230", "과제 회식 맥주", "OO호프")
    assert r.status == "불인정"


def test_ml_covers_words_without_rule():
    r = _hm().map_one("5240", "에탄올 500mL 구입", "덕산과학")
    assert r.rule is None and r.semok == "연구재료 구입비"


def test_meeting_meal_after_rule_change():
    df = pd.DataFrame([{"date": "2026-06-03", "account": "5220", "description": "내부 회의 식사", "vendor": "",
                        "amount": 150000, "pay_method": "법인카드", "evidence": "카드전표;회의록",
                        "external_attendee": "N", "note": "", "RCMS 비목": "연구활동비", "RCMS 세목": "회의비"}])
    f = checks.run_checks(df, checks.ProjectInfo(date(2025, 1, 1), date(2026, 12, 31), 10**9, 10**8))
    assert "참여연구자만 참석한 회의 식비" in set(f["title"])


def test_inkind_other_national_rnd_flagged():
    row = loader.load_csv("sample_inkind.csv").iloc[3]  # 타 국가R&D 재원 GPU 서버
    assert inkind.evaluate(row, date(2026, 1, 1)).grade == "불인정 위험"


def test_budget_default_passes():
    _, C = budget.evaluate(budget.default_table(), 250_000, 0.5, 0.15, 0.2)
    assert all(c.ok for c in C)


def test_search_finds_meeting_rule():
    hits, _ = search.RegSearch().search("회의비 식대 참여연구원만")
    assert hits[0].id == "K03"
