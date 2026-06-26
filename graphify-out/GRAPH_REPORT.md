# Graph Report - (재정)회계업무 자동화_WEB_Version  (2026-06-26)

## Corpus Check
- 1936 files · ~3,501,005 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4725 nodes · 37006 edges · 61 communities detected
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 3027 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 281|Community 281]]
- [[_COMMUNITY_Community 282|Community 282]]
- [[_COMMUNITY_Community 283|Community 283]]
- [[_COMMUNITY_Community 284|Community 284]]
- [[_COMMUNITY_Community 285|Community 285]]
- [[_COMMUNITY_Community 286|Community 286]]
- [[_COMMUNITY_Community 287|Community 287]]
- [[_COMMUNITY_Community 288|Community 288]]
- [[_COMMUNITY_Community 289|Community 289]]
- [[_COMMUNITY_Community 290|Community 290]]
- [[_COMMUNITY_Community 291|Community 291]]
- [[_COMMUNITY_Community 292|Community 292]]
- [[_COMMUNITY_Community 293|Community 293]]
- [[_COMMUNITY_Community 294|Community 294]]
- [[_COMMUNITY_Community 295|Community 295]]
- [[_COMMUNITY_Community 296|Community 296]]

## God Nodes (most connected - your core abstractions)
1. `get_invoice()` - 244 edges
2. `build_output_set_status()` - 182 edges
3. `update_invoice_json()` - 161 edges
4. `JobCreateRequest` - 136 edges
5. `sleep()` - 134 edges
6. `add_invoice_log()` - 131 edges
7. `ERPAutoApp` - 92 edges
8. `safe_filename()` - 84 edges
9. `UplusEdocuHandler` - 82 edges
10. `EtaxUnipostHandler` - 79 edges

## Surprising Connections (you probably didn't know these)
- `api_jobs()` --calls--> `list_jobs()`  [INFERRED]
  excel_voucher_web\app\main.py → C:\Users\user\Desktop\개발파일\회계업무 자동화_WEB_Version\_release_fix9_stage\web_v1\backend\app.py
- `api_job_voucher()` --calls--> `get_job()`  [INFERRED]
  excel_voucher_web\app\main.py → C:\Users\user\Desktop\개발파일\회계업무 자동화_WEB_Version\_release_fix9_stage\web_v1\backend\app.py
- `_queue_expense_report_after_erp()` --calls--> `write_expense_report_queue()`  [INFERRED]
  _codex_app_probe.py → _codex_stage_zoom_billing_manual_amount_fix184_20260617_154500\web_v1\backend\erp_queue.py
- `_output_print_task()` --calls--> `queue_dir()`  [INFERRED]
  _codex_app_probe.py → C:\Users\user\Desktop\개발파일\회계업무 자동화_WEB_Version\_release_fix9_stage\web_v1\backend\erp_queue.py
