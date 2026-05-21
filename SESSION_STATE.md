# SESSION STATE

## 현재 작업
- fix144 ERP 상단 폼 UIA/COM 안정화 작업중

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
- 전표관리단위/회계일 같은 중요 상단 필드 입력 전후 안정 대기 기본값을 0.20초로 조정
- 분개전표입력 폼 세팅 시작 시 K-System 메인 창 좌표를 캐시하고 좌표 우선 입력에서는 캐시 좌표를 사용하도록 변경
- WEB/Agent 버전 1.0.132로 bump
- py_compile/Graphify 검증 완료
- fix144 ZIP 생성/검증 완료: C:\Tmp\accounting_web_v1_form_uia_cache_fix144_20260521_144639.zip

## 다음 작업
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 전달

## 주의사항
- manager_server active source만 수정
- backup/hotfix/release 폴더 수정 금지
- 기존 unrelated dirty 파일은 stage하지 않음
- 상단 필드 튕김은 거래처 팝업 문제가 아니라 K-System UIA/COM 안정화 문제로 분리해서 본다
