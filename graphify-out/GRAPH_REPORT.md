# Graph Report - erp_auto_web_release_1c2c9c5  (2026-07-16)

## Corpus Check
- 111 files · ~170,548 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2503 nodes · 7286 edges · 190 communities (143 shown, 47 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 635 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9b72175b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- JobStore
- main.py
- config.py
- UplusEdocuHandler
- app.py
- .process
- SmartBillHandler
- 전표 자동화 프로그램(담당자용)_v6.2.py
- app.js
- Communities
- app.py
- .get
- purchase_analysis.py
- app.js
- agent_adapter.py
- RuntimeError
- ._do_process
- erp_agent.py
- regular_due_monitor.py
- erp_runner.py
- SmileEdiHandler
- UplusEdocuHandler
- CODEBASE WIKI
- Project Status
- repair_db_rows
- parse_tax_invoice_xml
- setup_state.py
- collect_mail_once
- AI Work Memory
- KtAttachmentHandler
- AutoEverHandler
- CsbillHandler
- XmlAttachmentHandler
- main
- Accounting automation WEB v1 package.
- parse_tax_invoice_xml
- AccountStore
- notifications.py
- invoice_db.py
- Excel voucher web application.
- WehagoHandler
- JobStore
- test_manager_vendor_search.py
- compuzone_quote.py
- Devlog
- voucher_builder.py
- parse_tax_invoice_xml
- BaseTaxInvoiceHandler
- JobCreateRequest
- BaseModel
- DEBUG.md
- HometaxHandler
- fetch_finance_users
- settings.py
- SESSION STATE
- admin_db.js
- test_voucher_builder.py
- Graph Report - 세금계산서 크롤링  (2026-04-30)
- Handover
- Feature Ledger
- worker.py
- Excel Voucher Web
- 운영서버 복붙 명령
- AILearningViewer
- Project State
- DECISIONS.md
- SESSION.md
- Decisions
- WEB v1.0 Operating Server Deploy
- TODO.md
- 회계업무 자동화 WEB v1.0
- _build_user_pc_payload_zip
- api_admin_db_overview
- approval_fetcher.py
- AGENTS.md
- main
- AGENTS.md
- api_unhandled_exception_handler
- User Feedback
- regular_due_history_page
- 2026-05-20 fix130 AutoEver Password Extraction
- 2026-05-20 fix131 AutoEver Password Pattern
- 2026-05-21 fix139 Agent Protocol Gesture
- AI_HANDOFF.md
- __init__.py
- __init__.py
- 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)
- 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)
- 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)
- 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- Run a dry-run print preview or the real legacy ERP automation on the voucher PC
- Placeholder for the real ERP UI automation run on the automatic voucher PC Agent
- Placeholder for the real ERP UI automation run on the automatic voucher PC Agent
- Placeholder for the real ERP UI automation run on the 담당자 PC Agent.
- 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)
- The legacy UI module imports fitz at module load, but ERP input does not use it
- The legacy UI module imports fitz at module load, but ERP input does not use it
- The legacy UI module imports fitz at module load, but ERP input does not use it
- The legacy UI module imports fitz at module load, but ERP input does not use it
- The legacy UI module imports fitz at module load, but ERP input does not use it
- The legacy UI module imports fitz at module load, but ERP input does not use it

## God Nodes (most connected - your core abstractions)
1. `Communities` - 101 edges
2. `ERPAutoApp` - 90 edges
3. `SmileEdiHandler` - 64 edges
4. `get_invoice()` - 57 edges
5. `Project Status` - 53 edges
6. `CODEBASE WIKI` - 51 edges
7. `AI Work Memory` - 46 edges
8. `BaseTaxInvoiceHandler` - 36 edges
9. `WehagoHandler` - 36 edges
10. `add_invoice_log()` - 36 edges

## Surprising Connections (you probably didn't know these)
- `_run_real_erp_voucher_task()` --calls--> `_validate_install_info()`  [INFERRED]
  excel_voucher_web/app/agent_adapter.py → web_v1/backend/erp_runner.py
- `_run_real_erp_voucher_task()` --calls--> `ERPLoginBot`  [INFERRED]
  excel_voucher_web/app/agent_adapter.py → manager_server/전표 자동화 프로그램(담당자용)_v6.2.py
- `_job_response()` --calls--> `get_job()`  [INFERRED]
  excel_voucher_web/app/main.py → web_v1/backend/app.py
