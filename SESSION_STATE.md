# SESSION STATE

## 현재 작업
- fix131 AutoEver/eTax 비밀번호 패턴 보정 완료

## 현재 수정중 파일
- tax_crawler/portal_autoever.py
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md

## 방금 수정한 내용
- AutoEver 비밀번호 기준을 실제 원문 기준으로 변경: 8자리 날짜 + 12자리 토큰
- 3개 EML 원문 비밀번호 검증: 20260320zs!tblan1af@, 2026042098s6hv0m399p, 20260520cr8wn7yw!plp
- 짧은 토큰/세금계산서번호는 비밀번호로 사용하지 않게 차단
- WEB/Agent 버전 1.0.119 bump
- py_compile 통과
- Graphify update는 1295 vs 1383 노드 감소로 거부되어 기존 graph 유지

## 다음 작업
- fix131 ZIP 생성/검증 완료: C:\Tmp\accounting_web_v1_autoever_password_pattern_fix131_20260520_094000.zip
- 관련 파일만 stage/commit/push

## 주의사항
- backup/hotfix/release 폴더 수정 금지
- 현재 워크트리에는 unrelated dirty/delete 파일이 많으므로 관련 파일만 stage
