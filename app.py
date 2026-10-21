"""RND-HELP — K-water 국가R&D 과제관리 도우미 (Streamlit 샘플)

실행:  streamlit run app.py
"""
import hashlib
import sys
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="국가 수탁 관리 시스템 | K-water 연구원", page_icon="assets/icon.png", layout="wide")

# 클라우드에서 새 코드가 반영될 때 core 모듈이 옛 버전으로 남아 있으면(AttributeError 등)
# core/*.py 내용이 바뀐 것을 감지해 강제로 다시 불러온다.
_CORE = Path(__file__).parent / "core"
_SIG = hashlib.md5(b"".join(p.read_bytes() for p in sorted(_CORE.glob("*.py")))).hexdigest()
if getattr(sys.modules.get("core"), "_SIG", None) != _SIG:
    for _m in [m for m in list(sys.modules) if m == "core" or m.startswith("core.")]:
        sys.modules.pop(_m, None)

import core  # noqa: E402
from core import ui  # noqa: E402

core._SIG = _SIG

ui.setup_page()

pages = {
    "": [st.Page("views/home.py", title="홈", icon=":material/home:", default=True)],
    "과제 준비": [
        st.Page("views/proposal.py", url_path="proposal", title="제안서 작성 도우미", icon=":material/edit_document:"),
    ],
    "수행·정산": [
        st.Page("views/mapping.py", url_path="mapping", title="비목 매핑 (K-water↔RCMS)", icon=":material/swap_horiz:"),
        st.Page("views/settlement.py", url_path="settlement", title="정산 사전점검", icon=":material/fact_check:"),
        st.Page("views/inkind.py", url_path="inkind", title="현물 적정성 점검", icon=":material/precision_manufacturing:"),
    ],
    "지원": [
        st.Page("views/rules.py", url_path="rules", title="규정·FAQ 검색", icon=":material/search:"),
        st.Page("views/interview.py", url_path="interview", title="연구소 애로사항 접수", icon=":material/forum:"),
    ],
}

with st.sidebar:
    st.caption("K-water 연구원 · AI연구소")

nav = st.navigation(pages)
nav.run()
ui.footer()