- `api_upload_voucher()` --calls--> `create_job()`  [INFERRED]
  excel_voucher_web/app/main.py → web_v1/backend/app.py
- `api_jobs()` --calls--> `list_jobs()`  [INFERRED]
  excel_voucher_web/app/main.py → web_v1/backend/app.py

## Import Cycles
- None detected.

## Communities (190 total, 47 thin omitted)

### Community 0 - "JobStore"
Cohesion: 0.10
Nodes (12): JobStore, JobEvent, JobRecord, JobStore, Any, datetime, JobStatus, utc_now() (+4 more)

### Community 1 - "main.py"
Cohesion: 0.10
Nodes (55): _agent_payload(), api_admin_agent_commands(), api_admin_create_agent_command(), api_admin_reset_jobs(), api_admin_server_update(), api_agent_admin_complete(), api_agent_admin_next(), api_agent_heartbeat() (+47 more)

### Community 2 - "config.py"
Cohesion: 0.10
Nodes (27): _active_invoice_items(), claim_next_erp_task(), now_text(), Any, Path, _read_task(), _task_files(), update_erp_task() (+19 more)

### Community 3 - "UplusEdocuHandler"
Cohesion: 0.16
Nodes (3): Path, LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, UplusEdocuHandler

### Community 4 - "app.py"
Cohesion: 0.37
Nodes (17): StreamingResponse, api_delete_invoice(), api_get_invoice(), api_get_invoice_logs(), api_list_invoices(), api_retry_invoice(), create_demo_job(), create_job() (+9 more)

### Community 5 - ".process"
Cohesion: 0.06
Nodes (23): UplusEDocuHandler, LG U+ eDocu tax invoice portal adapter.  This adapter intentionally routes edo, UplusPortalHandler, main(), print_result(), 세금계산서 크롤링 모듈 개별 테스트 도구 실행: python test.py  포털별로 URL/파일경로를 직접 입력해서 단독 테스트 가능., URL 자동 감지 테스트 (crawler_main 사용), test_auto() (+15 more)

### Community 6 - "SmartBillHandler"
Cohesion: 0.11
Nodes (21): BaseTaxInvoiceHandler, _clean_token(), _is_better_parse(), portal_name(), Path, SmartBill print flow based on the actual HTML fnPrint() logic.      The print, 화면을 가리는 광고(크레포트 등)를 닫습니다., 수신미승인 상태면 승인 처리를 진행하고,         최종적으로 '인쇄' 버튼이 렌더링되었는지 확인합니다. (+13 more)

### Community 7 - "전표 자동화 프로그램(담당자용)_v6.2.py"
Cohesion: 0.08
Nodes (17): _is_sane_amount(), _normalize_biz_no(), _normalize_issue_date(), 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence), AppManager, _detect_erp_target_monitor(), ERPConfig, _ErpGuiAutomationLock (+9 more)

### Community 8 - "app.js"
Cohesion: 0.06
Nodes (136): escapeHtml(), refreshJobs(), accountOptions(), addLog(), agentConnectedFromSetup(), agentUpdateRequiredFromSetup(), applyDetailMode(), applyModeUi() (+128 more)

### Community 9 - "Communities"
Cohesion: 0.02
Nodes (101): Communities, Community 0 - "Community 0", Community 100 - "Community 100", Community 101 - "Community 101", Community 102 - "Community 102", Community 103 - "Community 103", Community 104 - "Community 104", Community 10 - "Community 10" (+93 more)

### Community 10 - "app.py"
Cohesion: 0.07
Nodes (99): admin_db_page(), _agent_bootstrap_script(), _agent_cmd_launcher(), _agent_exe_launcher(), _agent_update_notes(), api_agent_job_complete(), api_agent_job_event(), api_agent_job_expense_report_upload() (+91 more)

### Community 12 - "purchase_analysis.py"
Cohesion: 0.23
Nodes (31): _to_int(), _ai_parse(), analyze_purchase_documents(), _clean_match_text(), _clean_text(), _collapse_duplicate_total_prices(), _extract_amounts_from_tax(), _extract_compuzone_quote_items() (+23 more)

### Community 13 - "app.js"
Cohesion: 0.15
Nodes (42): appendErpCredentials(), applyAuthUi(), askErpCredentials(), badge(), canUseApp(), changePassword(), commandStatus(), commandTitle() (+34 more)

