# SESSION STATE

## 현재 작업
- fix111 정기 처리 CS 기준 보정 완료

## 현재 수정중 파일
- web_v1/backend/erp_runner.py
- web_v1/backend/app.py
- web_v1/frontend/app.js
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- web_v1/VERSION
- manager_server/전표 자동화 프로그램(담당자용)_v6.2.py
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md

## 방금 수정한 내용
- 정기 처리 품목 계정은 CS legacy `_guess_regular_account()` 기준으로 다시 계산
- 기존/크롤러 계정값은 사용자가 WEB에서 수동 변경한 경우에만 유지
- 다우오피스/그룹웨어/다우기술 정기 건 기본 계정 `지급수수료` 보정
- 정기 ERP payload에 공급자 사업자번호 전달
- Agent ERP 거래처 팝업에서 일반 정기 거래처도 사업자번호로 자동 선택
- fix110 트레이 우클릭 로직 유지, 버전 1.0.99로 정합화
- fix111 ZIP 생성: C:\Tmp\accounting_web_v1_regular_legacy_rules_fix111_20260515_121226.zip

## 다음 작업
- 운영서버 172.17.39.121에 fix111 ZIP 배포
- 담당자 PC Agent 업데이트 후 Daou Technology 정기 ERP 실환경 E2E 확인
- ERP 거래처 팝업이 220-81-02810 행을 자동 선택하는지 확인

## 주의사항
- active source는 web_v1 기준
- backup / hotfix / release 계열 폴더 수정 금지
- manager_server는 Agent ERP GUI 자동화 기준 파일로, 이번에는 거래처 팝업 보정을 위해 필요한 최소 범위만 수정
- graphify update .는 1247 vs 1274 node 감소 보호로 미반영


