# SESSION STATE

## 현재 작업
- fix134 AutoEver/KT 거래처 사업자번호 붙여넣기 안정화 완료 단계

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
- AutoEver 사업자번호 `104-81-53190` 자체만 들어와도 특수 거래처 입력 루트를 타게 함
- 거래처 팝업 사업자번호 입력을 `pyautogui.write()`에서 클립보드 붙여넣기로 변경
- 확인된 키보드 시퀀스 유지: Tab 4, Down 5, Up 1, Tab 3, Enter 2
- WEB/Agent 버전 1.0.122로 bump
- py_compile 통과
- fix134 ZIP 생성/검증 완료: C:\Tmp\accounting_web_v1_vendor_biz_paste_fix134_20260520_114023.zip
- graphify update 시도했으나 1298 vs 1383 node 감소로 overwrite 거부, 기존 graph 유지

## 다음 작업
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령 전달

## 주의사항
- manager_server 활성 파일만 수정
- backup/hotfix/release 폴더 수정 금지
- worktree에 unrelated dirty/delete가 많으므로 관련 파일만 stage