### Community 14 - "agent_adapter.py"
Cohesion: 0.20
Nodes (29): _apply_company_erp_credentials(), _archive_pdf(), _clean_management_items(), _clipboard_account_name(), _clipboard_vendor_value(), _fallback_bank_management_items(), _fallback_line_management_items(), _file_uri() (+21 more)

### Community 15 - "RuntimeError"
Cohesion: 0.08
Nodes (70): _connection_error_message(), _download_job_source(), _execute_admin_command(), _heartbeat(), _install_agent_task(), _latest_agent_log(), main(), _normalize_printer_name() (+62 more)

### Community 16 - "._do_process"
Cohesion: 0.19
Nodes (3): 메일 본문에서 법인 키워드를 찾아 사업자번호 후보 dict 반환., 유니포스트 etax 세금계산서 핸들러 대상: etax.unipost.co.kr, UnipostHandler

### Community 17 - "erp_agent.py"
Cohesion: 0.08
Nodes (51): CompletedProcess, _acquire_single_instance(), _agent_bundle_hash(), _agent_update_required(), AgentTray, _apply_server_setup_config(), _cert_cache_path(), _cert_store_has_thumbprint() (+43 more)

### Community 18 - "regular_due_monitor.py"
Cohesion: 0.12
Nodes (59): api_regular_due_check(), _add_months(), _alert_hour(), _alert_start_date(), _amount(), build_regular_due_report(), _clean_text(), _compact() (+51 more)

### Community 19 - "erp_runner.py"
Cohesion: 0.16
Nodes (43): build_purchase_erp_payload(), build_regular_erp_payload(), _clean_text(), _configure_pyautogui_for_server(), _corp_codes(), _extract_invoice_date(), _extract_invoice_date_from_text(), _extract_pdf_text_for_date() (+35 more)

### Community 20 - "SmileEdiHandler"
Cohesion: 0.09
Nodes (5): main(), Path, WebDriver, SmileEdiHandler, WebElement

### Community 21 - "UplusEdocuHandler"
Cohesion: 0.05
Nodes (7): Service, EtaxUnipostHandler, Chrome, InvoiceMailWatcher, Path, LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, UplusEdocuHandler

### Community 22 - "CODEBASE WIKI"
Cohesion: 0.04
Nodes (51): 2026-05-22 Log Display Notes, 2026-05-22 Regular Auto-Agent Notes, 2026-05-22 Vendor Business Number Notes, Agent Architecture, CODEBASE WIKI, Common Pitfalls, Configuration, Current Handoff (+43 more)

### Community 23 - "Project Status"
Cohesion: 0.04
Nodes (50): 2026-05-18 fix123 selective output documents, 2026-05-18 fix124 KT vendor business-number row selection, 2026-05-18 fix125 KT vendor business-number popup search, 2026-05-18 fix126 KT vendor keyboard sequence, 2026-05-18 fix126 KT vendor search input, 2026-05-18 fix127 KT vendor final double-enter, 2026-05-18 fix128 setup installer reuse, 2026-05-18 fix129 Chrome notifications (+42 more)

### Community 24 - "repair_db_rows"
Cohesion: 0.58
Nodes (9): build_pdf_filename(), clean_token(), dedupe_path(), parse_pdf(), patch_crawler_file(), repair_db_rows(), safe_name(), site_from_biz_no() (+1 more)

### Community 25 - "parse_tax_invoice_xml"
Cohesion: 0.53
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 26 - "setup_state.py"
Cohesion: 0.12
Nodes (45): STAThread, string, api_agent_heartbeat(), _active_install_job(), _add_check(), _age_seconds(), authenticate_user(), change_initial_password() (+37 more)

### Community 27 - "collect_mail_once"
Cohesion: 0.09
Nodes (47): IMAP4_SSL, LogRecord, ProgressCallback, AutoEverHandler(), crawl_invoice(), _csbill_link_bill_no(), _csbill_link_priority(), CsbillHandler() (+39 more)

### Community 28 - "AI Work Memory"
Cohesion: 0.04
Nodes (46): 2026-04-30 SmartBill PDF text fallback parse, 2026-04-30 SmartBill/WEHAGO crawler fix, 2026-04-30 SmartBill/WEHAGO hardening after repeat failure, 2026-04-30 TAB1 XML / 결의서 혼합 계정 버그 수정, 2026-04-30 WEHAGO PDF 저장 다이얼로그 '새 폴더' 생성 및 오작동 완벽 수정, 2026-04-30 WEHAGO PDF 저장 다이얼로그 '새 폴더' 클릭 오작동 수정, 2026-04-30 WEHAGO Save As new-folder guard, 2026-04-30 WEHAGO Save As overwrite guard refinement (+38 more)

