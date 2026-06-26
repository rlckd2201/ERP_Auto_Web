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

## 2026-06-25 Agent 접속 타임아웃
- 담당자 PC에서 `run_agent.ps1 -Server https://172.17.39.121:8081` 실행 시 `/api/agent/heartbeat` 연결 타임아웃 발생.
- 원인 범위: 서버 8081 미기동, 서버 방화벽 8081 미허용, 서버 바인딩/네트워크 경로 문제.
- Agent는 서버 접속 실패 시 Traceback 종료 대신 stderr에 짧게 출력하고 재시도하도록 수정했다.
- 수정 후 `py_compile` 통과, `pytest tests -q` 결과: 2 passed, `graphify update .` 완료.

## 2026-06-25 PowerShell 5.1 스크립트 인코딩
- 서버에서 `run_server.ps1`의 한글 `throw` 메시지가 Windows PowerShell 5.1 기본 인코딩으로 깨져 parser error 발생.
- `run_server.ps1`, `run_agent.ps1`의 throw 메시지를 ASCII 영어로 변경했다.
- `[scriptblock]::Create((Get-Content .\run_server.ps1 -Raw))` 및 `run_agent.ps1` parse 검증 통과.
- `pytest tests -q` 결과: 2 passed.

## 2026-06-25 Agent self-signed SSL 오류
- 담당자 PC Agent가 `SSLCertVerificationError: self-signed certificate`로 서버 heartbeat 실패.
- 테스트용으로 `agent_worker.py --insecure-skip-tls-verify`와 `run_agent.ps1 -InsecureSkipTlsVerify` 옵션을 추가했다.
- 운영 안정화 시 담당자 PC에 `C:\ERP_DB\certs\web_v1.cert.pem` 신뢰 등록 후 TLS 검증을 켜고 실행하는 쪽이 더 좋다.
- 수정 후 `py_compile` 통과, `pytest tests -q` 결과: 2 passed, `run_agent.ps1` parse 검증 통과, `graphify update .` 완료.

## 2026-06-26 출력/메일/계정 확장
- 172.17.30.243 프린터 연결 완료 전제로 Agent 출력 제출 단계를 추가했다.
- 현재 출력물은 ERP 자동입력 전 dry-run 전표 HTML 산출물이다. 실제 ERP 화면 입력/ERP 자체 출력은 후속 연결 필요.
- `run_agent.ps1` 기본값은 `-PrintMode default-printer`이며 테스트 시 `-PrintMode off`로 출력 없이 검증 가능하다.
- 웹 업로드 UI는 파일 선택과 드래그 앤 드롭을 모두 지원한다.
- 로그인/세션/비밀번호 해시는 로컬 SQLite에 저장한다.
- 그룹웨어 MariaDB는 `gw_emp`, `ds_t_emp`를 `SHOW COLUMNS`와 `SELECT`로만 읽는다.
- 외부 DB에는 쓰기 SQL을 넣지 않았다. 운영 시 반드시 읽기 전용 DB 계정을 사용한다.
- 신규 동기화 계정 초기 비밀번호는 `wowjd12!@`, 최초 로그인 및 비밀번호 찾기 후 변경 강제.
- 완료 메일은 Agent 결과에 `print_submitted=true`가 있을 때 발송한다.
- SMTP 미설정 시 메일은 `data/mail_outbox` JSON으로 보관된다.
- 검증: `py_compile` 통과, PowerShell scriptblock parse 통과, `pytest tests -q` 결과 5 passed, `node --check app/static/app.js` 통과, `/api/settings` TestClient smoke 200.

## 2026-06-26 기존 메일/DB 기본값 반영
- 그룹웨어 DB 기본 계정은 `dlpadmin2`를 사용하도록 반영했다.
- 기존 회계업무 WEB의 메일 기본값을 참고해 SMTP 기본값을 `35.216.76.148:25`, 발신자 `admpdm@dae-seung.co.kr`로 맞췄다.
- 기존 전산 코드처럼 SMTP 서버가 STARTTLS를 지원할 때만 TLS를 시작하도록 수정했다.
- 실제 DB 컬럼 확인: `gw_emp.EmpID`, `gw_emp.GwID`, `gw_emp.Use_yn`, `ds_t_emp.EmpID`, `ds_t_emp.kor_name`, `ds_t_emp.bu_code`, `ds_t_emp.DeptName`, `ds_t_emp.use_yn`.
- 재정 하위 부서 활성 계정 조회 결과 17건 확인.
- `gw_emp`에 직접 메일 주소 컬럼은 없어서 `GwID@dae-seung.co.kr` 형식으로 수신 메일을 만든다.

## 2026-06-26 전산 관리자 계정 동기화
- 기존 회계업무 WEB 기본 전산 계정은 `rlckd9646 / 김기창`.
- 새 시스템 시작 시와 전산 계정 로그인 직전에 `C:\ERP_DB\learned_data.db`의 `users` 테이블에서 `rlckd9646` 계정을 다시 읽어 동기화한다.
- 기존 DB에서 읽은 전산 계정은 비밀번호 변경 상태까지 새 시스템 로컬 해시에 반영한다.
- 기존 DB를 읽을 수 없을 때는 새 시스템 로컬 DB에 있는 계정 비밀번호를 유지한다.
- 기존 DB에도 계정이 없을 때만 fallback으로 `eotmd12!@`를 사용한다.

## 2026-06-26 담당자용 UI 정리
- 헤더에서 Agent ID/IP 노출 제거.
- 업로드 영역을 전면 배치하고 드래그 앤 드롭 영역 높이를 확대했다.
- 업로드 시작 즉시 처리 현황 카드에 진행률을 표시한다.
- 작업 큐/데이터 서버/Agent 같은 내부 용어는 화면에서 빼고 접수, 자료 확인, 전표 처리, 출력 단계로 표시한다.
- 검증: `node --check app/static/app.js` 통과, `pytest tests -q` 결과 7 passed.
