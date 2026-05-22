# SESSION STATE

## 현재 작업
- fix147 KT/AutoEver 거래처 사업자번호 팝업 타이밍 추가 지연 작업중

## 현재 수정중 파일
- manager_server/전표 자동화 프로그램(담당자용)_v6.2.py
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md

## 방금 수정한 내용
- 거래처 관계항목 Delete 후 settle 대기를 최소 0.18초로 확대
- 팝업 선감지 timeout 0.25초에서 0.70초로 확대
- 팝업 열기 후 wait/search timeout 확대
- 팝업 감지 후 붙여넣기 전 0.35초, 붙여넣기 후 0.35초 대기
- Tab/방향키 간격 0.08초, Enter 간격 0.12초로 확대
- WEB/Agent 버전 1.0.135로 bump

## 다음 작업
- py_compile 검증 완료
- graphify update 완료
- fix147 ZIP 생성/검증 완료: C:\Tmp\accounting_web_v1_vendor_popup_slow_timing_fix147_20260522_092748.zip
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 전달

## 주의사항
- 회계일/전표관리단위 상단 필드 타이밍은 건드리지 않음
- fix144 방식 재도입 금지
- manager_server active source만 수정
- backup/hotfix/release 폴더 수정 금지
- 기존 unrelated dirty 파일은 stage하지 않음
