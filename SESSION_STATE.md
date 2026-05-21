# SESSION STATE

## 현재 작업
- fix140 AutoEver 거래처 사업자번호 키보드 선택 보강 완료, 커밋/푸시 대기

## 현재 수정중 파일
- manager_server/전표 자동화 프로그램(담당자용)_v6.2.py
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
- AutoEver/KT special vendor path를 target business-number digits 기준으로 통일
- AutoEver relation-item value를 먼저 Delete로 비운 뒤 vendor popup을 열고 `104-81-53190` 붙여넣기
- AutoEver 사업자번호 감지를 vendor/supplier business-number 변형 필드와 payload text까지 확대
- WEB/Agent 버전 1.0.128로 bump
- fix140 ZIP 생성/검증 완료: C:\Tmp\accounting_web_v1_autoever_vendor_keyboard_fix140_20260521_095036.zip
- Graphify 정상 갱신: 234 files / 1393 nodes / 4394 edges / 84 communities

## 다음 작업
- 관련 파일만 stage/commit/push
- 운영 배포 명령 전달

## 주의사항
- 기존 unrelated dirty 파일은 stage하지 않음
- Gemini API 키는 소스/ZIP에 넣지 않음
- 백업/중첩 support 파일이 들어간 `C:\Tmp\accounting_web_v1_autoever_vendor_keyboard_fix140_20260521_094909.zip`은 사용하지 말고 `095036.zip`만 사용
