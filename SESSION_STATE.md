# SESSION STATE

## 현재 작업
- fix112 정기 처리 계정 규칙 전체 대조/보강 완료

## 현재 수정중 파일
- web_v1/backend/erp_runner.py
- web_v1/frontend/app.js
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md

## 방금 수정한 내용
- CS 담당자용 _guess_regular_account()와 WEB backend/frontend 정기 계정 규칙 재대조
- 지급수수료 키워드에 누락됐던 crobat 추가
- 통신비/지급수수료 전체 키워드 목록 기준 확인
- 버전 1.0.100 bump
- fix112 ZIP 생성 예정: C:\Tmp\accounting_web_v1_regular_account_rules_fix112_20260515_122034.zip

## 다음 작업
- 운영서버 172.17.39.121에 fix112 ZIP 배포
- 담당자 PC Agent 업데이트 후 정기 처리 실환경 E2E 확인

## 주의사항
- active source는 web_v1 기준
- backup / hotfix / release 계열 폴더 수정 금지
- graphify update .는 기존처럼 node 감소 보호로 실패할 수 있음
