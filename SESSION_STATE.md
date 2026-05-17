# SESSION STATE

## 현재 작업
- fix119 작업중
- old CS `admin_viewer.py` 대신 WEB에서 운영 DB를 직접 볼 수 있게 수정

## 현재 수정중 파일
- web_v1/backend/app.py
- web_v1/frontend/admin_db.html
- web_v1/frontend/admin_db.js
- web_v1/frontend/admin_db.css
- web_v1/frontend/app.js
- web_v1/frontend/styles.css
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md

## 방금 수정한 내용
- 원인: `admin_viewer.py`는 현재 WEB v1에 없는 `/api/dictionary`, `/api/update_dict`, `/api/delete_dict`를 호출하는 old CS용 파일이었음
- `/admin-db` 브라우저 DB 보기 화면 추가
- `/api/admin/db/overview`, `/api/admin/db/table` 읽기 전용 API 추가
- 메인 WEB detail/admin 모드에서 `DB 보기` 버튼을 동적으로 추가
- WEB/Agent 버전 1.0.107 bump
- fix119 ZIP 생성 및 내용 검증 완료: C:\Tmp\accounting_web_v1_admin_db_view_fix119_20260518_083745.zip

## 다음 작업
- 관련 파일만 stage/commit/push
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
- 작업트리에 unrelated dirty 파일이 많으므로 stage/commit은 fix119 관련 파일만
