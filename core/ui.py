"""공통 UI — K-water 내부 업무시스템 톤 (절제된 블루, 표 중심, 장식 최소화)."""
from __future__ import annotations

import html

import streamlit as st

KW_BLUE = "#005BAC"
KW_NAVY = "#0B3B6E"
KW_TEAL = "#00A0B0"

BADGE = {
    "불인정": ("#B42318", "#FDECEA"),
    "불인정 위험": ("#B42318", "#FDECEA"),
    "보완": ("#9A5B00", "#FFF4E0"),
    "보완 필요": ("#9A5B00", "#FFF4E0"),
    "검토필요": ("#9A5B00", "#FFF4E0"),
    "확인": ("#1A56A8", "#E8F0FB"),
    "적정": ("#1E6B3A", "#E6F4EA"),
    "자동확정": ("#1E6B3A", "#E6F4EA"),
}

CSS = f"""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
html, body, [class*="css"], .stMarkdown, .stTextInput, .stSelectbox, button, input, textarea {{
  font-family: 'Pretendard', 'Noto Sans KR', 'Malgun Gothic', sans-serif !important;
}}
.block-container {{ padding-top: 4rem; max-width: 1240px; }}
@media (max-width: 640px) {{
  .block-container {{ padding-top: 3.8rem; padding-left: .9rem; padding-right: .9rem; }}
  .kw-top {{ flex-direction: column; align-items: flex-start !important; gap: 2px; padding: 10px 14px !important; }}
  .kw-top .brand {{ font-size: .98rem !important; }}
  .kw-top .brand small {{ display: block; margin-left: 0 !important; }}
  .kw-top .meta {{ font-size: .72rem !important; }}
  .kw-title {{ font-size: 1.2rem !important; }}
}}
[data-testid="stSidebar"] {{ background: #F4F6F9; border-right: 1px solid #DDE3EA; }}
[data-testid="stSidebarNav"] span {{ font-size: 0.92rem; }}
.kw-top {{
  display:flex; justify-content:space-between; align-items:center;
  background:{KW_NAVY}; color:#fff; padding:16px 22px; border-radius:4px; margin-bottom:14px; gap:16px;
}}
.kw-top .sub {{ font-size:.82rem; opacity:.8; font-weight:400; }}
.kw-top .brand {{ font-weight:800; font-size:1.55rem; letter-spacing:-0.4px; line-height:1.25; }}
.kw-top .meta {{ font-size:.74rem; opacity:.7; text-align:right; line-height:1.5; }}
.kw-crumb {{ color:#6B7684; font-size:.82rem; margin:-4px 0 2px 2px; }}
.kw-title {{ font-size:1.35rem; font-weight:700; color:#16202C; margin:2px 0 4px 0; }}
.kw-desc {{ color:#4E5968; font-size:.92rem; margin-bottom:12px; }}
.kw-sec {{ border-left:4px solid {KW_BLUE}; padding-left:9px; font-weight:700; font-size:1.02rem;
          color:#16202C; margin:18px 0 8px 0; }}
.kw-card {{ background:#fff; border:1px solid #DDE3EA; border-radius:6px; padding:14px 16px; height:100%; }}
.kw-card .lbl {{ color:#6B7684; font-size:.8rem; }}
.kw-card .val {{ color:#16202C; font-size:1.45rem; font-weight:700; margin-top:2px; }}
.kw-card .sub {{ color:#8B95A1; font-size:.78rem; }}
.kw-note {{ background:#F4F8FD; border:1px solid #D6E4F5; border-radius:4px; padding:9px 12px;
           color:#2B3A4D; font-size:.86rem; }}
.kw-warn {{ background:#FFF8EC; border:1px solid #F3D9A8; border-radius:4px; padding:9px 12px;
           color:#5A4100; font-size:.86rem; }}
.kw-badge {{ display:inline-block; padding:1px 8px; border-radius:10px; font-size:.78rem; font-weight:600; }}
.kw-result {{ border:1px solid #DDE3EA; border-left:4px solid {KW_TEAL}; border-radius:6px; padding:14px 16px; background:#fff; }}
.kw-result .path {{ font-size:1.15rem; font-weight:700; color:{KW_NAVY}; }}
.kw-kv {{ color:#4E5968; font-size:.86rem; margin-top:6px; }}
.kw-foot {{ color:#8B95A1; font-size:.76rem; border-top:1px solid #E5E8EB; margin-top:28px; padding-top:8px; }}
.kw-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
@media (max-width: 640px) {{ .kw-grid {{ grid-template-columns:repeat(2,1fr); gap:8px; }} .kw-grid .kw-card .val {{ font-size:1.2rem; }} }}
div[data-testid="stMetricValue"] {{ font-size:1.4rem; }}
.stTabs [data-baseweb="tab"] {{ font-size:.92rem; }}
</style>
"""


def setup_page() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="kw-top"><div class="kw-top-l"><div class="sub">K-water 연구원 R&amp;D 지원 에이전트</div>'
        '<div class="brand">수탁과제 관리 Support 시스템</div></div>'
        '<div class="meta">RND-HELP · 시범운영<br>기준: 연구개발비 사용 기준 2026.5.6. 개정 반영</div></div>',
        unsafe_allow_html=True,
    )


def header(crumb: str, title: str, desc: str = "") -> None:
    if crumb:
        st.markdown(f'<div class="kw-crumb">{html.escape(crumb)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kw-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    if desc:
        st.markdown(f'<div class="kw-desc">{desc}</div>', unsafe_allow_html=True)


def section(title: str) -> None:
    st.markdown(f'<div class="kw-sec">{html.escape(title)}</div>', unsafe_allow_html=True)


def card(label: str, value: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="kw-card"><div class="lbl">{html.escape(label)}</div>'
        f'<div class="val">{html.escape(value)}</div><div class="sub">{html.escape(sub)}</div></div>',
        unsafe_allow_html=True,
    )


def card_grid(items: list[tuple[str, str, str]]) -> None:
    """카드 여러 개를 한 줄(모바일은 2열)로."""
    cells = "".join(
        f'<div class="kw-card"><div class="lbl">{html.escape(a)}</div><div class="val">{html.escape(b)}</div>'
        f'<div class="sub">{html.escape(c)}</div></div>' for a, b, c in items)
    st.markdown(f'<div class="kw-grid">{cells}</div>', unsafe_allow_html=True)


def badge(text: str) -> str:
    fg, bg = BADGE.get(text, ("#4E5968", "#F2F4F6"))
    return f'<span class="kw-badge" style="color:{fg};background:{bg}">{html.escape(text)}</span>'


def note(text: str, kind: str = "note") -> None:
    st.markdown(f'<div class="kw-{kind}">{text}</div>', unsafe_allow_html=True)


def footer() -> None:
    st.markdown(
        '<div class="kw-foot">본 도우미의 판정은 사전 점검용 참고 정보이며 정산 결과를 보장하지 않음. '
        '최종 판단은 연구개발계획서·협약서, 전문기관 지침과 연구지원 담당 부서 확인을 따름.</div>',
        unsafe_allow_html=True,
    )


def style_status(df, cols):
    """표의 판정/등급 열을 배지 색으로 칠한 Styler."""
    def f(v):
        fg, bg = BADGE.get(str(v), (None, None))
        return f"color:{fg};background-color:{bg};font-weight:600" if fg else ""
    cols = [c for c in ([cols] if isinstance(cols, str) else cols) if c in df.columns]
    return df.style.map(f, subset=cols).format(precision=2, thousands=",")


def won(v) -> str:
    try:
        return f"{int(v):,}원"
    except Exception:
        return "-"
