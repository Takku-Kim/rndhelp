"""데이터·설정 로더. Streamlit 캐시를 쓰지 않는 순수 함수로 두고, 페이지에서 cache_data로 감싼다."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_yaml(name: str) -> dict:
    with open(DATA / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_csv(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(DATA / name, encoding="utf-8-sig", dtype={"account": str, "code": str}, **kw)


def accounts() -> pd.DataFrame:
    return load_csv("kwater_accounts.csv")


def account_name_map() -> dict[str, str]:
    df = accounts()
    return dict(zip(df["code"].astype(str), df["name"]))


def rcms_items() -> dict:
    return load_yaml("rcms_items.yaml")


def semok_index() -> dict[str, dict]:
    """세목명 → {bimok, group, evidence, limit, verified}"""
    out: dict[str, dict] = {}
    for it in rcms_items()["items"]:
        for s in it["semok"]:
            out[s["name"]] = {
                "bimok": it["bimok"],
                "group": it["group"],
                "evidence": s.get("evidence", []),
                "limit": s.get("limit", ""),
                "verified": s.get("verified", True),
            }
    return out


def regulations() -> dict:
    return load_yaml("regulations.yaml")


def agencies() -> dict:
    return load_yaml("agencies.yaml")


def mapping_rules() -> list[dict]:
    return load_yaml("mapping_rules.yaml")["rules"]


INSTITUTES = [
    "경영연구소", "수자원환경연구소", "상하수도연구소", "물인프라안전연구소",
    "물에너지연구소", "수자원위성연구소", "AI연구소",
]
