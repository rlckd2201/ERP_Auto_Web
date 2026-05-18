# SESSION STATE

## 현재 작업
- fix129 Chrome/Windows 작업 완료 알림 추가

## 현재 수정중 파일
- web_v1/frontend/app.js
- web_v1/frontend/index.html
- web_v1/frontend/sw.js
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md

## 방금 수정한 내용
- 알림 허용 버튼을 일반 화면에 노출
- 작업 시작 시 Chrome 알림 권한을 1회 요청
- 작업 완료/실패 알림을 서비스워커 기반 Windows 알림으로 표시
- WEB/Agent 버전 1.0.117 bump

## 다음 작업
- node syntax 검증
- py_compile 검증
- Graphify update
- fix129 ZIP 생성/검증
- 관련 파일만 stage/commit/push

## 주의사항
- Chrome 알림은 HTTPS 접속에서만 정상 동작
- 로컬 Agent가 개발 frontend를 지우는 증상이 있어 개발 중에는 Agent를 임시 중지함
