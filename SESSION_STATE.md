# SESSION STATE

## 현재 작업
- fix145 fix144 즉시 롤백/복구 작업중

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
- fix144의 ERP 상단 필드 좌표 캐시 제거
- fix144의 회계일/전표관리단위 붙여넣기 직후 추가 sleep 제거
- ERP_CRITICAL_FIELD_WAIT 기본값을 fix143 기준 0.10초로 복구
- WEB/Agent 버전 1.0.133으로 bump

## 다음 작업
- py_compile 검증 완료
- graphify update 완료
- fix145 ZIP 생성/검증 완료: C:\Tmp\accounting_web_v1_revert_form_uia_cache_fix145_20260521_155204.zip
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 전달

## 주의사항
- fix144는 회계일이 적요/관리항목으로 들어가는 포커스 타이밍 문제를 만들었으므로 운영 배포 금지
- manager_server active source만 수정
- backup/hotfix/release 폴더 수정 금지
- 기존 unrelated dirty 파일은 stage하지 않음
