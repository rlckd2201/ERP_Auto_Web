# SESSION STATE

## 현재 작업
- fix128 필수 프로그램 EXE 반복 다운로드 방지

## 현재 수정중 파일
- web_v1/frontend/app.js
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md

## 방금 수정한 내용
- 로그인 후 Agent 미연결 시 EXE 자동 다운로드 fallback 제거
- 설치 버튼은 먼저 accountingweb://start 프로토콜로 기존 설치 실행기를 호출
- 연결 실패 시 처음 설치 PC인지 확인 후에만 EXE 다운로드
- WEB/Agent 버전 1.0.116 bump

## 다음 작업
- frontend node syntax 검증
- py_compile 검증
- Graphify update
- fix128 ZIP 생성/검증
- 관련 파일만 stage/commit/push

## 주의사항
- 이미 설치된 PC는 같은 EXE를 다시 받을 필요 없음
- EXE 자체는 실행 시 최신 payload를 서버에서 다운로드하는 bootstrapper
