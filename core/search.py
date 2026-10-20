"""규정·FAQ 검색 (경량 RAG의 검색 단계).

신뢰도 표시는 연구원 RAG 지표 연구(Top1 점수·Top1–Top2 마진이 검색 충분성 판별에 유효)를 참고해
Top1 유사도와 Top1–Top2 마진으로 '근거 충분/부족'을 함께 보여준다. 임계값은 샘플 KB 기준 임시값.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import loader


@dataclass
class Hit:
    id: str
    title: str
    category: str
    text: str
    article: str
    source_name: str
    source_url: str
    score: float


class RegSearch:
    def __init__(self):
        kb = loader.regulations()
        self.sources = kb["sources"]
        self.items = kb["items"]
        docs = [f"{it['title']} {it['category']} {it['article']} {it['text']}" for it in self.items]
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3), sublinear_tf=True)
        self.M = self.vec.fit_transform(docs)

    def search(self, q: str, k: int = 4) -> tuple[list[Hit], dict]:
        sims = cosine_similarity(self.vec.transform([q]), self.M)[0]
        order = np.argsort(sims)[::-1][:k]
        hits = []
        for i in order:
            it = self.items[i]
            src = self.sources.get(it["source"], {})
            hits.append(Hit(it["id"], it["title"], it["category"], " ".join(it["text"].split()), it["article"],
                            src.get("name", it["source"]), src.get("url", ""), float(sims[i])))
        top1 = hits[0].score if hits else 0.0
        margin = top1 - (hits[1].score if len(hits) > 1 else 0.0)
        if top1 >= 0.2 and margin >= 0.03:
            level = "근거 충분"
        elif top1 >= 0.12:
            level = "근거 일부"
        else:
            level = "근거 부족 — 담당자 문의"
        return hits, {"top1": top1, "margin": margin, "level": level}

    def get(self, rid: str) -> dict | None:
        for it in self.items:
            if it["id"] == rid:
                src = self.sources.get(it["source"], {})
                return {**it, "source_name": src.get("name", ""), "source_url": src.get("url", "")}
        return None
