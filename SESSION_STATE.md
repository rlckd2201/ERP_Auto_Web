# SESSION STATE

## 현재 작업
- fix117 작업중
- 기존 문서 출력/정기 원클릭 전 자동 저장이 수신내역 상태를 대기중으로 되돌리는 문제 수정

## 현재 수정중 파일
- web_v1/backend/app.py
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md

## 방금 수정한 내용
- 원인: `startErpQueue()`가 원클릭 전 선택 상세를 자동 저장하고, `purchase-analysis` / `regular-data` 저장 API가 실제 변경 여부와 무관하게 `reset_invoice()`를 호출했음
- 이미 처리완료/문서세트 준비 완료인 건도 같은 값으로 자동 저장되면 수신내역 상태가 `대기중`으로 돌아갈 수 있었음
- `app.py`에 구매/정기 editable snapshot 비교를 추가해 화면 payload가 기존 저장값과 동일하면 JSON 저장 및 상태 초기화를 건너뜀
- WEB/Agent 버전 1.0.105 bump
- 업데이트 노트 fix117 갱신
- py_compile, frontend node check, 정기 snapshot 회귀 테스트 통과
- graphify update 완료: 1339 nodes, 4264 edges, 81 communities
- fix117 ZIP 생성 및 내용 검증 완료: C:\Tmp\accounting_web_v1_noop_save_status_fix117_20260515_161724.zip

## 다음 작업
- 관련 파일만 commit/push
- 운영서버 172.17.39.121 배포 명령 제공

## 작업 기준
- `.codex/hooks.json`의 반복 PreToolUse graphify 안내 훅은 끔. Graphify 규칙은 `AGENTS.md` 기준으로 사람이 직접 지킨다.
- 커밋은 기능 단위로 1회만 한다. 상태문서만 따로 추가 커밋하지 않는다.
- 문서 갱신은 작업 종료 직전에 한 번에 하고, 코드/문서/graphify를 가능하면 같은 기능 커밋에 묶는다.
- Graphify update는 의미 있는 코드 변경 뒤에만 실행한다. 단순 조사, 명령어 제공, 문서 문구 수정만으로는 실행하지 않는다.
- ZIP은 검증 완료 후 1개만 만들고, 같은 fix 번호로 재생성하지 않는다. 재생성이 필요하면 다음 fix 번호로 올린다.
- 운영 배포 전에는 `git diff --name-status HEAD --` 기준으로 실제 변경 파일만 확인하고, `git status`의 노이즈는 바로 커밋 대상으로 보지 않는다.

## 주의사항
- active source는 web_v1
- backup / hotfix / release 폴더 수정 금지
- 로컬 Agent pythonw가 켜지면 서버 payload로 개발 폴더를 덮어쓸 수 있으니 작업 중 Agent 중지 유지
- 작업트리에 unrelated dirty 파일이 많으므로 stage/commit은 fix117 관련 파일만
