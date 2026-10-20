"""RND-HELP — K-water 국가R&D 과제관리 도우미 (Streamlit 샘플)

실행:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="RND-HELP | 국가R&D 과제관리 도우미", page_icon="assets/icon.png", layout="wide")

from core import ui  # noqa: E402

ui.setup_page()

pages = {
    "": [st.Page("views/home.py", title="홈", icon=":material/home:", default=True)],
    "과제 준비": [
        st.Page("views/proposal.py", url_path="proposal", title="제안서 작성 도우미", icon=":material/edit_document:"),
    ],
    "수행·정산": [
        st.Page("views/mapping.py", url_path="mapping", title="비목 매핑 (수공↔RCMS)", icon=":material/swap_horiz:"),
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
