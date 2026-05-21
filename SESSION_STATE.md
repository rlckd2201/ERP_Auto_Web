# SESSION STATE

## 현재 작업
- fix146 KT/AutoEver 거래처 사업자번호 팝업 입력 복구 작업중

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
- 거래처 관계항목 기존값 삭제 직후 팝업 선감지 추가
- 팝업이 이미 열렸으면 추가 클릭 생략하고 기본 검색 텍스트박스 포커스 유지
- 팝업 열기 fallback 클릭을 raw pyautogui.click(x, y)에서 _click_form_xy()로 변경
- WEB/Agent 버전 1.0.134로 bump

## 다음 작업
- py_compile 검증 완료
- graphify update 완료
- fix146 ZIP 생성/검증 완료: C:\Tmp\accounting_web_v1_vendor_popup_precheck_fix146_20260522_082859.zip
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 전달

## 주의사항
- 회계일/전표관리단위 상단 필드 타이밍은 건드리지 않음
- fix144 방식 재도입 금지
- manager_server active source만 수정
- backup/hotfix/release 폴더 수정 금지
- 기존 unrelated dirty 파일은 stage하지 않음
