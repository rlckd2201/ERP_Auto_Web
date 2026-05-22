# SESSION STATE

## Current Work - 2026-05-22 fix151

- Implemented hardcoded vendor business-number matching for ERP vendor relation-item selection.
- Added/confirmed vendor business numbers:
  - 컴퓨존 `106-81-83458`
  - KT/케이티 `102-81-42945`
  - 현대오토에버/AutoEver `104-81-53190`
  - 다우기술/다우오피스 `220-81-02810`
  - 안랩 `214-81-83536`
  - 시큐어포인트/Genian/NAC `534-87-01726`
  - 동양정보통신 `402-81-23213`
  - 대신아이씨티 `504-86-20609`
  - 이테크시스템/Acronis `211-88-35257`
  - 에티버스 `106-81-43363`
- Parenthesized vendor codes such as `대신아이씨티(DS163)` are ignored during matching.
- WEB/Agent version is `1.0.141`.

## Previous Work - 2026-05-22 fix150

- Fixed selected invoice/work/recent job log display so long error messages wrap instead of expanding the page horizontally.
- Selected invoice logs are grouped into 실패 로그 and 성공/일반 로그, each capped to the most recent 10 visible rows.
- Work/job logs are grouped into 실패 로그 and 성공/진행 로그, each capped to the most recent 10 visible rows.
- Recent jobs are grouped into 실패 작업 and 성공/진행 작업, each capped to 10 visible jobs. Backend `/api/jobs` default limit is now 10.
- WEB/Agent version is `1.0.138`.
- Latest planned deploy ZIP: `C:\Tmp\accounting_web_v1_log_group_limit_fix150_20260522_141739.zip`.
- Verification so far: JS syntax check, Python py_compile for backend/Agent touched modules, `git diff --check`, and `graphify update .` completed with 1419 nodes / 4491 edges.

## 현재 작업
- fix148 KT/AutoEver 거래처 팝업 더블클릭 복구 작업중

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
- 팝업이 이미 열렸는지 먼저 확인하는 fix146 guard 유지
- 팝업이 안 열렸을 때 관계항목값 칸을 단일 클릭이 아닌 _double_click_form_xy()로 열도록 변경
- WEB/Agent 버전 1.0.136으로 bump

## 다음 작업
- py_compile 검증 완료
- graphify update 완료
- fix148 ZIP 생성/검증 완료: C:\Tmp\accounting_web_v1_vendor_popup_doubleclick_fix148_20260522_094339.zip
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 전달

## 주의사항
- 회계일/전표관리단위 상단 필드 타이밍은 건드리지 않음
- fix144 방식 재도입 금지
- manager_server active source만 수정
- backup/hotfix/release 폴더 수정 금지
- 기존 unrelated dirty 파일은 stage하지 않음
## 2026-05-22 fix149 진행 상태

- 정기 자동처리 전용 Agent 설정 및 서버 자동 큐 생성 구현 완료.
- 대상 PC: `172.17.30.243`.
- 출력 고정: `pyeongtaek` / `평택 프린터 (172.16.10.172)`.
- WEB/Agent 버전: `1.0.137`.
- 변경 파일:
  - `web_v1/backend/app.py`
  - `web_v1/backend/config.py`
  - `web_v1/backend/erp_queue.py`
  - `web_v1/backend/worker.py`
  - `web_v1/deploy/install_operating_server.ps1`
  - `web_v1/backend/UPDATE_NOTES.txt`
  - `web_v1/VERSION`
  - `web_v1/agent/erp_agent.py`
  - `graphify-out/`
  - `PROJECT_STATUS.md`
  - `CODEBASE_WIKI.md`
  - `SESSION_STATE.md`
- 검증:
  - py_compile 통과.
  - app import/dedupe helper smoke check 통과.
  - git diff --check 통과.
  - graphify update 완료.
- 남은 운영 확인:
  - 172.17.30.243 로그인 세션 유지/잠금 방지/절전 해제.
  - Agent 자동시작 및 `/api/regular-auto/status`에서 최근 heartbeat 확인.
  - ERP 설치 및 평택 프린터 매핑 확인.
  - 실제 정기 세금계산서 1건으로 ERP 전표 생성 후 평택 출력 E2E 확인.


## fix152 / 1.0.140
- 사업자번호 매핑 대상 거래처는 거래처 관계항목 셀과 팝업 검색칸 모두 사업자번호를 사용한다.
- 거래처명은 표시/적요용으로만 유지하고 ERP 거래처 검색값으로 쓰지 않는다.


## fix153 / 1.0.141
- ERP GUI 좌표 입력 전 K-System 메인 창을 최대화하고 창 크기를 로그로 검증한다.
- 좌표 기반 입력은 작은 창에서 금액/거래처/관리항목이 밀릴 수 있으므로 메뉴 진입 전과 폼 입력 직전에 최대화를 반복한다.

- fix153 timing: 정기처리 PC 기본값은 느린 모드이며 ERP_MGMT_SUMMARY_OPEN_WAIT=0.55, ERP_MGMT_AFTER_GRID_PASTE_WAIT=0.70, ERP_VENDOR_POPUP_OPEN_WAIT=0.55 기준으로 관리항목 입력을 기다린다.
