# SESSION STATE

## 현재 작업
- fix138 Agent 자동실행/다시점검 프론트 수정 완료 단계

## 현재 수정중 파일
- web_v1/frontend/app.js
- web_v1/frontend/index.html
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md
- graphify-out/GRAPH_REPORT.md
- graphify-out/graph.json
- graphify-out/graph.html

## 방금 수정한 내용
- 로그인 전 autoStartAgentAfterLogin 선호출 제거
- setup 상태 로드 후 미연결/업데이트필요일 때 accountingweb://start 호출
- 다시 점검 버튼이 상태조회 후 필요 시 Agent 실행을 force 재시도하도록 변경
- frontend cache busting bump
- WEB/Agent 버전 1.0.126로 bump
- node --check 및 Agent py_compile 통과
- Graphify 정상 갱신: 233 files / 1388 nodes / 4385 edges / 38 communities

## 다음 작업
- fix138 ZIP 생성/검증
- 관련 파일만 stage/commit/push
- 운영 배포/서버 시작 명령 전달

## 주의사항
- 기존 unrelated dirty 파일은 stage하지 않음
- Gemini API 키는 소스/ZIP에 넣지 않음
