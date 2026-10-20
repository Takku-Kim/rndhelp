import io
from datetime import date

import pandas as pd
import streamlit as st

from core import checks, loader, mapper, state, ui

ui.header("수행·정산 › 정산 사전점검", "정산 사전점검",
          "사용실적보고 전에 집행내역 전체를 RCMS 비목으로 변환하고, 정산에서 자주 지적되는 항목을 미리 걸러냅니다.")

hm = state.get_mapper(state.model_version())
rs = state.get_search()

with st.expander("과제 정보", expanded=True):
    c1, c2, c3 = st.columns(3)
    pname = c1.text_input("과제명", "AI 기반 정수장 미량오염물질 대응 기술 개발")
    agency = c2.selectbox("전문기관", ["KEITI (환경산업기술원)", "KAIA (국토교통과학기술진흥원)", "NRF (연구재단)", "기타"])
    inst = c3.selectbox("수행 연구소", loader.INSTITUTES, index=1)
    c4, c5, c6, c7 = st.columns(4)
    start = c4.date_input("협약 시작일", date(2025, 4, 1))
    end = c5.date_input("협약 종료일", date(2026, 12, 31))
    direct_total = c6.number_input("직접비 총액(현물 포함, 백만원)", value=900, step=10) * 1_000_000
    personnel = c7.number_input("수정인건비(현물 포함, 백만원)", value=260, step=10) * 1_000_000

up = st.file_uploader("집행내역 (CSV/XLSX) — 열: date, account, description, vendor, amount, pay_method, evidence, external_attendee, note",
                      type=["csv", "xlsx"])
if up is not None:
    df = pd.read_excel(up, dtype={"account": str}) if up.name.endswith("xlsx") else pd.read_csv(up, dtype={"account": str}, encoding="utf-8-sig")
else:
    df = loader.load_csv("sample_ledger.csv")
    st.caption("파일을 올리지 않으면 例示 집행내역 22건으로 점검합니다.")

mapped = mapper.results_to_frame(df, hm.map_many(df)).reset_index(drop=True)
p = checks.ProjectInfo(start, end, int(direct_total), int(personnel))
f = checks.run_checks(mapped, p)

deadline = (pd.Timestamp(end) + pd.DateOffset(months=3)).date()
dday = (deadline - date.today()).days
sev = f["severity"].value_counts() if len(f) else pd.Series(dtype=int)
risk_amt = int(f.loc[f["severity"] == "불인정", "amount"].sum()) if len(f) else 0
c1, c2, c3, c4 = st.columns(4)
with c1:
    ui.card("불인정(회수 위험)", f"{sev.get('불인정', 0)}건", f"관련 금액 {risk_amt:,}원")
with c2:
    ui.card("보완 필요", f"{sev.get('보완', 0)}건", "증빙·소명 보완")
with c3:
    ui.card("담당자 확인", f"{sev.get('확인', 0)}건", "규정 해석·계획 대비 확인")
with c4:
    ui.card("사용실적보고 기한", f"{deadline:%Y.%m.%d}", f"종료 후 3개월 · D{-dday:+d}" if dday < 0 else f"종료 후 3개월 · D-{dday}")

ui.section("점검 결과")
if f.empty:
    st.success("지적 사항이 없습니다.")
else:
    tbl = f.copy()
    tbl["건"] = tbl["row"].apply(lambda r: "과제 전체" if pd.isna(r) else f"#{int(r) + 1}")
    tbl["집행 내용"] = tbl["row"].apply(lambda r: "" if pd.isna(r) else f"{mapped.loc[int(r), 'date']} · {mapped.loc[int(r), 'description']} ({int(mapped.loc[int(r), 'amount']):,}원)")
    tbl["근거"] = tbl["ref"].apply(lambda x: f"{x} {rs.get(x)['title']}" if rs.get(x) else x)
    pick = st.radio("등급", ["전체", "불인정", "보완", "확인"], horizontal=True, label_visibility="collapsed")
    if pick != "전체":
        tbl = tbl[tbl["severity"] == pick]
    st.dataframe(ui.style_status(tbl[["건", "severity", "title", "집행 내용", "detail", "근거"]], "severity"), hide_index=True, width="stretch", height=440,
                 column_config={"severity": "등급", "title": "점검 항목", "detail": st.column_config.TextColumn("설명", width="large")})

    with st.expander("근거 규정 원문 요약 보기"):
        for rid in sorted(set(f["ref"])):
            it = rs.get(rid)
            if it:
                st.markdown(f"**{rid} · {it['title']}** ({it['article']}) — {' '.join(it['text'].split())}  \n"
                            f"<span style='color:#8B95A1;font-size:.8rem'>출처: {it['source_name']}</span>", unsafe_allow_html=True)

ui.section("비목별 집행 요약 (RCMS 기준)")
summ = mapped.groupby(["RCMS 비목", "RCMS 세목"], as_index=False)["amount"].agg(["count", "sum"]).rename(columns={"count": "건수", "sum": "금액"})
st.dataframe(summ, hide_index=True, width="stretch", column_config={"금액": st.column_config.NumberColumn(format="localized")})

buf = io.BytesIO()
with pd.ExcelWriter(buf) as xw:
    mapped.to_excel(xw, sheet_name="집행내역_RCMS변환", index=False)
    f.assign(row=f["row"].apply(lambda r: None if pd.isna(r) else int(r) + 1)).to_excel(xw, sheet_name="점검결과", index=False)
    summ.to_excel(xw, sheet_name="비목별요약", index=False)
st.download_button("점검 결과 내려받기 (xlsx)", buf.getvalue(), f"정산사전점검_{date.today():%Y%m%d}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
ui.note(f"<b>{inst}</b> · {agency} · 이 점검은 공개 기준을 요약한 룰로 수행합니다. 전문기관별 세부 지침(예: KEITI 사례집)과 다를 수 있어 "
        "‘확인’ 항목은 연구지원 담당과 협의해 주세요.")
