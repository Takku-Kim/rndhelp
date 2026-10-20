"""현물(기관 보유 장비) 계상 적정성 사전점검.

산정 방식 두 가지를 나란히 보여주고, 보수적인 값을 권고한다.
  A. 감가상각 기준 = 취득가 / 내용연수 × (과제 사용개월 / 12) × 과제 사용비율  (잔존 장부가 한도)
  B. 기관 사용료 규정 기준 = 시간당 사용료 × 과제 사용시간
※ 산식은 '기관 자체 규정' 예시이며, 실제 인정 산식은 전문기관·정산기관과 사전 협의 필요.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd


@dataclass
class InkindResult:
    name: str
    dep_based: int
    rate_based: int
    recommended: int
    claimed: int
    grade: str                      # 적정 / 보완 필요 / 불인정 위험
    issues: list[tuple[str, str, str]] = field(default_factory=list)  # (severity, message, ref)
    remaining_life_years: float = 0.0
    evidence: list[str] = field(default_factory=list)


BASE_EVIDENCE = [
    "현물부담 확인서 (기관장 명의)",
    "자산대장 사본 (자산번호·취득일·취득가·취득재원)",
    "연구개발계획서 '연구시설·장비 보유현황' 해당 쪽",
    "장비 사용일지 (일자·사용시간·사용자·과제명·결과물)",
    "현물 산정 근거 (감가상각 계산표 또는 기관 장비사용료 규정)",
]


def evaluate(row: pd.Series, project_start: date) -> InkindResult:
    acq = pd.to_datetime(row["acq_date"]).date()
    cost = int(row["acq_cost"])
    life = float(row["useful_life"]) or 1.0
    months = float(row["project_months"])
    ratio = float(row["usage_ratio"])
    hours = float(row.get("usage_hours", 0) or 0)
    rate = float(row.get("rate_per_hour", 0) or 0)
    claimed = int(row.get("claimed", 0) or 0)

    elapsed = max((project_start - acq).days / 365.25, 0)
    remaining = max(life - elapsed, 0.0)
    book_value = cost * remaining / life
    dep = cost / life * (months / 12) * ratio
    dep_based = int(min(dep, book_value))
    rate_based = int(rate * hours) if rate and hours else 0
    candidates = [v for v in (dep_based, rate_based) if v > 0]
    recommended = min(candidates) if candidates else 0

    issues: list[tuple[str, str, str]] = []
    funding = str(row["funding"])
    if "국가R&D" in funding or "정부" in funding:
        issues.append(("불인정", "타 국가R&D(정부재원)로 구축한 장비는 원칙적으로 현물 계상 불가. 사용기준 제66조 예외 요건 충족 여부를 정산기관과 사전 확인.", "K10"))
    if str(row["in_plan"]).upper() != "Y":
        issues.append(("불인정", "계획서 '연구시설·장비 보유현황'에 없는 내부 장비. 계획 변경(협약 변경) 없이 현물로 인정받기 어려움.", "K11"))
    if str(row["cash_dup"]).upper() == "Y":
        issues.append(("불인정", "같은 장비의 비용을 현금으로도 집행(유지·교정·임차 등). 현금·현물 중복 계상 지적 위험.", "K07"))
    if str(row["usage_log"]).upper() != "Y":
        issues.append(("보완", "장비 사용일지가 없음. 과제 사용시간·결과물을 입증할 기록이 정산 시 가장 많이 요구됨.", "K11"))
    if str(row.get("zeus", "")).upper() == "N":
        issues.append(("보완", "공동활용 대상 장비인데 ZEUS 미등록. 등록 후 계상 권고.", "K11"))
    if remaining <= 0:
        issues.append(("확인", f"내용연수({life:.0f}년) 경과 장비 — 감가상각 기준 산정액 0원. 기관 사용료 규정 방식으로만 산정 가능하며, 정산 담당자와 이견이 잦은 유형(경험칙).", "K09"))
    if recommended == 0 and claimed > 0:
        issues.append(("불인정", "산정 근거로 뒷받침되는 금액이 없음 (감가상각 0원, 사용료 규정·사용시간 미입력).", "K09"))
    elif claimed > 0 and recommended > 0 and claimed > max(candidates) * 1.05:
        issues.append(("보완", f"계상액 {claimed:,}원이 산정 근거 최대값 {max(candidates):,}원을 초과. 과다 계상분 조정 필요.", "K09"))
    elif claimed > recommended > 0 and len(candidates) > 1:
        issues.append(("확인", f"계상액이 보수적 산정액({recommended:,}원)보다 큼. 높은 쪽 산식(기관 사용료 규정 등)의 근거 문서를 반드시 첨부.", "K11"))
    if ratio > 0.8:
        issues.append(("확인", f"과제 사용비율 {ratio:.0%} — 다른 업무·과제 사용과 합쳐 100%를 넘지 않는지 사용일지로 입증.", "K11"))

    sev = {s for s, _, _ in issues}
    grade = "불인정 위험" if "불인정" in sev else ("보완 필요" if "보완" in sev else "적정")
    evidence = list(BASE_EVIDENCE)
    if str(row.get("zeus", "")).upper() in ("Y", "N"):
        evidence.append("ZEUS 공동활용 등록 화면")
    return InkindResult(str(row["name"]), dep_based, rate_based, recommended, claimed, grade, issues, round(remaining, 1), evidence)


def explanation_draft(res: InkindResult, row: pd.Series, project_name: str, org: str = "한국수자원공사") -> str:
    """정산 담당자·회계사 대응용 현물 산정 소명서 초안(텍스트)."""
    lines = [
        f"현물(연구시설·장비) 계상 소명서 (초안)",
        "",
        f"1. 과제명: {project_name}",
        f"2. 기관: {org}",
        f"3. 장비: {row['name']} (자산번호 {row['asset_no']}, 취득일 {row['acq_date']}, 취득가 {int(row['acq_cost']):,}원, 취득재원 {row['funding']})",
        f"4. 계획서 반영: {'연구개발계획서 연구시설·장비 보유현황에 반영' if str(row['in_plan']).upper()=='Y' else '미반영(협약변경 필요)'}",
        f"5. 과제 사용: 협약기간 중 {row['project_months']}개월, 과제 사용비율 {float(row['usage_ratio']):.0%}"
        + (f", 사용시간 {int(row['usage_hours'])}시간" if float(row.get('usage_hours', 0) or 0) else ""),
        "6. 산정 근거",
        f"   가. 감가상각 기준: {int(row['acq_cost']):,}원 ÷ {row['useful_life']}년 × {row['project_months']}/12 × {float(row['usage_ratio']):.0%} = {res.dep_based:,}원 (잔존 내용연수 {res.remaining_life_years}년)",
    ]
    if res.rate_based:
        lines.append(f"   나. 기관 장비사용료 규정 기준: 시간당 {int(row['rate_per_hour']):,}원 × {int(row['usage_hours'])}시간 = {res.rate_based:,}원")
    lines += [
        f"   다. 계상액: {res.claimed:,}원 (보수적 산정액 {res.recommended:,}원 이내로 조정 권고)",
        "7. 중복 계상 여부: 동일 장비의 유지보수·교정·임차 비용을 현금으로 계상하지 않았음을 확인함" if str(row['cash_dup']).upper() != 'Y'
        else "7. 중복 계상 여부: 동일 장비 현금 집행 내역 있음 — 현물 산정에서 해당 비용을 제외하여 재산정함",
        "8. 첨부: " + ", ".join(res.evidence),
        "",
        "※ 본 초안은 내부 검토용이며, 산식과 표현은 전문기관·정산기관 기준에 맞게 수정하여 사용.",
    ]
    return "\n".join(lines)
