# DEBUG.md

## 주의사항
- 기존 세금계산서 수신/Zoom/정기처리 기능을 임의로 삭제하지 않는다.
- 기존 기능과 신규 엑셀 업로드 전표처리는 분리해서 설계한다.
- Agent 작업 큐, 담당자별 설정, ERP 자동입력 흐름을 먼저 파악한다.
- graphify 결과를 먼저 읽고 관련 파일만 좁게 연다.
- 긴 로그와 시행착오는 이 파일에 갱신한다.

## 2026-06-25 초기 구현 메모
- graphify 리포트 확인 결과 기존 중심은 `ERPAutoApp`, `JobCreateRequest`, Agent 큐 관련 함수다.
- 신규 시스템은 기존 `web_v1`을 직접 수정하지 않고 `excel_voucher_web`에 독립 구성했다.
- 기존 Agent 큐 패턴은 파일 기반이지만 신규 MVP는 SQLite 큐로 시작한다.
- 실제 ERP 입력은 후속으로 `agent/agent_worker.py`의 `run_erp_voucher_task()`에 연결한다.
- Python 실행 파일은 샌드박스 밖 `C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe`에서 확인했다.
- `py_compile` 검증 통과.
- `pytest tests -q` 결과: 1 passed.
- `graphify update .` 완료. 1차 120초 제한에서는 타임아웃, 2차 300초 제한에서 완료됐다.
- 로컬 서버 `http://127.0.0.1:18100` 기동 확인.
- API smoke test 통과: 테스트 엑셀 업로드 200, 큐 상태 `queued`, Agent claim `claimed`, 완료 처리 `done`.
