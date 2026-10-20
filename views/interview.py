from datetime import datetime

import pandas as pd
import streamlit as st

from core import loader, state, ui

ui.header("지원 › 연구소 애로사항 접수", "연구소별 정산 애로사항 접수",
          "연구소 인터뷰 내용을 같은 양식으로 모아 룰·체크리스트·학습데이터 보완에 씁니다.")

with st.expander("인터뷰 질문지 (진행자용)"):
    st.markdown(
        "1. 최근 2년간 수행한 국가과제와 전문기관은?\n"
        "2. 수공 정산시스템 계정과 RCMS 비목이 달라 **입력을 망설였던 집행 유형**은? (예: 지급수수료로 처리한 분석의뢰·특허·플랫폼 이용료)\n"
        "3. 정산(사용실적보고·정산기관 검토)에서 **불인정·보완 요청을 받은 항목**과 사유는?\n"
        "4. **현물(장비·인건비)** 관련해 정산 담당자·회계사와 이견이 있었던 사례는? 산정 방식은 무엇이었나?\n"
        "5. 제안 단계에서 미리 알았으면 좋았을 편성·서식 사항은?\n"
        "6. 이 도우미에 꼭 있었으면 하는 기능은?"
    )

with st.form("iv", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    inst = c1.selectbox("연구소", loader.INSTITUTES)
    agency = c2.selectbox("전문기관", ["KEITI", "KAIA", "NRF", "KETEP", "기타"])
    stage = c3.selectbox("단계", ["제안", "수행(집행)", "사용실적보고", "정산·이의신청"])
    c4, c5 = st.columns([1, 2])
    kind = c4.selectbox("유형", ["비목 매핑 혼선", "현물 불인정·이견", "증빙 보완 요청", "편성 한도", "서식·제출", "기타"])
    acct = c5.text_input("관련 수공 계정 / RCMS 비목 (선택)", placeholder="예: 5260 지급수수료 → 외부 전문기술 활용비?")
    body = st.text_area("상황 설명", placeholder="무엇이 어려웠는지, 어떤 지적을 받았는지")
    idea = st.text_area("개선 아이디어 (선택)", height=70)
    who = st.text_input("작성자 (선택)")
    if st.form_submit_button("접수", type="primary"):
        if not body.strip():
            st.warning("상황 설명을 입력해 주세요.")
        else:
            row = {"ts": datetime.now().isoformat(timespec="seconds"), "연구소": inst, "전문기관": agency, "단계": stage,
                   "유형": kind, "관련 비목": acct, "상황": body, "개선": idea, "작성자": who}
            df = pd.concat([state.read_interviews(), pd.DataFrame([row])], ignore_index=True)
            df.to_csv(state.INTERVIEWS, index=False, encoding="utf-8-sig")
            st.success("접수했습니다.")

df = state.read_interviews()
ui.section(f"접수 현황 ({len(df)}건)")
if len(df):
    c1, c2 = st.columns(2)
    with c1:
        st.bar_chart(df["연구소"].value_counts(), horizontal=True, color="#005BAC")
    with c2:
        st.bar_chart(df["유형"].value_counts(), horizontal=True, color="#00A0B0")
    st.dataframe(df.sort_values("ts", ascending=False), hide_index=True, width="stretch")
    st.download_button("접수 내역 내려받기 (csv)", df.to_csv(index=False).encode("utf-8-sig"), "rndhelp_interviews.csv")
ui.note("Streamlit Community Cloud에 올리면 앱 재시작 시 파일 저장 내용이 지워질 수 있습니다. "
        "시범 기간에는 주기적으로 CSV를 내려받거나, 운영 시 DB(예: 연구원 서버의 SQLite/PostgreSQL)로 바꾸세요.")