- `_regular_auto_target_profile()` --calls--> `latest_agent_profile()`  [INFERRED]
  _codex_app_probe.py → _codex_stage_zoom_billing_manual_amount_fix184_20260617_154500\web_v1\backend\setup_state.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (780): add_invoice_log(), _clean_int(), _columns(), delete_invoice(), detect_invoice_type(), _ensure_column(), get_conn(), get_invoice() (+772 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (72): _active_invoice_items(), claim_next_erp_task(), now_text(), _read_task(), _task_files(), update_erp_task(), _write_task(), _app_version() (+64 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (85): ABC, _connection_error_message(), _heartbeat(), main(), _post(), run_loop(), Placeholder for the real ERP UI automation run on the 담당자 PC Agent., _render_print_html() (+77 more)

### Community 3 - "Community 3"
Cohesion: 0.38
Nodes (124): _add_installer_file(), _add_installer_tree(), _admin_db_conn(), admin_db_page(), _admin_table_names(), _agent_bootstrap_script(), _agent_cmd_launcher(), _agent_exe_launcher() (+116 more)

### Community 4 - "Community 4"
Cohesion: 0.22
Nodes (136): accountOptions(), addLog(), agentConnectedFromSetup(), agentUpdateRequiredFromSetup(), applyDetailMode(), applyModeUi(), approvalPaths(), approvalStatusText() (+128 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (19): UplusEDocuHandler, _digits_only(), LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler, _format_biz_no(), _format_date(), parse_tax_invoice_xml() (+11 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (26): escapeHtml(), loadOverview(), loadTable(), renderRows(), renderTables(), requestJson(), shortCell(), showError() (+18 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (101): AccountStore, AccountUser, hash_password(), make_temporary_password(), now_text(), verify_password(), data_server_target_url(), forward_job_to_data_server() (+93 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (121): addLog(), agentConnectedFromSetup(), agentUpdateRequiredFromSetup(), applyDetailMode(), applyModeUi(), approvalPaths(), approvalStatusText(), autoStartAgentAfterLogin() (+113 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (121): addLog(), agentConnectedFromSetup(), agentUpdateRequiredFromSetup(), applyDetailMode(), applyModeUi(), approvalPaths(), approvalStatusText(), autoStartAgentAfterLogin() (+113 more)

### Community 10 - "Community 10"
Cohesion: 0.31
Nodes (93): _add_months(), _alert_hour(), _alert_start_date(), _alias_matches_text(), _amount(), build_regular_due_report(), _clean_text(), _compact() (+85 more)

### Community 11 - "Community 11"
Cohesion: 0.19
Nodes (55): _check_playwright_runtime(), fetch_approval_documents(), _ai_parse(), analyze_purchase_documents(), _clean_match_text(), _clean_text(), _collapse_duplicate_total_prices(), _collapse_repeated_words() (+47 more)

### Community 12 - "Community 12"
Cohesion: 0.21
Nodes (49): _active_install_job(), _add_check(), _age_seconds(), authenticate_user(), change_initial_password(), claim_install_job(), _columns(), complete_install_job() (+41 more)

### Community 13 - "Community 13"
Cohesion: 0.1
Nodes (29): applyAuthUi(), badge(), canUseApp(), changePassword(), escapeHtml(), fetchJson(), forgotPassword(), jobTitle() (+21 more)

### Community 14 - "Community 14"
Cohesion: 0.48
Nodes (53): _aggregate_expense_items(), _appdata_template_candidates(), _build_expense_report_text(), _build_zoom_expense_report_text(), _clean_expense_item_name(), _clean_path(), _copy_or_merge_doc(), _docs_for_output() (+45 more)

### Community 15 - "Community 15"
Cohesion: 0.34
Nodes (51): _acquire_single_instance(), _agent_bundle_hash(), _agent_update_required(), AgentTray, _apply_server_setup_config(), _browser_pdf_print_app_candidates(), _cert_cache_path(), _cert_store_has_thumbprint() (+43 more)

### Community 16 - "Community 16"
Cohesion: 0.08
Nodes (14): portal_name(), LG U+ eDocu tax invoice portal adapter.  This adapter intentionally routes edo, UplusPortalHandler, main(), print_result(), 세금계산서 크롤링 모듈 개별 테스트 도구 실행: python test.py  포털별로 URL/파일경로를 직접 입력해서 단독 테스트 가능., URL 자동 감지 테스트 (crawler_main 사용), test_auto() (+6 more)

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (4): _digits_only(), LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler

### Community 18 - "Community 18"
Cohesion: 0.12
Nodes (6): EtaxUnipostHandler, format_biz_no(), format_date_yyyymmdd(), safe_filename(), split_classification(), text_or_none()

### Community 19 - "Community 19"
Cohesion: 0.39
Nodes (45): build_purchase_erp_payload(), build_regular_erp_payload(), _clean_text(), _configure_pyautogui_for_server(), _corp_codes(), _extract_invoice_date(), _extract_invoice_date_from_text(), _extract_pdf_text_for_date() (+37 more)

### Community 20 - "Community 20"
Cohesion: 0.11
Nodes (9): JobEvent, JobRecord, utc_now(), InvoiceIdsRequest, JobEventResponse, JobResponse, OutputSetRequest, PurchaseAnalysisUpdate (+1 more)

### Community 21 - "Community 21"
Cohesion: 0.23
Nodes (9): build_pdf_filename(), clean_token(), dedupe_path(), parse_pdf(), patch_crawler_file(), repair_db_rows(), safe_name(), site_from_biz_no() (+1 more)

### Community 22 - "Community 22"
Cohesion: 0.2
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 23 - "Community 23"
Cohesion: 0.08
Nodes (69): _add_months(), _alert_hour(), _alert_start_date(), _alias_matches_text(), _amount(), build_regular_due_report(), _clean_text(), _compact() (+61 more)

### Community 24 - "Community 24"
Cohesion: 0.08
Nodes (69): _add_months(), _alert_hour(), _alert_start_date(), _alias_matches_text(), _amount(), build_regular_due_report(), _clean_text(), _compact() (+61 more)

### Community 25 - "Community 25"
Cohesion: 0.3
Nodes (37): AutoEverHandler(), crawl_invoice(), _csbill_link_bill_no(), _csbill_link_priority(), CsbillHandler(), decode_mime_header(), _dedupe_csbill_links(), detect_handler() (+29 more)

### Community 26 - "Community 26"
Cohesion: 0.54
Nodes (27): auto_attach_compuzone_quote(), _clean_order_no(), _click_print_button(), _close_context(), _compuzone_accounts(), CompuzoneQuoteError, _emit(), fetch_compuzone_quote_pdf() (+19 more)

### Community 27 - "Community 27"
Cohesion: 0.28
Nodes (13): _customer_name_from_lines(), _extract_kt_statement_date(), _file_uri_to_path(), _find_sequence(), _fitz(), KtAttachmentHandler, _normalize_issue(), _normalize_mail_date() (+5 more)

### Community 28 - "Community 28"
Cohesion: 0.22
Nodes (8): AutoEverHandler, _clean_password_candidate(), _normalize_cell(), portal_name(), _table_cells(), _to_int(), _valid_password_candidate(), _write_text()

### Community 29 - "Community 29"
Cohesion: 0.21
Nodes (6): CsbillHandler, _parse_amount(), _parse_field(), _parse_item_name(), portal_name(), _write_text()

### Community 30 - "Community 30"
Cohesion: 0.21
Nodes (5): HometaxHandler, _parse_amount(), _parse_field(), portal_name(), _write_text()

### Community 31 - "Community 31"
Cohesion: 0.36
Nodes (9): _file_uri_to_path(), _font(), _guess_account(), _line(), _money(), _normalize_mail_date(), portal_name(), _to_int() (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.06
Nodes (1): WEB v1 backend package.

### Community 33 - "Community 33"
Cohesion: 0.06
Nodes (1): main()

### Community 34 - "Community 34"
Cohesion: 0.06
Nodes (1): Backend maintenance tools.

### Community 35 - "Community 35"
Cohesion: 0.06
Nodes (1): Accounting automation WEB v1 package.

### Community 36 - "Community 36"
Cohesion: 0.4
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 37 - "Community 37"
Cohesion: 0.07
Nodes (1): main()

### Community 38 - "Community 38"
Cohesion: 0.15
Nodes (2): Resolve-EnvValue(), Resolve-EnvValueAllowBlank()

### Community 39 - "Community 39"
Cohesion: 0.15
Nodes (2): Resolve-PythonExe(), Resolve-PythonwExe()

### Community 40 - "Community 40"
Cohesion: 0.11
Nodes (1): Program

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Excel voucher web application.

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): 이 핸들러가 처리 가능한 URL인지 반환.

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): 실제 크롤링 로직. result dict를 직접 채운다.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): 캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치.

### Community 281 - "Community 281"
Cohesion: 1.0
Nodes (1): Placeholder for the real ERP UI automation run on the 담당자 PC Agent.

### Community 282 - "Community 282"
Cohesion: 1.0
Nodes (1): 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)

### Community 283 - "Community 283"
Cohesion: 1.0
Nodes (1): ?멸툑怨꾩궛??URL(?먮뒗 濡쒖뺄 file:// 寃쎈줈) ??PDF ?ㅼ슫濡쒕뱶 ??寃곌낵 dict 諛섑솚.      諛섑솚媛?

### Community 284 - "Community 284"
Cohesion: 1.0
Nodes (1): KT 硫붿씪 紐낆꽭??PDF 泥⑤?瑜???ν븯怨?file:// URI 紐⑸줉 諛섑솚.     ?쒕ぉ ?먮뒗 泥⑤??뚯씪紐낆뿉 'KT emai

### Community 285 - "Community 285"
Cohesion: 1.0
Nodes (1): Save tax-invoice XML attachments and return file:// URIs.

### Community 286 - "Community 286"
Cohesion: 1.0
Nodes (1): 硫붿씪 HTML 蹂몃Ц?먯꽌 ?멸툑怨꾩궛???ы꽭 留곹겕留?異붿텧.

### Community 287 - "Community 287"
Cohesion: 1.0
Nodes (1): ?대찓??硫붿떆吏?먯꽌 NTS_eTaxInvoice.html 泥⑤??뚯씪??李얠븘 ?????     file:// URI 諛섑솚. ?놁쑝硫

### Community 288 - "Community 288"
Cohesion: 1.0
Nodes (1): 硫붿씪 ?섏떊????yymmdd ?뺤떇.

### Community 289 - "Community 289"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 290 - "Community 290"
Cohesion: 1.0
Nodes (1): 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)

### Community 291 - "Community 291"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 292 - "Community 292"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 293 - "Community 293"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 294 - "Community 294"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 295 - "Community 295"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 296 - "Community 296"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

## Knowledge Gaps
- **55 isolated node(s):** `DueRule`, `DueContact`, `DueRule`, `DueContact`, `Placeholder for the real ERP UI automation run on the 담당자 PC Agent.` (+50 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 32`** (34 nodes): `WEB v1 backend package.`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (34 nodes): `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `main()`, `create_https_cert.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (34 nodes): `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `Backend maintenance tools.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (31 nodes): `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `Accounting automation WEB v1 package.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (27 nodes): `main()`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`, `expense_excel_export.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (25 nodes): `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `Resolve-EnvValue()`, `Resolve-EnvValueAllowBlank()`, `install_operating_server.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (25 nodes): `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `Resolve-PythonExe()`, `Resolve-PythonwExe()`, `start_user_erp_agent.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (20 nodes): `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `Program`, `.Main()`, `.ReadServerUrl()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (2 nodes): `Excel voucher web application.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `이 핸들러가 처리 가능한 URL인지 반환.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `실제 크롤링 로직. result dict를 직접 채운다.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 281`** (1 nodes): `Placeholder for the real ERP UI automation run on the 담당자 PC Agent.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 282`** (1 nodes): `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 283`** (1 nodes): `?멸툑怨꾩궛??URL(?먮뒗 濡쒖뺄 file:// 寃쎈줈) ??PDF ?ㅼ슫濡쒕뱶 ??寃곌낵 dict 諛섑솚.      諛섑솚媛?`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 284`** (1 nodes): `KT 硫붿씪 紐낆꽭??PDF 泥⑤?瑜???ν븯怨?file:// URI 紐⑸줉 諛섑솚.     ?쒕ぉ ?먮뒗 泥⑤??뚯씪紐낆뿉 'KT emai`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 285`** (1 nodes): `Save tax-invoice XML attachments and return file:// URIs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 286`** (1 nodes): `硫붿씪 HTML 蹂몃Ц?먯꽌 ?멸툑怨꾩궛???ы꽭 留곹겕留?異붿텧.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 287`** (1 nodes): `?대찓??硫붿떆吏?먯꽌 NTS_eTaxInvoice.html 泥⑤??뚯씪??李얠븘 ?????     file:// URI 諛섑솚. ?놁쑝硫`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 288`** (1 nodes): `硫붿씪 ?섏떊????yymmdd ?뺤떇.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 289`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 290`** (1 nodes): `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 291`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 292`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 293`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 294`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 295`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 296`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `sleep()` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 14`, `Community 15`, `Community 16`, `Community 17`, `Community 18`, `Community 26`, `Community 28`, `Community 29`, `Community 30`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `BaseTaxInvoiceHandler` connect `Community 2` to `Community 27`, `Community 28`, `Community 29`, `Community 30`, `Community 31`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 205 inferred relationships involving `get_invoice()` (e.g. with `_start_purchase_approval_fetch_background()` and `_queue_expense_report_after_erp()`) actually correct?**
  _`get_invoice()` has 205 INFERRED edges - model-reasoned connections that need verification._
- **Are the 131 inferred relationships involving `build_output_set_status()` (e.g. with `_invoice_output_set_ready()` and `_queue_expense_report_after_erp()`) actually correct?**
  _`build_output_set_status()` has 131 INFERRED edges - model-reasoned connections that need verification._
- **Are the 128 inferred relationships involving `update_invoice_json()` (e.g. with `_regular_auto_mark_skip()` and `_queue_regular_auto_job()`) actually correct?**
  _`update_invoice_json()` has 128 INFERRED edges - model-reasoned connections that need verification._
- **Are the 102 inferred relationships involving `JobCreateRequest` (e.g. with `JobEvent` and `JobRecord`) actually correct?**
  _`JobCreateRequest` has 102 INFERRED edges - model-reasoned connections that need verification._
- **Are the 114 inferred relationships involving `sleep()` (e.g. with `api_generate_expense_report()` and `api_generate_expense_report()`) actually correct?**
  _`sleep()` has 114 INFERRED edges - model-reasoned connections that need verification._