"""의견·피드백 저장소 — 유실 방지.

Streamlit Community Cloud 의 파일시스템은 재시작·재배포 때 초기화되므로, 접수 내용은
(1) 비공개 GitHub 데이터 저장소(.streamlit/secrets.toml 의 [storage])에 접수 즉시 커밋하고,
(2) 로컬 파일에도 함께 기록한다. [storage] 가 없으면 로컬 파일만 쓰며 화면에 경고를 띄운다.

secrets.toml 예:
    [storage]
    repo   = "newcave/rndhelp-data"   # 반드시 비공개(private) 저장소
    token  = "github_pat_..."         # 해당 저장소 Contents: Read and write 권한만 부여
    branch = "main"
    dir    = ""                       # 하위 폴더 (선택)
"""
from __future__ import annotations

import base64
import io

import pandas as pd
import requests
import streamlit as st

from . import loader

API = "https://api.github.com"


def _cfg() -> dict | None:
    try:
        c = st.secrets.get("storage")
    except Exception:
        return None
    if c and c.get("repo") and c.get("token"):
        return dict(c)
    return None


def mode() -> str:
    return "github" if _cfg() else "local"


def _url(cfg: dict, name: str) -> str:
    path = f"{cfg.get('dir', '').strip('/')}/{name}".lstrip("/")
    return f"{API}/repos/{cfg['repo']}/contents/{path}"


def _headers(cfg: dict) -> dict:
    return {"Authorization": f"Bearer {cfg['token']}", "Accept": "application/vnd.github+json"}


def _remote_get(cfg: dict, name: str):
    """(DataFrame | None, sha | None). 파일이 없으면 (None, None)."""
    r = requests.get(_url(cfg, name), headers=_headers(cfg), params={"ref": cfg.get("branch", "main")}, timeout=15)
    if r.status_code == 404:
        return None, None
    r.raise_for_status()
    j = r.json()
    raw = base64.b64decode(j["content"]).decode("utf-8-sig")
    return pd.read_csv(io.StringIO(raw), dtype=str, keep_default_na=False), j["sha"]


def _remote_put(cfg: dict, name: str, df: pd.DataFrame, sha: str | None, msg: str) -> None:
    body = {"message": msg, "branch": cfg.get("branch", "main"),
            "content": base64.b64encode(df.to_csv(index=False).encode("utf-8-sig")).decode()}
    if sha:
        body["sha"] = sha
    r = requests.put(_url(cfg, name), headers=_headers(cfg), json=body, timeout=20)
    r.raise_for_status()


def _local_path(name: str):
    return loader.DATA / name


def _read_local(name: str, **kw) -> pd.DataFrame:
    p = _local_path(name)
    return pd.read_csv(p, encoding="utf-8-sig", **kw) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=20, show_spinner=False)
def _cached_remote(name: str, _cfg_key: str):
    df, _ = _remote_get(_cfg(), name)
    return df


def read(name: str, **kw) -> pd.DataFrame:
    """원격 저장소가 있으면 원격 우선, 실패하거나 없으면 로컬 파일."""
    cfg = _cfg()
    if cfg:
        try:
            df = _cached_remote(name, cfg["repo"])
            if df is not None:
                return df
        except Exception:
            pass
    return _read_local(name, **kw)


def append(name: str, row: dict) -> tuple[bool, str]:
    """행 추가. (영구 저장 성공 여부, 메시지). 로컬 파일에는 항상 기록."""
    cfg = _cfg()
    ok, msg = False, "영구 저장소 미연결 — 서버 임시 파일에만 저장됨. 접수 내역을 반드시 내려받아 보관할 것."
    if cfg:
        try:
            for attempt in range(2):
                cur, sha = _remote_get(cfg, name)
                if cur is None:
                    cur = _read_local(name, dtype=str).fillna("")
                new = pd.concat([cur, pd.DataFrame([row]).astype(str)], ignore_index=True)
                try:
                    _remote_put(cfg, name, new, sha, f"data: {name} 1건 추가")
                    break
                except requests.HTTPError as e:
                    if e.response is not None and e.response.status_code in (409, 422) and attempt == 0:
                        continue  # 동시 접수로 sha 충돌 → 최신본 다시 읽어 재시도
                    raise
            _cached_remote.clear()
            ok, msg = True, "영구 저장소에 저장됨."
            local = new
        except Exception as e:  # 네트워크·권한 오류
            msg = f"영구 저장소 저장 실패({type(e).__name__}) — 서버 임시 파일에만 저장됨. 내려받아 보관할 것."
            local = pd.concat([_read_local(name, dtype=str).fillna(""), pd.DataFrame([row]).astype(str)], ignore_index=True)
    else:
        local = pd.concat([_read_local(name, dtype=str).fillna(""), pd.DataFrame([row]).astype(str)], ignore_index=True)
    try:
        local.to_csv(_local_path(name), index=False, encoding="utf-8-sig")
    except Exception:
        pass
    return ok, msg
