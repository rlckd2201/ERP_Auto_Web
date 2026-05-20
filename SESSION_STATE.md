# SESSION STATE

## 현재 작업
- fix139 Agent 자동실행/다시점검 Chrome 프로토콜 호출 보강 완료

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
- 로그인 submit 시작 시 accountingweb://start 직접 호출 추가
- 다시 점검 클릭 시작 시 accountingweb://start 직접 호출 후 1.2초 대기 및 상태 재조회
- autoStartAgentAfterLogin 중복 호출을 requestAgentStartNow helper로 정리
- frontend cache busting bump
- WEB/Agent 버전 1.0.127로 bump
- 개발폴더를 지우던 pythonw.exe Agent 프로세스 중지 후 frontend/tools 복구
- Graphify 정상 갱신: 234 files / 1393 nodes / 4394 edges / 84 communities
- ZIP 생성/검증 완료: C:\Tmp\accounting_web_v1_agent_protocol_gesture_fix139_20260521_085057.zip

## 다음 작업
- 관련 파일만 stage/commit/push
- 운영 배포 명령 전달

## 주의사항
- 기존 unrelated dirty 파일은 stage하지 않음
- Gemini API 키는 소스/ZIP에 넣지 않음
- 로컬 Agent가 개발폴더를 런타임처럼 덮어쓰지 않게 주의
