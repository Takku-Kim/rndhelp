# RND-HELP · K-water 국가R&D 과제관리 도우미 (샘플)

수공 정산시스템과 국가 RCMS의 **비목 분류가 달라** 연구원이 정산 때마다 겪는 어려움을 줄이기 위한 Streamlit 시범 앱입니다.
룰 기반 판정과 과거 집행내역으로 학습한 AI 분류를 함께 씁니다. 인트라넷 탑재 전, aihub.kwaterai.com 처럼 웹에서 시범 운영하는 것을 전제로 했습니다.

**🔗 시범 서비스: https://rndaid.streamlit.app**

> ⚠ 계정코드·집행내역·현물 장비는 모두 **가상 샘플**입니다. 판정은 사전 점검용 참고 정보이며 정산 결과를 보장하지 않습니다.

## 메뉴

| 단계 | 메뉴 | 하는 일 |
|---|---|---|
| 과제 준비 | **제안서 작성 도우미** | 전문기관(KEITI·KAIA·NRF)별 체크리스트, 연구개발비 편성 한도 검증(정부지원·현금 비율, 연구수당 20%, 외부전문기술·위탁 40%, 연구혁신비 10%/5천만원, 간접비), 계획서 목차 초안 |
| 수행·정산 | **비목 매핑 (수공↔RCMS)** | 수공 계정+적요 → RCMS 비목/세목, 필요 증빙, 주의사항. 단건 조회·일괄 변환(xlsx)·담당자 교정→재학습 |
| | **정산 사전점검** | 집행내역 일괄 점검 — 협약기간 외, 유흥성, 회의 식비(2026.5.6. 개정 전/후 구분), 현금 지출, 3천만원 이상 장비, 내부 장비 사용료, 증빙 누락, 비목 한도 |
| | **현물 적정성 점검** | 기관 보유 장비 현물의 감가상각/사용료 산식 비교, 불인정 위험(계획서 미반영·타 국가R&D 재원·사용일지 부재·현금 중복), 증빙 목록, **소명서 초안** |
| 지원 | **규정·FAQ 검색** | 사용기준·KEITI 사례집 요약 KB 검색, Top1 유사도·Top1–Top2 마진으로 검색 신뢰도 표시 |
| | **연구소 애로사항 접수** | 7개 연구소 인터뷰 질문지와 접수 양식 → 룰·체크리스트 보완 근거 |

## 판정 방식 (룰 + AI 병행)

```
수공 계정코드 + 적요/거래처
   ├─ 룰 엔진 (data/mapping_rules.yaml)  : 계정 × 키워드 정규식, 우선순위
   └─ AI 분류기 (TF-IDF 문자 n-gram + 로지스틱 회귀, data/train_ledger.csv 학습)
        ↓
   일치 → 자동확정 · 불일치/확신 낮음 → 검토필요 · 유흥/종신회비 등 → 불인정
   담당자 교정 → data/feedback.csv (3배 가중) → 재학습
```

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
python -m pytest -q          # 핵심 로직 테스트
python scripts/make_sample_data.py   # 샘플 데이터 재생성
```

Streamlit Community Cloud: 리포 `newcave/rndhelp`, 브랜치 `main`, Main file `app.py`, App URL `rndaid` → https://rndaid.streamlit.app

### LLM 연결 (선택)
제안서 문단 초안을 LLM으로 채우려면 `.streamlit/secrets.toml`(깃 제외)에 OpenAI 호환 엔드포인트를 넣습니다.

```toml
[llm]
base_url = "https://<내부 LLM 서버>/v1"
api_key  = "..."
model    = "<모델명>"
```

## 실제 운영으로 넘어가려면

1. `data/kwater_accounts.csv` — 수공 정산시스템 실제 계정표로 교체
2. `data/train_ledger.csv` — 과거 집행내역 ↔ RCMS 최종 등록 비목 쌍으로 교체 (연구소별 수백 건이면 충분)
3. `data/mapping_rules.yaml` — 연구소 인터뷰 결과로 키워드·주의문 보강, `verified: false` 항목 RCMS 화면 기준 확정
4. `data/regulations.yaml` — 전문기관별 지침(KEITI 사례집 등) 조문 추가, 기준일 관리
5. 애로사항·교정 데이터 저장소를 파일 → DB로 전환 (Cloud는 재시작 시 파일 초기화)

## 근거 자료 (요약 반영, 원문 확인 필요)
- 과기정통부 「국가연구개발사업 연구개발비 사용 기준」 2026.5.6. 개정 (연구혁신비 신설, 회의비 식비 완화)
- KEITI 「환경기술개발사업 연구개발비 관리 및 Q&A 사례집」(2025.12)
- 환경부 「환경기술개발사업 운영규정」(2024.12.10.)
- 국가연구개발사업 회의비 집행 규제 완화 안내 (2026.5.6. 시행)

## 구조

```
app.py               내비게이션·공통 헤더
views/               화면 7개
core/  mapper.py     룰+ML 비목 매핑      checks.py   정산 점검 룰
       inkind.py     현물 산정·점검       budget.py   편성 검증
       search.py     규정 검색            llm.py      선택적 LLM
       ui.py         K-water 톤 스타일    state.py    캐시·저장
data/                룰·규정 KB·샘플 데이터 (YAML/CSV)
scripts/             샘플 데이터 생성기
tests/               회귀 테스트
```

K-water 연구원 AI연구소 · 시범 운영용 샘플
