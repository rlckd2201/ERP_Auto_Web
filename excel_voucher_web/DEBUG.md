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

## 2026-06-25 샘플 수시결제 파일 분석
- 파일: `5월 대승 수시결제.xlsx`.
- 시트: `수시결제어음`, `수시결제현금`, `인터넷뱅킹`, `필수확인`.
- `수시결제현금`: 190개 대상 행, 코드 E열, 업체명 F열, 원본 적요 G열.
- `수시결제현금` H열은 data_only 기준 1~190으로 저장되어 실제 금액으로 부적합.
- `인터넷뱅킹`: 190개 이체 행, D열 합계 `1,019,546,751`.
- 승인서 상단 합계 `1,019,546,751원 190(件)`와 `인터넷뱅킹` 합계/건수가 일치.
- 사용자 확인: 전표 작성 대상은 `수시결제현금` 시트에 있는 것만 사용한다.
- 변환기는 `수시결제현금` H열 금액을 우선 사용한다.
- 샘플처럼 H열이 순번으로 저장되어 승인서 합계와 다를 때만 `인터넷뱅킹` D열을 보조 금액으로 같은 순번 매칭한다.
- 샘플 변환 검증 결과: `source_rows=190`, `line_count=191`, `debit_total=1,019,546,751`, `credit_total=1,019,546,751`.
- 샘플 첫 분개 row: `미지급금(원화)		82500000	0	5월 수시결제 - 테스트슈어랩(TS042)`.
- 샘플 마지막 대변 row: `보통예금		0	1019546751	5월 수시결제 - 신한은행`.
- 수정 후 `py_compile` 통과, `pytest tests -q` 결과: 2 passed.
- `graphify update .` 재실행 완료. 1932 files AST extraction, 4645 nodes, 36768 edges.
