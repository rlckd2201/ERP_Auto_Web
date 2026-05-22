# SESSION STATE

## Current Work - 2026-05-22 fix149

- Implemented regular auto-processing for dedicated Agent PC `172.17.30.243`.
- Output is fixed to `pyeongtaek` / `평택 프린터 (172.16.10.172)`.
- WEB/Agent version is `1.0.137`.
- Verification passed: py_compile, app import/dedupe smoke check, git diff --check, and graphify update.
- Next operational E2E: keep the robot PC logged in/unlocked, confirm Agent heartbeat in `/api/regular-auto/status`, then test one real regular invoice through ERP voucher creation and Pyeongtaek printing.

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
