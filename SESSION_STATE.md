# SESSION STATE

## 현재 작업
- fix114 트레이 우클릭 메뉴 / 정기 다우기술 거래처명 수정 작업중

## 현재 수정중 파일
- web_v1/agent/erp_agent.py
- web_v1/backend/erp_runner.py
- web_v1/VERSION
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md

## 방금 수정한 내용
- Agent 트레이 우클릭 메뉴가 `None is not a valid string in this context`로 실패하던 원인을 수정
- pywin32 `AppendMenu(..., MF_SEPARATOR, 0, "")` 방식으로 구분선 생성 검증
- 정기 ERP payload에서 `(주)다우기술` 같은 원본 공급자명을 ERP 입력용 `다우기술` 기준명으로 정규화
- WEB/Agent 버전 1.0.102 bump
- 업데이트 노트 fix114 갱신
- 작업 중 서버 1.0.101 self-update가 개발 폴더를 덮어써서 로컬 Agent 종료 및 HKCU Run 키 임시 제거
- graphify update . 완료: 1330 nodes, 4238 edges, 79 communities
- fix114 ZIP 생성 및 내용 검증 완료: C:\Tmp\accounting_web_v1_tray_menu_daou_vendor_fix114_20260515_140924.zip

## 다음 작업
- git status 확인 후 관련 파일만 stage/commit/push
- 운영서버 172.17.39.121에 fix114 ZIP 배포
- 서버 배포 후 Agent 재실행/자동실행 재등록

## 주의사항
- 서버를 1.0.102로 먼저 올리기 전까지 로컬 Agent를 다시 켜면 1.0.101 payload로 개발 폴더를 다시 덮어쓸 수 있음
- active source는 web_v1 기준
- backup / hotfix / release 계열 폴더 수정 금지
