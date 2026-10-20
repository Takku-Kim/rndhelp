"""선택적 LLM 연동 (OpenAI 호환 엔드포인트).

기본값은 '꺼짐' — 룰·템플릿만으로 동작한다. 연구원 내부 LLM 서버나 상용 API를 쓰려면
.streamlit/secrets.toml 에 아래를 넣는다 (깃에 올리지 말 것).

    [llm]
    base_url = "https://<내부 LLM 서버>/v1"
    api_key  = "..."
    model    = "<모델명>"
"""
from __future__ import annotations

import json
import urllib.request


def get_config(secrets) -> dict | None:
    try:
        cfg = dict(secrets["llm"])
        return cfg if cfg.get("base_url") and cfg.get("model") else None
    except Exception:
        return None


def chat(cfg: dict, system: str, user: str, temperature: float = 0.2, timeout: int = 60) -> str:
    body = json.dumps({
        "model": cfg["model"],
        "temperature": temperature,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(
        cfg["base_url"].rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {cfg.get('api_key', '')}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


SYSTEM_PROPOSAL = (
    "너는 한국수자원공사 연구원의 국가연구개발과제 제안서 작성 보조자다. "
    "주어진 과제 정보와 목차 항목에 맞춰 연구개발계획서 문단 초안을 한국어 개조식으로 쓴다. "
    "수치·실적은 지어내지 말고 [ ] 자리표시로 남긴다."
)
