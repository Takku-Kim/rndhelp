from datetime import date

import pandas as pd
import streamlit as st

from core import inkind, loader, state, ui

ui.header("수행·정산 › 현물 적정성", "현물(기관 보유 장비) 적정성 점검",
          "정산 담당자·회계사가 현물 장비를 불인정하는 사유를 계획 단계부터 미리 점검하고, 산정 근거와 소명서 초안을 작성함.")

rs = state.get_search()
ui.note("현물 불인정은 대부분 다섯 가지에서 발생 — ① 계획서 <b>보유현황 미반영</b> ② <b>타 국가R&D 재원</b>으로 산 장비 "
        "③ 과제 사용을 입증할 <b>사용일지 부재</b> ④ 같은 장비의 유지·교정비를 현금으로도 잡은 <b>중복 계상</b> "
        "⑤ 연구기간 중 <b>감가상각</b>으로 인한 장비 가치 하락(잔존가치 감소·내용연수 경과). "
        "산정 방식은 기관 규정마다 달라 아래 두 산식을 나란히 보여주고 낮은 값을 권고함.", "warn")

c1, c2 = st.columns([2, 1])
pname = c1.text_input("과제명", "AI 기반 정수장 미량오염물질 대응 기술 개발")
pstart = c2.date_input("과제(연차) 시작일", date(2026, 1, 1))

ui.section("현물 장비 목록 (직접 수정 가능)")
src = loader.load_csv("sample_inkind.csv")
edited = st.data_editor(
    src, num_rows="dynamic", hide_index=True, width="stretch", key="ik_editor",
    column_config={
        "name": "장비명", "asset_no": "자산번호", "acq_date": "취득일",
        "acq_cost": st.column_config.NumberColumn("취득가(원)", format="localized"),
        "useful_life": st.column_config.NumberColumn("내용연수(년)"),
        "funding": st.column_config.SelectboxColumn("취득재원", options=["자체재원", "타 국가R&D", "기타 정부보조"]),
        "in_plan": st.column_config.SelectboxColumn("계획서 반영", options=["Y", "N"]),
        "project_months": st.column_config.NumberColumn("과제 사용(개월)"),
        "usage_ratio": st.column_config.NumberColumn("과제 사용비율", min_value=0.0, max_value=1.0, step=0.05),
        "usage_hours": st.column_config.NumberColumn("사용시간(h)"),
        "rate_per_hour": st.column_config.NumberColumn("시간당 사용료(원)", format="localized"),
        "usage_log": st.column_config.SelectboxColumn("사용일지", options=["Y", "N"]),
        "zeus": st.column_config.SelectboxColumn("ZEUS 등록", options=["Y", "N", "해당없음"]),
        "cash_dup": st.column_config.SelectboxColumn("현금 중복집행", options=["Y", "N"]),
        "claimed": st.column_config.NumberColumn("현물 계상액(원)", format="localized"),
    },
)

rows = edited.dropna(subset=["name", "acq_date", "acq_cost"]).reset_index(drop=True)
results = [inkind.evaluate(r, pstart) for _, r in rows.iterrows()]
summary = pd.DataFrame([{
    "장비": x.name, "등급": x.grade, "감가상각 기준": x.dep_based, "사용료 규정 기준": x.rate_based,
    "권고 계상액": x.recommended, "현재 계상액": x.claimed, "차이": x.claimed - x.recommended,
    "잔존 내용연수": x.remaining_life_years, "지적 수": len(x.issues),
} for x in results])

g = summary["등급"].value_counts() if len(summary) else pd.Series(dtype=int)
k1, k2, k3, k4 = st.columns(4)
with k1:
    ui.card("현물 장비", f"{len(summary)}대", f"계상액 합계 {int(summary['현재 계상액'].sum()):,}원" if len(summary) else "")
with k2:
    ui.card("불인정 위험", f"{g.get('불인정 위험', 0)}대",
            f"{int(summary.loc[summary['등급'] == '불인정 위험', '현재 계상액'].sum()):,}원" if len(summary) else "")
with k3:
    ui.card("보완 필요", f"{g.get('보완 필요', 0)}대", "증빙·산정 보완")
with k4:
    ui.card("적정", f"{g.get('적정', 0)}대", "")

ui.section("장비별 판정")
st.dataframe(ui.style_status(summary, "등급"), hide_index=True, width="stretch",
             column_config={c: st.column_config.NumberColumn(format="localized") for c in ["감가상각 기준", "사용료 규정 기준", "권고 계상액", "현재 계상액", "차이"]})

if results:
    ui.section("상세 점검 · 소명서 초안")
    names = [x.name for x in results]
    pick = st.selectbox("장비 선택", names, index=0)
    i = names.index(pick)
    res, row = results[i], rows.iloc[i]
    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.markdown(f"{ui.badge(res.grade)} &nbsp; **{res.name}** · {row['asset_no']}", unsafe_allow_html=True)
        if not res.issues:
            st.success("지적 사항 없음 — 아래 증빙만 갖추면 됨.")
        for sev, msg, ref in res.issues:
            it = rs.get(ref)
            st.markdown(f"{ui.badge(sev)} {msg} <span style='color:#8B95A1;font-size:.8rem'>[{ref} {it['title'] if it else ''}]</span>",
                        unsafe_allow_html=True)
        st.markdown("**정산 시 준비할 증빙**")
        for e in res.evidence:
            st.checkbox(e, key=f"ik_{i}_{e}")
    with c2:
        draft = inkind.explanation_draft(res, row, pname)
        st.text_area("현물 산정 소명서 (초안)", draft, height=380)
        st.download_button("소명서 초안 내려받기 (.txt)", draft.encode("utf-8"), f"현물소명서_{row['asset_no']}.txt")

ui.note("<b>산식 A (감가상각)</b> = 취득가 ÷ 내용연수 × 사용개월/12 × 과제 사용비율 (잔존 장부가 한도)<br>"
        "<b>산식 B (사용료)</b> = 기관 장비사용료 규정 단가 × 과제 사용시간<br>"
        "<span style='color:#6B7684'>(기관 자체 규정 例示 / 전문기관·정산기관과 사전 협의 필요 — 계획 단계에서 산식을 합의해 두는 것이 가장 확실한 예방책)</span>")
