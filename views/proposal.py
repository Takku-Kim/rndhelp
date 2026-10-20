import pandas as pd
import streamlit as st

from core import budget, llm, loader, state, ui

ui.header("과제 준비 › 제안서 작성 도우미", "제안서 작성 도우미",
          "전문기관별 체크리스트와 연구개발비 편성 한도를 확인하고, 연구개발계획서 목차 초안을 작성함. "
          "정산 마찰의 상당수는 <b>제안 단계의 편성·현물 반영</b>에서 시작됨.")

ag = loader.agencies()
rs = state.get_search()
c1, c2, c3 = st.columns([1.2, 1, 1])
akey = c1.selectbox("전문기관", list(ag["agencies"]), format_func=lambda k: f"{k} · {ag['agencies'][k]['name']}")
A = ag["agencies"][akey]
inst = c2.selectbox("주관 연구소", loader.INSTITUTES, index=2)
role = c3.selectbox("K-water 역할", ["주관연구개발기관", "공동연구개발기관", "위탁연구개발기관"])

t1, t2, t3 = st.tabs(["연구개발비 편성 검증", "제출 전 체크리스트", "계획서 목차 초안"])

with t1:
    st.caption("1개 연차 기준 · 단위 천원 · 표를 직접 고치면 바로 다시 검증함.")
    c1, c2, c3, c4 = st.columns(4)
    gov = c1.number_input("정부지원 연구개발비(천원)", value=250_000, step=10_000)
    gov_max = c2.number_input("정부지원 상한 (공기업)", value=float(A["gov_ratio_max_public"]), step=0.05, format="%.2f")
    cash_min = c3.number_input("기관부담 중 현금 하한", value=float(A["cash_ratio_min_public"]), step=0.01, format="%.2f")
    rate = c4.number_input("간접비 고시비율", value=0.20, step=0.01, format="%.2f",
                           help="기관별 과기정통부 간접비 고시비율을 입력")
    tbl = st.data_editor(budget.default_table(), hide_index=True, width="stretch", disabled=["비목"],
                         column_config={"현금(천원)": st.column_config.NumberColumn(format="localized"),
                                        "현물(천원)": st.column_config.NumberColumn(format="localized")})
    excl = st.multiselect("수정직접비에서 제외할 항목", ["현물", "위탁연구개발비", "국제공동연구개발비"],
                          default=["현물", "위탁연구개발비"], help="간접비 산정 기준. 적용 기준은 사용기준 제2조 정의 확인")
    s, C = budget.evaluate(tbl, int(gov), gov_max, cash_min, rate, tuple(excl))
    m = st.columns(5)
    for col, k in zip(m, ["총 연구개발비", "정부지원", "기관부담", "기관부담 현금", "기관부담 현물"]):
        col.metric(k, f"{s[k]:,.0f}")
    fails = [c for c in C if not c.ok]
    if fails:
        ui.note(f"한도·비율 위반 {len(fails)}건 — 제출 전 조정 필요.", "warn")
    st.dataframe(pd.DataFrame([{"결과": "✓ 적합" if c.ok else "✕ 위반", "항목": c.item, "편성": c.value, "기준": c.limit,
                                "근거": f"{c.ref} {rs.get(c.ref)['title'] if rs.get(c.ref) else ''}", "메모": c.note} for c in C]),
                 hide_index=True, width="stretch")

with t2:
    ui.section(f"{akey} 제출 전 확인")
    done = 0
    for i, item in enumerate(A["checklist"]):
        done += st.checkbox(item, key=f"ck_{akey}_{i}")
    st.progress(done / max(len(A["checklist"]), 1), text=f"{done}/{len(A['checklist'])} 확인")
    ui.section("연구원에서 실제로 겪은 실수 (사례 축적 중)")
    for p in A["pitfalls"]:
        st.markdown(f"- {p}")
    st.caption("연구소 인터뷰에서 나온 사례는 '연구소 애로사항 접수' 메뉴로 모아 이 목록에 반영함.")

with t3:
    c1, c2 = st.columns(2)
    title = c1.text_input("과제명", "AI 기반 정수장 미량오염물질 실시간 대응 기술 개발")
    kw = c2.text_input("핵심 키워드 (쉼표)", "PFAS, 고도정수, 디지털트윈, 운영 최적화")
    goal = st.text_area("최종 목표 (한두 문장)", "정수장 미량오염물질 유입을 조기 감지하고 공정 운전조건을 자동 제안하는 운영지원 기술을 개발하여 실증한다.", height=70)
    cfg = llm.get_config(st.secrets) if hasattr(st, "secrets") else None
    sections = ag["plan_outline"]
    lines = [f"# {title}", "", f"- 전문기관: {A['name']}", f"- 주관: 한국수자원공사 {inst} ({role})", f"- 핵심어: {kw}", ""]
    for sec in sections:
        lines += [f"## {sec['title']}", f"> 작성 요령: {sec['guide']}", ""]
        if sec["key"] == "goal":
            lines += [f"- 최종 목표: {goal}", "- 정량 목표: [성능지표] [목표값] [측정방법]", ""]
        elif sec["key"] == "budget":
            lines += ["- 현금·현물 구분 총괄표: (편성 검증 탭 결과 붙여넣기)",
                      "- 현물 장비: 장비명 / 자산번호 / 취득재원 / 산정 근거 를 장비 단위로 기재", ""]
        else:
            lines += ["- [ ]", ""]
    draft = "\n".join(lines)
    if cfg:
        if st.button("LLM으로 문단 초안 채우기", type="primary"):
            with st.spinner("초안 작성 중…"):
                try:
                    draft = llm.chat(cfg, llm.SYSTEM_PROPOSAL, f"과제 정보와 목차:\n{draft}\n각 항목을 3~5줄 개조식으로 채워줘.")
                except Exception as e:  # noqa: BLE001
                    st.error(f"LLM 호출 실패: {e}")
    else:
        st.caption("LLM 연결 전이라 템플릿 목차만 생성함. `.streamlit/secrets.toml`의 [llm] 설정 시 문단 초안까지 채움.")
    st.text_area("연구개발계획서 목차 초안 (Markdown)", draft, height=380)
    st.download_button("초안 내려받기 (.md)", draft.encode("utf-8"), "연구개발계획서_초안.md")
