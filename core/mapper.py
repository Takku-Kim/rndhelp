"""K-water 정산시스템 집행내역 → RCMS 비목/세목 매핑 (룰 기반 + ML 병행).

판정 순서
1) 룰 엔진: K-water 계정코드 + 적요/거래처 정규식 → 우선순위가 가장 높은 룰
2) ML 분류기: TF-IDF(문자 n-gram) + 로지스틱 회귀, 과거 집행내역(=RCMS 최종 비목)로 학습
3) 결합: 둘이 일치하면 자동확정, 다르면 '검토필요', 룰이 없으면 ML 확률로 판단
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from . import loader

LABEL_SEP = "|"


def _text(account: str, description: str, vendor: str = "", acc_names: dict | None = None) -> str:
    acc_names = acc_names or {}
    return f"ACC{account} {acc_names.get(str(account), '')} {description} {vendor}".strip()


# ─────────────────────────── 룰 엔진 ───────────────────────────
@dataclass
class RuleHit:
    id: str
    name: str
    bimok: str
    semok: str
    priority: int
    warn: str = ""
    verified: bool = True
    matched: str = ""


class RuleMapper:
    def __init__(self, rules: list[dict] | None = None):
        self.rules = rules if rules is not None else loader.mapping_rules()
        self._compiled = []
        for r in self.rules:
            pats = [re.compile(p, re.IGNORECASE) for p in r.get("patterns", [])]
            excl = [re.compile(p, re.IGNORECASE) for p in r.get("exclude", [])]
            self._compiled.append((r, pats, excl))

    def match(self, account: str, description: str, vendor: str = "") -> list[RuleHit]:
        text = f"{description} {vendor}"
        hits: list[RuleHit] = []
        for r, pats, excl in self._compiled:
            accs = [str(a) for a in r.get("accounts", [])]
            if accs and str(account) not in accs:
                continue
            m = next((p for p in pats if p.search(text)), None)
            if m is None or any(e.search(text) for e in excl):
                continue
            found = m.search(text).group(0) if m.pattern != ".*" else "(계정 기준)"
            hits.append(RuleHit(r["id"], r["name"], r["bimok"], r["semok"], int(r.get("priority", 50)),
                                r.get("warn", ""), bool(r.get("verified", True)), found))
        return sorted(hits, key=lambda h: -h.priority)


# ─────────────────────────── ML 분류기 ───────────────────────────
@dataclass
class MLModel:
    pipe: Pipeline
    classes: list[str]
    holdout_acc: float
    n_train: int
    n_feedback: int = 0

    def predict_top(self, texts: list[str], k: int = 3) -> list[list[tuple[str, float]]]:
        proba = self.pipe.predict_proba(texts)
        out = []
        for row in proba:
            idx = np.argsort(row)[::-1][:k]
            out.append([(self.classes[i], float(row[i])) for i in idx])
        return out


def train_model(train: pd.DataFrame, feedback: pd.DataFrame | None = None, seed: int = 0) -> MLModel:
    acc_names = loader.account_name_map()
    df = train.copy()
    n_fb = 0
    if feedback is not None and len(feedback):
        fb = feedback[["account", "description", "vendor", "rcms_bimok", "rcms_semok"]].copy()
        n_fb = len(fb)
        df = pd.concat([df] + [fb] * 3, ignore_index=True)  # 담당자 교정 건은 가중(×3)
    df["vendor"] = df["vendor"].fillna("")
    X = [_text(a, d, v, acc_names) for a, d, v in zip(df["account"].astype(str), df["description"], df["vendor"])]
    y = (df["rcms_bimok"] + LABEL_SEP + df["rcms_semok"]).tolist()

    def make_pipe() -> Pipeline:
        return Pipeline([
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=1, sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=3000, C=8.0)),
        ])

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y)
    probe = make_pipe().fit(Xtr, ytr)
    acc = float((probe.predict(Xte) == np.array(yte)).mean())
    pipe = make_pipe().fit(X, y)
    return MLModel(pipe, list(pipe.classes_), acc, len(train), n_fb)


# ─────────────────────────── 결합 판정 ───────────────────────────
@dataclass
class MapResult:
    bimok: str
    semok: str
    status: str            # 자동확정 / 검토필요 / 불인정
    basis: str             # 룰+AI 일치 / 룰 우선 / AI 단독
    confidence: float
    rule: RuleHit | None = None
    ml_top: list[tuple[str, float]] = field(default_factory=list)
    warn: str = ""
    evidence: list[str] = field(default_factory=list)


def split_label(label: str) -> tuple[str, str]:
    b, s = label.split(LABEL_SEP, 1)
    return b, s


class HybridMapper:
    def __init__(self, model: MLModel, rules: RuleMapper | None = None, ml_threshold: float = 0.7):
        self.model = model
        self.rules = rules or RuleMapper()
        self.th = ml_threshold
        self.acc_names = loader.account_name_map()
        self.semok_idx = loader.semok_index()

    def map_one(self, account: str, description: str, vendor: str = "") -> MapResult:
        return self.map_many(pd.DataFrame([{"account": account, "description": description, "vendor": vendor}]))[0]

    def map_many(self, df: pd.DataFrame) -> list[MapResult]:
        vendors = df.get("vendor", pd.Series([""] * len(df))).fillna("").astype(str)
        texts = [_text(a, d, v, self.acc_names) for a, d, v in zip(df["account"].astype(str), df["description"].astype(str), vendors)]
        tops = self.model.predict_top(texts, k=3)
        results = []
        for (acc, desc, ven), top in zip(zip(df["account"].astype(str), df["description"].astype(str), vendors), tops):
            hits = self.rules.match(acc, desc, ven)
            rule = hits[0] if hits else None
            ml_label, ml_p = top[0]
            ml_b, ml_s = split_label(ml_label)
            if rule and rule.bimok == "불인정":
                res = MapResult(rule.bimok, rule.semok, "불인정", "룰", 1.0, rule, top, rule.warn)
            elif rule and rule.semok == ml_s:
                res = MapResult(rule.bimok, rule.semok, "자동확정" if rule.verified else "검토필요",
                                "룰+AI 일치", max(ml_p, 0.9), rule, top, rule.warn)
            elif rule:
                res = MapResult(rule.bimok, rule.semok, "검토필요", "룰 우선(AI 이견)", ml_p, rule, top,
                                (rule.warn + " " if rule.warn else "") + f"AI는 '{ml_s}'({ml_p:.0%}) 제안")
            else:
                status = "불인정" if ml_b == "불인정" else ("자동확정" if ml_p >= self.th else "검토필요")
                res = MapResult(ml_b, ml_s, status, "AI 단독", ml_p, None, top,
                                "" if ml_p >= self.th else "룰 미적용·AI 확신도 낮음 — 담당자 확인")
            info = self.semok_idx.get(res.semok, {})
            res.evidence = info.get("evidence", [])
            if info.get("limit") and not (res.rule and res.rule.warn):
                res.warn = (res.warn + " · " if res.warn else "") + info["limit"]
            results.append(res)
        return results


def results_to_frame(df: pd.DataFrame, results: list[MapResult]) -> pd.DataFrame:
    out = df.copy()
    out["RCMS 비목"] = [r.bimok for r in results]
    out["RCMS 세목"] = [r.semok for r in results]
    out["판정"] = [r.status for r in results]
    out["근거"] = [r.basis + (f" [{r.rule.id}]" if r.rule else "") for r in results]
    out["AI 확신도"] = [round(r.ml_top[0][1], 2) if r.ml_top else None for r in results]
    out["주의"] = [r.warn for r in results]
    out["필요 증빙"] = ["; ".join(r.evidence) for r in results]
    return out
