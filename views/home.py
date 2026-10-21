import streamlit as st

from core import loader, state, ui

ui.header("홈", "국가수탁과제 관리 도우미",
          "K-water 정산시스템과 RCMS의 비목 차이로 생기는 정산 부담을 줄이기 위한 연구원용 시범 서비스임. "
          "룰 기반 판정과 과거 집행내역으로 학습한 AI 분류를 함께 사용함.")

hm = state.get_mapper(state.model_version())
iv = state.read_interviews()
ui.card_grid([
    ("매핑 룰", f"{len(loader.mapping_rules())}개", "K-water 계정 × 적요 키워드"),
    ("AI 학습 집행건", f"{hm.model.n_train + hm.model.n_feedback:,}건", f"담당자 피드백 {hm.model.n_feedback}건 포함"),
    ("규정 지식베이스", f"{len(loader.regulations()['items'])}항목", "사용기준·KEITI 사례집 등"),
    ("접수된 의견·피드백", f"{len(iv)}건", "7개 연구소 인터뷰"),
])

ui.section("업무 단계별 바로가기")
a, b, c = st.columns(3)
with a:
    st.markdown("**① 과제 준비**")
    st.caption("전문기관별 체크리스트, 연구개발비 편성 한도 검증, 계획서 목차 초안")
    st.page_link("views/proposal.py", label="제안서 작성 도우미", icon=":material/edit_document:")
with b:
    st.markdown("**② 수행 중 집행**")
    st.caption("K-water 계정·적요를 넣으면 RCMS 비목/세목과 필요 증빙을 안내")
    st.page_link("views/mapping.py", label="비목 매핑 (K-water↔RCMS)", icon=":material/swap_horiz:")
with c:
    st.markdown("**③ 사용실적보고·정산**")
    st.caption("집행내역 일괄 점검, 현물(장비) 산정 근거와 소명서 초안")
    st.page_link("views/settlement.py", label="정산 사전점검", icon=":material/fact_check:")
    st.page_link("views/inkind.py", label="현물 적정성 점검", icon=":material/precision_manufacturing:")

ui.section("< 최근 국가 기준 개정에 따라 영향을 주는 요소 >")
st.markdown(
    "- **회의비 식비** — 2026.5.6.부터 사전 내부결재 의무가 없어지고, *참여연구자만 참석한 회의*의 식비만 계상 불가로 변경됨. "
    "5.6. 이전 집행분은 종전 기준(외부인 참석 + 사전결재)을 그대로 적용함.\n"
    "- **연구혁신비 신설** (2026.6.11. 시행) — 재료비+활동비의 10% 이내, 연 평균 5천만원 이내. RCMS에 사용목적·거래내역 입력으로 증빙을 갈음함.\n"
    "- **현물 장비** — 계획서 보유현황 미반영, 타 국가R&D 재원 장비, 사용 입증 부족, 현금 유지비와 중복이 불인정의 주된 사유임."
)
ui.note("학습데이터를 지속 보완하여 갱신함.")
