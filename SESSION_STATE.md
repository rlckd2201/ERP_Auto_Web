# SESSION STATE

## 현재 작업
- fix142 Vendor Popup Click Guard 작업중

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
- AutoEver/KT 거래처 팝업 열기에서 pyautogui.doubleClick(x, y) 제거
- 기존값 삭제 후 팝업 열기 클릭을 한 번 보내고, 팝업 감지 즉시 추가 클릭 중단
- 팝업 미감지 시에만 두 번째 클릭 fallback
- WEB/Agent 버전 1.0.130로 bump
- 업데이트 노트와 상태 문서 갱신`r`n- Graphify 갱신 완료`r`n- fix142 ZIP 생성/검증 완료: C:\Tmp\accounting_web_v1_vendor_popup_click_fix142_20260521_105500.zip

## 다음 작업
- Graphify 갱신
- fix142 ZIP 생성 및 검증
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 전달

## 주의사항
- manager_server active source만 수정
- backup/hotfix/release 폴더 수정 금지
- 기존 unrelated dirty 파일은 stage하지 않음
- 로컬 pythonw Agent가 개발폴더를 되돌릴 수 있어 확인 후 종료함