import pandas as pd
import streamlit as st

from core import export, loader, state, ui

ui.header("", "국가 수탁 R&D 단계별 지원",
          "국가 수탁 R&D의 <b>제안서 작성 → 협약 → 과제 수행 → 정산 등 全 과정</b>에서 필요한 규정 확인, 비목 매핑, "
          "정산 사전점검, 현물 적정성 점검을 지원하는 연구원용 시범 서비스.<br>"
          "(룰 기반 판정과 과거 집행내역 등을 학습한 AI 분류를 복합 적용)")



def _xlsx_mime():
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@st.dialog("AI 학습데이터", width="large")
def _train_dialog():
    st.caption("K-water 계정 + 적요 + 거래처 → RCMS 비목·세목 (AI 분류 학습에 사용하는 집행내역)")
    st.dataframe(export.train_frame(), hide_index=True, width="stretch", height=380,
                 column_config={"금액(원)": st.column_config.NumberColumn(format="localized")})
    st.download_button("엑셀로 내려받기 (xlsx)", export.train_xlsx(), "RND-HELP_AI학습데이터.xlsx",
                       mime=_xlsx_mime(), type="primary")


@st.dialog("매핑 룰", width="large")
def _rules_dialog():
    st.caption("K-water 계정 × 적요 키워드 → RCMS 비목·세목")
    df = pd.DataFrame([{"ID": r["id"], "이름": r["name"], "대상 계정": ", ".join(r.get("accounts", [])) or "전체",
                        "키워드": ", ".join(r["patterns"]), "RCMS": f"{r['bimok']} › {r['semok']}",
                        "우선순위": r.get("priority"), "검증": "✓" if r.get("verified", True) else "확인필요"}
                       for r in loader.mapping_rules()])
    st.dataframe(df, hide_index=True, width="stretch", height=420)


@st.dialog("규정 아카이브", width="large")
def _archive_dialog():
    reg = loader.regulations()
    st.caption("사용기준·KEITI 사례집 등 규정 요약")
    df = pd.DataFrame([{"구분": it["category"], "제목": it["title"], "조항": it["article"],
                        "내용": " ".join(it["text"].split()),
                        "출처": reg["sources"].get(it["source"], {}).get("name", it["source"])}
                       for it in reg["items"]])
    st.dataframe(df, hide_index=True, width="stretch", height=420)


@st.dialog("의견·피드백", width="large")
def _feedback_dialog():
    df = state.read_interviews()
    if len(df):
        st.dataframe(df.sort_values("ts", ascending=False), hide_index=True, width="stretch", height=380)
    else:
        st.caption("접수된 의견이 없음.")
    st.page_link("views/interview.py", label="연구소별 의견/피드백 공간으로 이동", icon=":material/forum:")


_DIALOGS = {"train": _train_dialog, "rules": _rules_dialog, "archive": _archive_dialog, "feedback": _feedback_dialog}
_sel = st.query_params.get("data")
if _sel in _DIALOGS:
    del st.query_params["data"]
    _DIALOGS[_sel]()

hm = state.get_mapper(state.model_version())
iv = state.read_interviews()
ui.card_grid([
    ("매핑 룰", f"{len(loader.mapping_rules())}개", "K-water 계정 × 적요 키워드", "?data=rules"),
    ("AI 학습 집행건", f"{hm.model.n_train + hm.model.n_feedback:,}건", f"담당자 피드백 {hm.model.n_feedback}건 포함", "?data=train"),
    ("규정 아카이브", f"{len(loader.regulations()['items'])}항목", "사용기준·KEITI 사례집 등", "?data=archive"),
    ("접수된 의견·피드백", f"{len(iv)}건", "7개 연구소 인터뷰 등", "?data=feedback"),
])

ui.section("업무 단계별 바로가기")
a, b, c = st.columns(3)
with a:
    st.markdown("**① 과제 준비 단계**")
    st.caption("전문기관별 체크리스트, 연구개발비 편성 한도 검증, 계획서 목차 초안")
    st.page_link("views/proposal.py", label="제안서 작성 도우미", icon=":material/edit_document:")
with b:
    st.markdown("**② 수행 중 집행 단계**")
    st.caption("K-water 계정·적요를 넣으면 RCMS 비목/세목과 필요 증빙을 안내")
    st.page_link("views/mapping.py", label="비목 매핑 (K-water↔RCMS)", icon=":material/swap_horiz:")
with c:
    st.markdown("**③ 사용실적보고·정산 단계**")
    st.caption("집행내역 일괄 점검, 현물(장비) 산정 근거와 소명서 초안")
    st.page_link("views/settlement.py", label="정산 사전점검", icon=":material/fact_check:")
    st.page_link("views/inkind.py", label="현물 적정성 점검", icon=":material/precision_manufacturing:")

ui.section("< 최근 국가 기준 개정에 따라 영향을 주는 요소(검토사항) >")
st.markdown(
    "- **회의비 식비** — 2026.5.6.부터 사전 내부결재 의무가 없어지고, *참여연구자만 참석한 회의*의 식비만 계상 불가로 변경됨. "
    "5.6. 이전 집행분은 종전 기준(외부인 참석 + 사전결재)을 그대로 적용함.\n"
    "- **연구혁신비 신설** (2026.6.11. 시행) — 재료비+활동비의 10% 이내, 연 평균 5천만원 이내. RCMS에 사용목적·거래내역 입력으로 증빙을 갈음함.\n"
    "- **현물 장비** — 계획서 보유현황 미반영, 타 국가R&D 재원 장비, 사용 입증 부족, 현금 유지비와 중복이 불인정의 주된 사유임."
)
ui.note("기준 개정에 따른 공지 및 각 소별 제시의견에 따른 학습데이터 추가 보완 및 갱신.")
