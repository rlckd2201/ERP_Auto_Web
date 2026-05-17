# SESSION STATE

## 현재 작업
- fix118 작업중
- 컴퓨존 구매 분석에서 신규 품목명이 견적서 원문 그대로 들어가는 문제 수정

## 현재 수정중 파일
- web_v1/backend/purchase_analysis.py
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md

## 방금 수정한 내용
- 원인: `_ai_parse()` 함수는 있었지만 `analyze_purchase_documents()`에서 `ai_data = None`으로 고정되어 Gemini 분석이 실제로 호출되지 않았음
- 신규 컴퓨존 품목은 학습 DB 매칭 실패 시 fast_parse 결과가 그대로 남아 견적서 원문이 품목명으로 들어갔음
- unknown purchase items가 있으면 `GEMINI_API_KEY` 설정 시 `_ai_parse()`를 호출하게 연결
- AI 미설정/실패 시에도 컴퓨존 소모품류는 `USB 3구 멀티탭`, `블루투스 스피커`, `차량용 공기청정기`, `차량용 무선충전 거치대`, `모니터 받침대`처럼 기본 축약되게 fallback 추가
- WEB/Agent 버전 1.0.106 bump
- 업데이트 노트 fix118 갱신
- py_compile, frontend node check, 품목명 축약 회귀 테스트, empty learning DB 처리 회귀 테스트 통과
- graphify update 완료: 1347 nodes, 4277 edges, 81 communities
- fix118 ZIP 생성 및 내용 검증 완료: C:\Tmp\accounting_web_v1_compuzone_ai_item_names_fix118_20260518_081512.zip

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
- 작업트리에 unrelated dirty 파일이 많으므로 stage/commit은 fix118 관련 파일만
