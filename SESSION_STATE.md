# SESSION STATE

## 현재 작업
- fix130 AutoEver/eTax 비밀번호 추출 수정 완료

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
- AutoEver/eTax 메일 비밀번호 추출을 비밀번호 라벨 주변으로 제한
- 특수문자 포함 비밀번호 예: 20260520cr8wn7yw!plp 허용
- 세금계산서번호 같은 숫자-only 후보는 비밀번호로 사용하지 않게 차단
- WEB/Agent 버전 1.0.118 bump
- fix130 ZIP 생성: C:\Tmp\accounting_web_v1_autoever_password_fix130_20260520_091900.zip

## 다음 작업
- 관련 파일만 stage/commit/push
- 운영서버에 fix130 ZIP 배포

## 주의사항
- backup/hotfix/release 폴더 수정 금지
- 현재 워크트리에는 unrelated dirty 파일이 많으므로 관련 파일만 stage
- Graphify update는 1295 vs 1383 노드 감소로 거부되어 기존 graph를 유지함
- AutoEver 실제 운영 메일은 비밀번호에 ! 같은 특수문자가 포함됨