### Community 31 - "CsbillHandler"
Cohesion: 0.22
Nodes (3): CsbillHandler, Path, WebDriver

### Community 37 - "parse_tax_invoice_xml"
Cohesion: 0.48
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 39 - "AccountStore"
Cohesion: 0.12
Nodes (24): AccountStore, AccountUser, hash_password(), now_text(), protect_secret(), Any, Connection, Path (+16 more)

### Community 40 - "notifications.py"
Cohesion: 0.18
Nodes (40): EmailMessage, _add_attachment(), _attachment_paths(), completion_mail_body(), completion_mail_html(), _details_table(), _diagnostic_attachment(), _display_address() (+32 more)

### Community 42 - "invoice_db.py"
Cohesion: 0.30
Nodes (31): add_invoice_log(), _clean_int(), _columns(), delete_invoice(), detect_invoice_type(), _ensure_column(), get_conn(), get_invoice_by_pdf_path() (+23 more)

### Community 44 - "WehagoHandler"
Cohesion: 0.10
Nodes (7): Path, WEHAGO URL의 Base64 토큰에서 사업자번호(10자리) 추출.         예: .../eTaxMail/VFgyMDI2MDQ2OTQ, visible text input 중 마지막 = 모달 입력창.         확인 클릭 후 visible inputs 수가 줄면 인증 성공., Chrome 외부 앱 실행 권한 팝업에서 '허용' 버튼을 자동 클릭.         WEHAGO 인쇄 버튼 이후 1회성 팝업이 뜨는 구조라,, UIA? ? ?? ?? Chrome ?? ??? ?? ??? ??? ??., Microsoft Print to PDF sometimes ignores the target folder.         If the corr, WehagoHandler

### Community 45 - "JobStore"
Cohesion: 0.17
Nodes (14): JobStore, _json_dumps(), _json_loads(), now_text(), Any, Connection, JobEvent, JobRecord (+6 more)

### Community 46 - "test_manager_vendor_search.py"
Cohesion: 0.12
Nodes (14): _FakeControl, _FakeLogger, _FakeRect, _load_nested_functions(), test_finance_first_result_does_not_press_enter_when_mdi_stays_open(), test_finance_first_vendor_detects_same_handle_title_transition_after_double_click(), test_finance_first_vendor_executes_required_search_order(), test_finance_vendor_state_uses_popup_once_then_preserves_bank_path() (+6 more)

### Community 47 - "compuzone_quote.py"
Cohesion: 0.22
Nodes (30): auto_attach_compuzone_quote(), _clean_order_no(), _click_print_button(), _close_context(), _compuzone_accounts(), CompuzoneQuoteError, _emit(), fetch_compuzone_quote_pdf() (+22 more)

### Community 48 - "Devlog"
Cohesion: 0.07
Nodes (26): 2026-04-28, 2026-04-29, 2026-04-30, 2026-05-06, 2026-05-07, 2026-05-08, 2026-05-13 WEB v1.0 expense AppData template/workspace fix88, 2026-05-13 WEB v1.0 fix77 ERP voucher server upload (+18 more)

### Community 49 - "voucher_builder.py"
Cohesion: 0.22
Nodes (25): VoucherLine, ManagerProfile, _bank_management_items(), _build_daeseung_cash_payload(), _build_generic_payload(), build_voucher_payload(), _cash_amount_source(), _clean_header() (+17 more)

### Community 50 - "parse_tax_invoice_xml"
Cohesion: 0.15
Nodes (7): SMILE EDI tax invoice crawler.  Approval is opt-in because SMILE EDI approval, WEHAGO (더존비즈온) 세금계산서 핸들러 대상: www.wehago.com/invoice/#/eTaxMail/... 메일 수신 업체: A, _format_biz_no(), _format_date(), parse_tax_invoice_xml(), 반환: (supplier_dict, buyer_dict, content_dict)     content_dict 안에 '항목' 리스트 포함., _text()

