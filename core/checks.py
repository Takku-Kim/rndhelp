"""정산 사전점검 룰 엔진.

각 점검은 (집행 건 또는 과제 전체) → Finding 목록을 돌려준다.
등급: 불인정(회수 위험) > 보완(증빙·소명 필요) > 확인(담당자 판단)
근거(ref)는 data/regulations.yaml 의 항목 id.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import pandas as pd

MEET_RULE_CHANGE = date(2026, 5, 6)  # 회의비 식비 기준 개정 시행일
SEVERITY_ORDER = {"불인정": 0, "보완": 1, "확인": 2}


@dataclass
class Finding:
    row: int | None
    severity: str
    title: str
    detail: str
    ref: str
    amount: int = 0


@dataclass
class ProjectInfo:
    start: date
    end: date
    direct_total: int          # 직접비 총액(현물 포함, 계획 기준)
    personnel_total: int       # 수정인건비(현물 포함)
    agency: str = "KEITI"


FOOD = re.compile(r"식대|식사|도시락|다과|케이터링|오찬|만찬")
ALCOHOL = re.compile(r"주류|맥주|소주|와인|호프|노래|유흥|골프")
LIFETIME = re.compile(r"종신|평생회원|학위과정|등록금")
INTERNAL_EQUIP = re.compile(r"보유 장비 사용료|자체 장비 사용료|내부 대체|장비사용료")
PLAN_UNKNOWN = re.compile(r"미반영|사전승인 미확인")


def _d(s) -> date | None:
    try:
        return pd.to_datetime(s).date()
    except Exception:
        return None


def _has(evidence: str, *keys: str) -> bool:
    ev = str(evidence or "")
    return any(k in ev for k in keys)


def check_row(i: int, r: pd.Series, p: ProjectInfo) -> list[Finding]:
    f: list[Finding] = []
    desc = f"{r.get('description', '')} {r.get('vendor', '')} {r.get('note', '')}"
    amt = int(r.get("amount", 0) or 0)
    semok = str(r.get("RCMS 세목", ""))
    d = _d(r.get("date"))
    ev = str(r.get("evidence", "") or "")

    # 1. 협약기간
    if d and (d < p.start or d > p.end):
        f.append(Finding(i, "불인정", "협약기간 외 집행",
                         f"집행일 {d} 이 협약기간({p.start}~{p.end}) 밖임. 협약기간 내 지출원인행위가 없으면 회수 대상.", "K17", amt))

    # 2. 유흥·접대
    if ALCOHOL.search(desc) or str(r.get("RCMS 비목")) == "불인정" and "유흥" in semok:
        f.append(Finding(i, "불인정", "회의비", "주류 등 유흥성 비용은 계상 불가.", "K07", amt))

    # 3. 회의 식비
    if FOOD.search(desc) and (semok == "회의비" or str(r.get("account")) in ("5220", "5230")):
        ext = str(r.get("external_attendee", "") or "").upper()
        if d and d >= MEET_RULE_CHANGE:
            if ext == "N":
                f.append(Finding(i, "불인정", "참여연구자만 참석한 회의 식비",
                                 "2026.5.6. 이후 참여연구자만 참여한 회의의 식비는 계상 불가. 과제 미참여자가 실제 참석했다면 회의록에 명단 보완.", "K03", amt))
            elif ext != "Y":
                f.append(Finding(i, "보완", "회의 참석자 구분 미기재",
                                 "과제 미참여자 참석 여부 확인 불가. 회의록에 참석자 명단·소속 기재.", "K03"))
        elif d:
            if not _has(ev, "결재", "품의"):
                f.append(Finding(i, "보완", "개정 전 회의 식비 — 사전결재 증빙",
                                 "2026.5.6. 이전 집행분은 종전 기준(외부인 참석 + 사전 내부결재) 적용. 사전결재 문서 첨부 필요.", "K03"))
            if ext == "N":
                f.append(Finding(i, "불인정", "외부인 미참석 회의 식비(개정 전)",
                                 "종전 기준상 소속기관 외부인이 참여한 회의만 식비 계상 가능.", "K03", amt))
        if not _has(ev, "회의록") and amt > 100_000:
            f.append(Finding(i, "보완", "회의록 누락",
                             "10만원 초과 회의비는 내부결재문서 또는 회의록 + 영수증 필요.", "K04"))

    # 4. 현금 결제
    if str(r.get("pay_method", "")) == "현금":
        f.append(Finding(i, "보완", "현금 지출 소명",
                         "현금 지출은 카드·계좌이체가 불가능한 경우만 허용. 사유서와 적격증빙 첨부.", "K17"))

    # 5. 장비
    if semok.startswith("연구시설·장비 구축") and str(r.get("account")) in ("1510", "1520"):
        if amt >= 30_000_000 and PLAN_UNKNOWN.search(desc):
            f.append(Finding(i, "불인정", "3천만원 이상 장비 — 계획 미반영·승인 미확인",
                             "계획서 미반영 3천만원 이상 장비는 전문기관 사전승인 필요. 승인 공문 확인.", "K18", amt))
        elif amt >= 30_000_000:
            f.append(Finding(i, "확인", "3천만원 이상 장비",
                             "계획서 반영 금액 대비 변경(±20% 초과) 여부 확인.", "K18"))
        if d and (p.end - d).days < 61:
            f.append(Finding(i, "보완", "종료 임박 장비 구입",
                             f"종료일 {p.end} 기준 2개월 이내 구입. 납품·설치 완료일 확인(산업부 사업은 2개월 전 완료 기준, 전문기관별 확인).", "K20"))
        if not _has(ev, "검수"):
            f.append(Finding(i, "보완", "장비 검수조서 누락", "검수조서·자산등록 증빙 첨부.", "K17"))

    # 6. 내부 장비 사용료
    if INTERNAL_EQUIP.search(desc):
        f.append(Finding(i, "불인정", "내부 보유 장비 사용료 현금 집행",
                         "기관 내부 보유 장비 사용료 지급은 원칙적 불인정(전문기관 인정 시 예외). 현물로 계상했는지, 계획서에 반영됐는지 확인.", "K12", amt))

    # 7. 현물 장비와 동일 장비 현금 유지비
    if "현물 계상 장비" in str(r.get("note", "")):
        f.append(Finding(i, "확인", "현물 장비와 현금 유지비 중복 여부",
                         "같은 장비를 현물(사용료/감가상각)로 계상하면서 유지·교정비를 현금으로 잡으면 중복 계상 지적 가능. 현물 산정에 유지비 포함 여부 확인.", "K07"))

    # 8. 종신회비·학위
    if LIFETIME.search(desc):
        f.append(Finding(i, "불인정", "종신 학회비·학위과정 비용", "연구인력 지원비 불인정 항목.", "K08", amt))

    # 9. 외부 용역 결과물
    if semok == "외부 전문기술 활용비" and not _has(ev, "결과", "성적서", "보고서"):
        f.append(Finding(i, "보완", "외부 전문기술 결과물 누락", "시험성적서·결과보고서 등 결과물 첨부.", "K05"))

    # 10. 증빙 자체 누락
    if not ev.strip():
        f.append(Finding(i, "보완", "증빙 없음", "지출 근거 증명자료가 없으면 인정되지 않음.", "K17"))

    # 11. 간이영수증
    if "간이영수증" in ev and amt > 30_000:
        f.append(Finding(i, "보완", "적격증빙 아님", "간이영수증은 적격증빙이 아님. 세금계산서·카드전표 또는 소명.", "K17"))
    return f


def check_aggregate(df: pd.DataFrame, p: ProjectInfo) -> list[Finding]:
    f: list[Finding] = []
    amt = df["amount"].fillna(0).astype(int)
    ext = int(amt[df["RCMS 세목"] == "외부 전문기술 활용비"].sum())
    if p.direct_total and ext > 0.4 * p.direct_total:
        f.append(Finding(None, "불인정", "외부 전문기술 활용비 한도 초과",
                         f"집행 {ext:,}원 > 직접비 {p.direct_total:,}원의 40%({int(0.4*p.direct_total):,}원).", "K05", ext - int(0.4 * p.direct_total)))
    elif p.direct_total and ext > 0.32 * p.direct_total:
        f.append(Finding(None, "확인", "외부 전문기술 활용비 한도 근접",
                         f"직접비 대비 {ext / p.direct_total:.0%} (한도 40%).", "K05"))
    allow = int(amt[df["RCMS 비목"] == "연구수당"].sum())
    if p.personnel_total and allow > 0.2 * p.personnel_total:
        f.append(Finding(None, "불인정", "연구수당 한도 초과",
                         f"연구수당 {allow:,}원 > 수정인건비의 20%({int(0.2*p.personnel_total):,}원).", "K06", allow - int(0.2 * p.personnel_total)))
    consign = int(amt[df["RCMS 비목"] == "위탁연구개발비"].sum())
    if p.direct_total and consign > 0.4 * p.direct_total:
        f.append(Finding(None, "불인정", "위탁연구개발비 한도 초과",
                         f"위탁 {consign:,}원 > 직접비의 40%.", "K21", consign - int(0.4 * p.direct_total)))
    return f


def run_checks(df: pd.DataFrame, p: ProjectInfo) -> pd.DataFrame:
    findings: list[Finding] = []
    for i, r in df.reset_index(drop=True).iterrows():
        findings.extend(check_row(i, r, p))
    findings.extend(check_aggregate(df, p))
    out = pd.DataFrame([f.__dict__ for f in findings])
    if out.empty:
        return pd.DataFrame(columns=["row", "severity", "title", "detail", "ref", "amount"])
    out["_o"] = out["severity"].map(SEVERITY_ORDER)
    return out.sort_values(["_o", "row"], na_position="first").drop(columns="_o").reset_index(drop=True)
