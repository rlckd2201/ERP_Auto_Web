# Graph Report - erp_auto_web_release_1c2c9c5  (2026-07-20)

## Corpus Check
- 111 files · ~181,332 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2420 nodes · 6968 edges · 109 communities (93 shown, 16 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 1001 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8d4c8502`
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
- worker.py
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
- .copy_erp
- parse_tax_invoice_xml
- setup_state.py
- collect_mail_once
- AI Work Memory
- KtAttachmentHandler
- AutoEverHandler
- CsbillHandler
- XmlAttachmentHandler
- __init__.py
- main
- __init__.py
- Accounting automation WEB v1 package.
- parse_tax_invoice_xml
- install_operating_server.ps1
- AccountStore
- notifications.py
- test_auth_defaults.py
- invoice_db.py
- WehagoHandler
- JobStore
- test_manager_vendor_search.py
- Devlog
- parse_tax_invoice_xml
- BaseTaxInvoiceHandler
- JobCreateRequest
- BaseModel
- DEBUG.md
- run_backend.ps1
- check_operating_server.ps1
- HometaxHandler
- enable_http_notification_policy.ps1
- start_operating_server.ps1
- trust_https_cert_current_user.ps1
- biz_groups.py
- run_backend.ps1
- check_operating_server.ps1
- enable_http_notification_policy.ps1
- install_operating_server.ps1
- start_operating_server.ps1
- trust_https_cert_current_user.ps1
- sw.js
- fetch_finance_users
- settings.py
- SESSION STATE
- admin_db.js
- .log
- Graph Report - 세금계산서 크롤링  (2026-04-30)
- Handover
- Feature Ledger
- worker.py
- Excel Voucher Web
- 운영서버 복붙 명령
- AILearningViewer
- Project State
- SESSION.md
- WEB v1.0 Operating Server Deploy
- TODO.md
- _build_user_pc_payload_zip
- Program
- AGENTS.md
- User Feedback
- install_operating_server.ps1
- start_user_erp_agent.ps1
- regular_due_history_page

## God Nodes (most connected - your core abstractions)
1. `Communities` - 101 edges
2. `ERPAutoApp` - 87 edges
3. `SmileEdiHandler` - 65 edges
4. `Project Status` - 53 edges
5. `BaseTaxInvoiceHandler` - 51 edges
6. `CODEBASE WIKI` - 51 edges
7. `get_invoice()` - 50 edges
8. `AI Work Memory` - 46 edges
9. `_load_nested_functions()` - 38 edges
10. `WehagoHandler` - 37 edges

## Surprising Connections (you probably didn't know these)
- `_run_real_erp_voucher_task()` --calls--> `ERPLoginBot`  [INFERRED]
  excel_voucher_web/app/agent_adapter.py → manager_server/전표 자동화 프로그램(담당자용)_v6.2.py
- `ERPLoginBot` --calls--> `run_invoice_erp_input()`  [INFERRED]
  manager_server/전표 자동화 프로그램(담당자용)_v6.2.py → web_v1/backend/erp_runner.py
- `api_upload_voucher()` --calls--> `create_job()`  [INFERRED]
  excel_voucher_web/app/main.py → web_v1/backend/app.py
- `api_jobs()` --calls--> `list_jobs()`  [INFERRED]
  excel_voucher_web/app/main.py → web_v1/backend/app.py
- `test_agent_admin_command_lifecycle()` --calls--> `JobStore`  [INFERRED]
  excel_voucher_web/tests/test_admin_commands.py → web_v1/backend/job_store.py

## Import Cycles
- None detected.

## Communities (109 total, 16 thin omitted)

### Community 0 - "JobStore"
Cohesion: 0.06
Nodes (82): HTMLResponse, JSONResponse, StreamingResponse, _add_installer_file(), _add_installer_tree(), _admin_db_conn(), admin_db_page(), _admin_table_names() (+74 more)

### Community 1 - "main.py"
Cohesion: 0.09
Nodes (59): make_temporary_password(), Any, groupware_enabled(), _agent_payload(), api_admin_agent_commands(), api_admin_create_agent_command(), api_admin_reset_jobs(), api_admin_server_update() (+51 more)

### Community 2 - "config.py"
Cohesion: 0.08
Nodes (33): action, applyDetailMode(), bootstrap(), button, checkbox, clearLoginAndShowLogin(), dept, docCard (+25 more)

### Community 4 - "app.py"
Cohesion: 0.07
Nodes (22): _site_name_from_biz_no(), _clean_html_cell(), _clean_text(), _date_after(), _element_label(), _field_after(), _font_rows(), _format_biz_no() (+14 more)

### Community 5 - ".process"
Cohesion: 0.09
Nodes (70): build_purchase_erp_payload(), build_regular_erp_payload(), _clean_text(), _configure_pyautogui_for_server(), _corp_codes(), _extract_invoice_date(), _extract_invoice_date_from_text(), _extract_pdf_text_for_date() (+62 more)

### Community 6 - "SmartBillHandler"
Cohesion: 0.07
Nodes (48): IMAP4_SSL, LogRecord, ProgressCallback, AutoEverHandler(), crawl_invoice(), _csbill_link_bill_no(), _csbill_link_priority(), CsbillHandler() (+40 more)

### Community 7 - "전표 자동화 프로그램(담당자용)_v6.2.py"
Cohesion: 0.02
Nodes (101): Communities, Community 0 - "Community 0", Community 100 - "Community 100", Community 101 - "Community 101", Community 102 - "Community 102", Community 103 - "Community 103", Community 104 - "Community 104", Community 10 - "Community 10" (+93 more)

### Community 8 - "app.js"
Cohesion: 0.32
Nodes (11): button, els, escapeHtml(), loadOverview(), loadTable(), renderRows(), renderTables(), requestJson() (+3 more)

### Community 9 - "Communities"
Cohesion: 0.08
Nodes (51): CompletedProcess, _acquire_single_instance(), _agent_bundle_hash(), _agent_update_required(), AgentTray, _apply_server_setup_config(), _cert_cache_path(), _cert_store_has_thumbprint() (+43 more)

### Community 10 - "app.py"
Cohesion: 0.04
Nodes (50): 2026-05-18 fix123 selective output documents, 2026-05-18 fix124 KT vendor business-number row selection, 2026-05-18 fix125 KT vendor business-number popup search, 2026-05-18 fix126 KT vendor keyboard sequence, 2026-05-18 fix126 KT vendor search input, 2026-05-18 fix127 KT vendor final double-enter, 2026-05-18 fix128 setup installer reuse, 2026-05-18 fix129 Chrome notifications (+42 more)

### Community 11 - ".get"
Cohesion: 0.15
Nodes (44): appendErpCredentials(), applyAuthUi(), askErpCredentials(), badge(), canUseApp(), changePassword(), commandStatus(), commandTitle() (+36 more)

### Community 12 - "worker.py"
Cohesion: 0.13
Nodes (58): api_regular_due_check(), _add_months(), _alert_hour(), _alert_start_date(), _amount(), build_regular_due_report(), _clean_text(), _compact() (+50 more)

### Community 13 - "app.js"
Cohesion: 0.07
Nodes (19): CsbillHandler, _parse_amount(), _parse_field(), _parse_item_name(), Path, WebDriver, _write_text(), LG U+ eDocu tax invoice portal adapter.  This adapter intentionally routes edo (+11 more)

### Community 14 - "agent_adapter.py"
Cohesion: 0.04
Nodes (51): 2026-05-22 Log Display Notes, 2026-05-22 Regular Auto-Agent Notes, 2026-05-22 Vendor Business Number Notes, Agent Architecture, CODEBASE WIKI, Common Pitfalls, Configuration, Current Handoff (+43 more)

### Community 15 - "RuntimeError"
Cohesion: 0.08
Nodes (68): index(), _FakeControl, _FakeLogger, _FakeRect, _fast_visible_voucher_snapshot(), _load_nested_functions(), _load_runtime_navigation(), Menu startup must not depend on a helper local to _setup_slip_form. (+60 more)

### Community 16 - "._do_process"
Cohesion: 0.22
Nodes (25): VoucherLine, ManagerProfile, _bank_management_items(), _build_daeseung_cash_payload(), _build_generic_payload(), build_voucher_payload(), _cash_amount_source(), _clean_header() (+17 more)

### Community 17 - "erp_agent.py"
Cohesion: 0.12
Nodes (45): STAThread, string, api_agent_heartbeat(), _active_install_job(), _add_check(), _age_seconds(), authenticate_user(), change_initial_password() (+37 more)

### Community 18 - "regular_due_monitor.py"
Cohesion: 0.04
Nodes (46): 2026-04-30 SmartBill PDF text fallback parse, 2026-04-30 SmartBill/WEHAGO crawler fix, 2026-04-30 SmartBill/WEHAGO hardening after repeat failure, 2026-04-30 TAB1 XML / 결의서 혼합 계정 버그 수정, 2026-04-30 WEHAGO PDF 저장 다이얼로그 '새 폴더' 생성 및 오작동 완벽 수정, 2026-04-30 WEHAGO PDF 저장 다이얼로그 '새 폴더' 클릭 오작동 수정, 2026-04-30 WEHAGO Save As new-folder guard, 2026-04-30 WEHAGO Save As overwrite guard refinement (+38 more)

### Community 19 - "erp_runner.py"
Cohesion: 0.18
Nodes (41): EmailMessage, _add_attachment(), _attachment_paths(), completion_mail_body(), completion_mail_html(), _details_table(), _diagnostic_attachment(), _display_address() (+33 more)

### Community 20 - "SmileEdiHandler"
Cohesion: 0.06
Nodes (31): 2026-06-25 Agent self-signed SSL 오류, 2026-06-25 Agent 접속 타임아웃, 2026-06-25 PowerShell 5.1 스크립트 인코딩, 2026-06-25 샘플 수시결제 파일 분석, 2026-06-25 초기 구현 메모, 2026-06-26 ERP 관리항목/메일 기준, 2026-06-26 기존 메일/DB 기본값 반영, 2026-06-26 담당자용 UI 정리 (+23 more)

### Community 21 - "UplusEdocuHandler"
Cohesion: 0.07
Nodes (26): 2026-04-28, 2026-04-29, 2026-04-30, 2026-05-06, 2026-05-07, 2026-05-08, 2026-05-13 WEB v1.0 expense AppData template/workspace fix88, 2026-05-13 WEB v1.0 fix77 ERP voucher server upload (+18 more)

### Community 22 - "CODEBASE WIKI"
Cohesion: 0.06
Nodes (18): Service, EtaxUnipostHandler, format_biz_no(), format_date_yyyymmdd(), Chrome, safe_filename(), split_classification(), text_or_none() (+10 more)

### Community 23 - "Project Status"
Cohesion: 0.14
Nodes (8): AutoEverHandler, _clean_password_candidate(), _normalize_cell(), Path, _table_cells(), _to_int(), _valid_password_candidate(), _write_text()

### Community 24 - ".copy_erp"
Cohesion: 0.15
Nodes (5): _digits_only(), Path, LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler

### Community 26 - "setup_state.py"
Cohesion: 0.17
Nodes (11): 2026-05-22 fix149 진행 상태, Current Work - 2026-05-22 fix151, fix152 / 1.0.140, fix153 / 1.0.141, Previous Work - 2026-05-22 fix150, SESSION STATE, 다음 작업, 방금 수정한 내용 (+3 more)

### Community 27 - "collect_mail_once"
Cohesion: 0.48
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 28 - "AI Work Memory"
Cohesion: 0.22
Nodes (8): Authentication Notes, Current Status, Final Source Files, Handover, Important Current Gaps, PDF Filename Rule, Samples In This Folder, SmartBill WEB v1.0 Print Note

### Community 29 - "KtAttachmentHandler"
Cohesion: 0.22
Nodes (8): Current Portal Test Inputs, Feature Ledger, Graphify Code Map, KT Password Rules, Mail Target Routing, PDF Filename Rule, Project Memory Lite, Tax Invoice Crawling Core

### Community 30 - "AutoEverHandler"
Cohesion: 0.25
Nodes (7): Agent 실행 예시, Excel Voucher Web, 데이터 서버 전달, 로그인/그룹웨어 DB 연동, 실행, 작업 내역 초기화, 접속 확인

### Community 31 - "CsbillHandler"
Cohesion: 0.25
Nodes (7): 1. ZIP 풀기, 2. 설치, 3. 실행, 4. 점검, 5. 인증서 등록, 6. 구매 메일 수집, 운영서버 복붙 명령

### Community 32 - "XmlAttachmentHandler"
Cohesion: 0.29
Nodes (6): Current Notes, Main Entry Points, Portal Handlers, Project State, Purpose, Verification Habit

### Community 33 - "__init__.py"
Cohesion: 0.29
Nodes (5): ERP 관리항목 규칙, 대승 수시결제 엑셀 형식, 새 시스템 배치, 적요 규칙, 확정 설계

### Community 34 - "main"
Cohesion: 0.29
Nodes (5): 계정/메일 방향, 기본 흐름, 신규 목표, 운영 원칙, 이번 세션 구현 범위

### Community 35 - "__init__.py"
Cohesion: 0.29
Nodes (6): 2026-04-28 - Backup Before Code Edits, 2026-04-28 - Exclude U+, 2026-04-28 - KT W00127 Manual Handling, 2026-04-28 - Use Graphify For Structure, Not Product Memory, 2026-04-28 - Use Project-Local Memory, Decisions

### Community 36 - "Accounting automation WEB v1 package."
Cohesion: 0.29
Nodes (6): 0. 프로젝트 ZIP 풀기, 1. 설치, 2. 실행, 3. 점검, WEB v1.0 Operating Server Deploy, 참고

### Community 37 - "parse_tax_invoice_xml"
Cohesion: 0.33
Nodes (5): WEB v1.0 방향, 제외한 것, 폴더 구성, 현재 개발 기준, 회계업무 자동화 WEB v1.0

### Community 38 - "install_operating_server.ps1"
Cohesion: 0.33
Nodes (4): 담당자별 설정, 엑셀 업로드 전표 처리, 완료 메일, 전표 작성 규칙

### Community 40 - "notifications.py"
Cohesion: 0.20
Nodes (29): _apply_company_erp_credentials(), _archive_pdf(), _clean_management_items(), _clipboard_account_name(), _clipboard_vendor_value(), _fallback_bank_management_items(), _fallback_line_management_items(), _file_uri() (+21 more)

### Community 42 - "invoice_db.py"
Cohesion: 0.50
Nodes (3): Git / release hygiene, graphify, Project Memory Lite

### Community 46 - "test_manager_vendor_search.py"
Cohesion: 0.15
Nodes (10): BaseTaxInvoiceHandler, _file_uri_to_path(), _font(), _guess_account(), _line(), _money(), _normalize_mail_date(), Path (+2 more)

### Community 50 - "parse_tax_invoice_xml"
Cohesion: 0.09
Nodes (60): _active_value(), _allowed_dept_codes(), _company_key_for_dept(), _connect(), fetch_finance_users(), GroupwareColumnMap, inspect_columns(), _mail_from_user_id() (+52 more)

### Community 51 - "BaseTaxInvoiceHandler"
Cohesion: 0.24
Nodes (29): add_invoice_log(), _clean_int(), _columns(), delete_invoice(), detect_invoice_type(), _ensure_column(), get_conn(), get_invoice_by_pdf_path() (+21 more)

### Community 52 - "JobCreateRequest"
Cohesion: 0.11
Nodes (13): _customer_name_from_lines(), _extract_kt_statement_date(), _file_uri_to_path(), _find_sequence(), _fitz(), KtAttachmentHandler, _normalize_issue(), _normalize_mail_date() (+5 more)

### Community 54 - "DEBUG.md"
Cohesion: 0.15
Nodes (19): AccountStore, AccountUser, hash_password(), now_text(), protect_secret(), Connection, Path, Row (+11 more)

### Community 55 - "run_backend.ps1"
Cohesion: 0.40
Nodes (8): build_pdf_filename(), clean_token(), dedupe_path(), parse_pdf(), repair_db_rows(), safe_name(), site_from_biz_no(), to_int()

### Community 56 - "check_operating_server.ps1"
Cohesion: 0.18
Nodes (10): Logger, _detect_erp_target_monitor(), _ErpGuiAutomationLock, ERPLoginBot, _monitor_summary(), _move_window_to_erp_monitor(), 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence), _set_process_dpi_aware_for_erp_windowing() (+2 more)

### Community 57 - "HometaxHandler"
Cohesion: 0.36
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 58 - "enable_http_notification_policy.ps1"
Cohesion: 0.16
Nodes (18): api_agent_admin_next(), api_agent_heartbeat(), api_agent_next(), _client_ip(), AgentHeartbeat, JobStore, _json_dumps(), _json_loads() (+10 more)

### Community 59 - "start_operating_server.ps1"
Cohesion: 0.09
Nodes (14): ABC, _add_months(), BaseTaxInvoiceHandler, _do_process(), _get_chromedriver_service(), _period_rule_key(), Chrome, Path (+6 more)

### Community 60 - "trust_https_cert_current_user.ps1"
Cohesion: 0.16
Nodes (32): create_demo_job(), create_job(), create_output_set_job(), create_purchase_analyze_job(), create_purchase_erp_input_job(), create_purchase_mail_collect_job(), create_purchase_one_click_job(), create_regular_erp_input_job() (+24 more)

### Community 61 - "biz_groups.py"
Cohesion: 0.08
Nodes (14): _is_stable(), _candidates_from_url(), _parse_amount(), _parse_field(), _paste_text(), Path, WEHAGO (더존비즈온) 세금계산서 핸들러 대상: www.wehago.com/invoice/#/eTaxMail/... 메일 수신 업체: A, WEHAGO URL의 Base64 토큰에서 사업자번호(10자리) 추출.         예: .../eTaxMail/VFgyMDI2MDQ2OTQ (+6 more)

### Community 62 - "run_backend.ps1"
Cohesion: 0.17
Nodes (35): api_agent_job_complete(), api_agent_job_expense_report_upload(), api_agent_job_voucher_upload(), api_analyze_purchase(), api_create_manual_purchase_invoice(), api_generate_expense_report(), api_get_invoice_output_set(), api_retry_invoice() (+27 more)

### Community 63 - "check_operating_server.ps1"
Cohesion: 0.13
Nodes (9): 메일 본문에서 법인 키워드를 찾아 사업자번호 후보 dict 반환., _build_data(), _build_subject(), 유니포스트 etax 세금계산서 핸들러 대상: etax.unipost.co.kr, UnipostHandler, _format_date(), parse_tax_invoice_xml(), 반환: (supplier_dict, buyer_dict, content_dict)     content_dict 안에 '항목' 리스트 포함. (+1 more)

### Community 64 - "enable_http_notification_policy.ps1"
Cohesion: 0.18
Nodes (10): JobStore, on_startup(), _start_mail_collect_scheduler(), _start_regular_auto_scheduler(), Any, JobStatus, start_regular_due_scheduler(), JobWorker (+2 more)

### Community 65 - "install_operating_server.ps1"
Cohesion: 0.14
Nodes (24): collectRegularForm(), currentOutputTarget(), els, ensureJobNotificationPermission(), guessRegularAccount(), isLocalhost(), mappedDefaultOutputTarget(), notificationNeedsHttps() (+16 more)

### Community 66 - "start_operating_server.ps1"
Cohesion: 0.24
Nodes (22): _connection_error_message(), _download_job_source(), _execute_admin_command(), _heartbeat(), _install_agent_task(), _latest_agent_log(), main(), _normalize_printer_name() (+14 more)

### Community 67 - "trust_https_cert_current_user.ps1"
Cohesion: 0.27
Nodes (11): _check_playwright_runtime(), fetch_approval_documents(), Any, Progress, _fmt_amount(), _invoice_data(), _invoice_summary_line(), notify_regular_auto_result() (+3 more)

### Community 68 - "sw.js"
Cohesion: 0.17
Nodes (22): agentConnectedFromSetup(), agentUpdateRequiredFromSetup(), autoStartAgentAfterLogin(), certificateMissingFromSetup(), checkClass(), continueAfterLogin(), downloadUserPcInstaller(), handleInitialPasswordChange() (+14 more)

### Community 69 - "fetch_finance_users"
Cohesion: 0.21
Nodes (4): HometaxHandler, Path, WebDriver, _write_text()

### Community 70 - "settings.py"
Cohesion: 0.29
Nodes (17): _active_invoice_items(), claim_next_erp_task(), now_text(), Any, Path, _read_task(), _task_files(), update_erp_task() (+9 more)

### Community 71 - "SESSION STATE"
Cohesion: 0.15
Nodes (11): _is_better_parse(), SmartBill print flow based on the actual HTML fnPrint() logic.      The print, SmartBill: open preview URL, scroll to the bottom, click the actual bottom print, SmartBill preview print flow using the confirmed ibtnPrint element., SmartBill print flow fixed to the confirmed fnPrint/prt_prev.aspx path., Click the real SmartBill print button on the current invoice page.      SmartB, _smartbill_bottom_print_save_pdf(), _smartbill_current_ibtn_window_save_pdf() (+3 more)

### Community 72 - "admin_db.js"
Cohesion: 0.15
Nodes (9): digits_only(), _clean_token(), Path, 화면을 가리는 광고(크레포트 등)를 닫습니다., 수신미승인 상태면 승인 처리를 진행하고,         최종적으로 '인쇄' 버튼이 렌더링되었는지 확인합니다., 스마트빌 화면에서 공급자/공급받는자/사업자번호/금액을 추출합니다., 인쇄 버튼을 누른 후, 새 창으로 뜨는 인쇄 미리보기 페이지에서         크롬 네이티브 인쇄 다이얼로그를 우회하여 driver.print, SmartBillHandler (+1 more)

### Community 73 - ".log"
Cohesion: 0.17
Nodes (17): accountOptions(), approvalPaths(), approvalStatusText(), canRunErp(), clearApprovalPoll(), collectAnalysisForm(), compactApprovalError(), detailData() (+9 more)

### Community 74 - "Graph Report - 세금계산서 크롤링  (2026-04-30)"
Cohesion: 0.26
Nodes (16): addLog(), connectEvents(), finishJob(), loadJobLog(), renderJobLogs(), schedulePostJobRefresh(), setBadge(), setBusy() (+8 more)

### Community 75 - "Handover"
Cohesion: 0.21
Nodes (13): canRetryInvoice(), displayProcessor(), filteredInvoices(), formatMoney(), loadSelectedPurchaseDetail(), matchesStatusFilter(), renderInvoices(), selectedInvoicesCanRetry() (+5 more)

### Community 76 - "Feature Ledger"
Cohesion: 0.13
Nodes (40): auto_attach_compuzone_quote(), _clean_order_no(), _click_print_button(), _close_context(), _compuzone_accounts(), CompuzoneQuoteError, _emit(), fetch_compuzone_quote_pdf() (+32 more)

### Community 77 - "worker.py"
Cohesion: 0.31
Nodes (13): createManualPurchaseInvoice(), deleteSelectedInvoices(), generateExpenseReport(), loadInvoiceLogs(), loadOutputSet(), loadSelectedInvoiceLogs(), refreshInvoices(), requestForm() (+5 more)

### Community 79 - "운영서버 복붙 명령"
Cohesion: 0.27
Nodes (5): _env(), _env_bool(), _env_int(), Path, Settings

### Community 80 - "AILearningViewer"
Cohesion: 0.25
Nodes (20): BaseModel, data_server_target_url(), forward_job_to_data_server(), Any, JobRecord, _voucher_for_data_server(), AdminAgentCommandRequest, AdminResetJobsRequest (+12 more)

### Community 81 - "Project State"
Cohesion: 0.22
Nodes (8): Community Hubs (Navigation), Corpus Check, God Nodes (most connected - your core abstractions), Graph Report - 세금계산서 크롤링  (2026-04-30), Knowledge Gaps, Suggested Questions, Summary, Surprising Connections (you probably didn't know these)

### Community 83 - "SESSION.md"
Cohesion: 0.25
Nodes (8): escapeHtml(), isFailureLog(), logClass(), renderJobEventLine(), renderJobTableGroup(), renderLogGroup(), renderPrinterMapping(), splitRecentLogs()

### Community 85 - "WEB v1.0 Operating Server Deploy"
Cohesion: 0.38
Nodes (9): Path, test_build_voucher_payload_adds_bank_credit_line(), test_build_voucher_payload_keeps_last_vendor_before_bank_line(), test_build_voucher_payload_uses_cash_sheet_rows_only(), test_daeseung_erp_credentials_use_payload_before_environment(), test_only_daeseung_manager_is_enabled_for_upload(), _write_cash_sheet_sample(), _write_many_cash_sheet_sample() (+1 more)

### Community 88 - "_build_user_pc_payload_zip"
Cohesion: 0.33
Nodes (6): applyModeUi(), formatTime(), loadHealth(), loadMailCollectStatus(), showApp(), startMailCollectMonitor()

## Knowledge Gaps
- **410 isolated node(s):** `주의사항`, `2026-06-25 초기 구현 메모`, `2026-06-25 샘플 수시결제 파일 분석`, `2026-06-25 Agent 접속 타임아웃`, `2026-06-25 PowerShell 5.1 스크립트 인코딩` (+405 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SmileEdiHandler` connect `app.py` to `start_operating_server.ps1`, `test_manager_vendor_search.py`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `BaseTaxInvoiceHandler` connect `start_operating_server.ps1` to `app.py`, `fetch_finance_users`, `SESSION STATE`, `admin_db.js`, `app.js`, `test_manager_vendor_search.py`, `JobCreateRequest`, `CODEBASE WIKI`, `Project Status`, `biz_groups.py`, `check_operating_server.ps1`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `UplusEdocuHandler` connect `.copy_erp` to `biz_groups.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Are the 54 inferred relationships involving `RuntimeError` (e.g. with `_execute_admin_command()` and `_install_agent_task()`) actually correct?**
  _`RuntimeError` has 54 INFERRED edges - model-reasoned connections that need verification._
- **What connects `주의사항`, `2026-06-25 초기 구현 메모`, `2026-06-25 샘플 수시결제 파일 분석` to the rest of the system?**
  _410 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `JobStore` be split into smaller, more focused modules?**
  _Cohesion score 0.060240963855421686 - nodes in this community are weakly interconnected._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09011776753712238 - nodes in this community are weakly interconnected._