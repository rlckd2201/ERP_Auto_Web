# SESSION STATE

## 현재 작업
- fix143 Vendor Popup Timing Buffer 작업중

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
- AutoEver/KT 거래처 팝업 열기/감지/붙여넣기 주변에 0.1초 여유 추가
- 첫 팝업 감지 wait/timeout을 0.18/0.25에서 0.28/0.35로 조정
- fallback wait/timeout을 ERP_FORM_WAIT/3.0에서 ERP_FORM_WAIT+0.1/3.1로 조정
- 팝업 감지 후 붙여넣기 전 0.1초, 붙여넣기 후 Tab 전 0.1초 추가
- WEB/Agent 버전 1.0.131로 bump`r`n- Graphify 갱신 완료`r`n- fix143 ZIP 생성/검증 완료: C:\Tmp\accounting_web_v1_vendor_popup_timing_fix143_20260521_132030.zip

## 다음 작업
- Graphify 갱신
- fix143 ZIP 생성 및 검증
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 전달

## 주의사항
- manager_server active source만 수정
- backup/hotfix/release 폴더 수정 금지
- 기존 unrelated dirty 파일은 stage하지 않음
- 줄 단위 PowerShell 편집으로 한글이 깨질 수 있어 UTF-8 원문 복구 후 작은 diff만 재적용함