### Community 51 - "BaseTaxInvoiceHandler"
Cohesion: 0.11
Nodes (9): ABC, BaseTaxInvoiceHandler, Chrome, Path, 캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치., 세금계산서 포털별 핸들러 공통 베이스.     각 포털 핸들러는 이 클래스를 상속하고 supports() / _do_process() 를 구현, 이 핸들러가 처리 가능한 URL인지 반환., 통일 반환값:         {             "ok": bool,             "portal": str, (+1 more)

### Community 52 - "JobCreateRequest"
Cohesion: 0.32
Nodes (9): create_purchase_analyze_job(), InvoiceIdsRequest, JobCreateRequest, JobEventResponse, JobResponse, OutputSetRequest, PurchaseAnalysisUpdate, BaseModel (+1 more)

### Community 53 - "BaseModel"
Cohesion: 0.36
Nodes (16): BaseModel, AdminAgentCommandRequest, AdminResetJobsRequest, AgentAdminCommandCompleteRequest, AgentCompleteRequest, AgentEventRequest, AgentHeartbeat, BankTransfer (+8 more)

### Community 54 - "DEBUG.md"
Cohesion: 0.11
Nodes (16): 2026-06-25 Agent self-signed SSL 오류, 2026-06-25 Agent 접속 타임아웃, 2026-06-25 PowerShell 5.1 스크립트 인코딩, 2026-06-25 샘플 수시결제 파일 분석, 2026-06-25 초기 구현 메모, 2026-06-26 ERP 관리항목/메일 기준, 2026-06-26 기존 메일/DB 기본값 반영, 2026-06-26 담당자용 UI 정리 (+8 more)

### Community 57 - "HometaxHandler"
Cohesion: 0.26
Nodes (3): HometaxHandler, Path, WebDriver

### Community 69 - "fetch_finance_users"
Cohesion: 0.26
Nodes (15): make_temporary_password(), _active_value(), _allowed_dept_codes(), _company_key_for_dept(), _connect(), fetch_finance_users(), groupware_enabled(), GroupwareColumnMap (+7 more)

### Community 70 - "settings.py"
Cohesion: 0.17
Nodes (10): data_server_target_url(), forward_job_to_data_server(), Any, JobRecord, _voucher_for_data_server(), _env(), _env_bool(), _env_int() (+2 more)

### Community 71 - "SESSION STATE"
Cohesion: 0.17
Nodes (11): 2026-05-22 fix149 진행 상태, Current Work - 2026-05-22 fix151, fix152 / 1.0.140, fix153 / 1.0.141, Previous Work - 2026-05-22 fix150, SESSION STATE, 다음 작업, 방금 수정한 내용 (+3 more)

### Community 72 - "admin_db.js"
Cohesion: 0.36
Nodes (10): els, escapeHtml(), loadOverview(), loadTable(), renderRows(), renderTables(), requestJson(), shortCell() (+2 more)

### Community 73 - "test_voucher_builder.py"
Cohesion: 0.38
Nodes (9): Path, test_build_voucher_payload_adds_bank_credit_line(), test_build_voucher_payload_keeps_last_vendor_before_bank_line(), test_build_voucher_payload_uses_cash_sheet_rows_only(), test_daeseung_erp_credentials_use_payload_before_environment(), test_only_daeseung_manager_is_enabled_for_upload(), _write_cash_sheet_sample(), _write_many_cash_sheet_sample() (+1 more)

### Community 74 - "Graph Report - 세금계산서 크롤링  (2026-04-30)"
Cohesion: 0.22
Nodes (8): Community Hubs (Navigation), Corpus Check, God Nodes (most connected - your core abstractions), Graph Report - 세금계산서 크롤링  (2026-04-30), Knowledge Gaps, Suggested Questions, Summary, Surprising Connections (you probably didn't know these)

### Community 75 - "Handover"
Cohesion: 0.22
Nodes (8): Authentication Notes, Current Status, Final Source Files, Handover, Important Current Gaps, PDF Filename Rule, Samples In This Folder, SmartBill WEB v1.0 Print Note

### Community 76 - "Feature Ledger"
Cohesion: 0.22
Nodes (8): Current Portal Test Inputs, Feature Ledger, Graphify Code Map, KT Password Rules, Mail Target Routing, PDF Filename Rule, Project Memory Lite, Tax Invoice Crawling Core

### Community 77 - "worker.py"
Cohesion: 0.44
Nodes (7): _fmt_amount(), _invoice_data(), _invoice_summary_line(), notify_regular_auto_result(), Any, _regular_auto_sender(), _send_mail()

### Community 78 - "Excel Voucher Web"
Cohesion: 0.25
Nodes (7): Agent 실행 예시, Excel Voucher Web, 데이터 서버 전달, 로그인/그룹웨어 DB 연동, 실행, 작업 내역 초기화, 접속 확인

### Community 79 - "운영서버 복붙 명령"
Cohesion: 0.25
Nodes (7): 1. ZIP 풀기, 2. 설치, 3. 실행, 4. 점검, 5. 인증서 등록, 6. 구매 메일 수집, 운영서버 복붙 명령

### Community 81 - "Project State"
Cohesion: 0.29
Nodes (6): Current Notes, Main Entry Points, Portal Handlers, Project State, Purpose, Verification Habit

### Community 82 - "DECISIONS.md"
Cohesion: 0.29
Nodes (5): ERP 관리항목 규칙, 대승 수시결제 엑셀 형식, 새 시스템 배치, 적요 규칙, 확정 설계

### Community 83 - "SESSION.md"
Cohesion: 0.29
Nodes (5): 계정/메일 방향, 기본 흐름, 신규 목표, 운영 원칙, 이번 세션 구현 범위

### Community 84 - "Decisions"
Cohesion: 0.29
Nodes (6): 2026-04-28 - Backup Before Code Edits, 2026-04-28 - Exclude U+, 2026-04-28 - KT W00127 Manual Handling, 2026-04-28 - Use Graphify For Structure, Not Product Memory, 2026-04-28 - Use Project-Local Memory, Decisions

### Community 85 - "WEB v1.0 Operating Server Deploy"
Cohesion: 0.29
Nodes (6): 0. 프로젝트 ZIP 풀기, 1. 설치, 2. 실행, 3. 점검, WEB v1.0 Operating Server Deploy, 참고

### Community 86 - "TODO.md"
Cohesion: 0.33
Nodes (4): 담당자별 설정, 엑셀 업로드 전표 처리, 완료 메일, 전표 작성 규칙

### Community 87 - "회계업무 자동화 WEB v1.0"
Cohesion: 0.33
Nodes (5): WEB v1.0 방향, 제외한 것, 폴더 구성, 현재 개발 기준, 회계업무 자동화 WEB v1.0

### Community 88 - "_build_user_pc_payload_zip"
Cohesion: 0.47
Nodes (6): _add_installer_file(), _add_installer_tree(), _agent_installer_script(), _agent_self_contained_cmd(), _build_user_pc_payload_zip(), ZipFile

### Community 89 - "api_admin_db_overview"
Cohesion: 0.53
Nodes (6): _admin_db_conn(), _admin_table_names(), api_admin_db_overview(), api_admin_db_table(), Connection, _quote_identifier()

### Community 90 - "approval_fetcher.py"
Cohesion: 0.50
Nodes (4): _check_playwright_runtime(), fetch_approval_documents(), Any, Progress

### Community 91 - "AGENTS.md"
Cohesion: 0.50
Nodes (3): Git / release hygiene, graphify, Project Memory Lite

### Community 92 - "main"
Cohesion: 0.83
Nodes (3): first(), fmt(), main()

### Community 94 - "api_unhandled_exception_handler"
Cohesion: 0.67
Nodes (3): JSONResponse, api_unhandled_exception_handler(), Exception

## Knowledge Gaps
- **378 isolated node(s):** `state`, `statusText`, `statusMessage`, `state`, `els` (+373 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **47 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `list_invoices()` connect `invoice_db.py` to `regular_due_monitor.py`, `app.py`, `.get`, `app.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `BaseTaxInvoiceHandler` connect `BaseTaxInvoiceHandler` to `XmlAttachmentHandler`, `SmartBillHandler`, `WehagoHandler`, `._do_process`, `parse_tax_invoice_xml`, `SmileEdiHandler`, `HometaxHandler`, `KtAttachmentHandler`, `AutoEverHandler`, `CsbillHandler`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `run_invoice_erp_input()` connect `erp_runner.py` to `JobStore`, `전표 자동화 프로그램(담당자용)_v6.2.py`, `.get`, `worker.py`, `RuntimeError`, `erp_agent.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 63 inferred relationships involving `RuntimeError` (e.g. with `_execute_admin_command()` and `_install_agent_task()`) actually correct?**
  _`RuntimeError` has 63 INFERRED edges - model-reasoned connections that need verification._
- **What connects `state`, `statusText`, `statusMessage` to the rest of the system?**
  _378 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `JobStore` be split into smaller, more focused modules?**
  _Cohesion score 0.09877551020408164 - nodes in this community are weakly interconnected._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1038961038961039 - nodes in this community are weakly interconnected._