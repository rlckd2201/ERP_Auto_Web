# Graph Report - (재정)회계업무 자동화_WEB_Version  (2026-06-29)

## Corpus Check
- 1939 files · ~3,510,579 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4837 nodes · 37301 edges · 79 communities detected
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 3111 edges (avg confidence: 0.79)
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
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
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
- [[_COMMUNITY_Community 297|Community 297]]
- [[_COMMUNITY_Community 298|Community 298]]
- [[_COMMUNITY_Community 299|Community 299]]
- [[_COMMUNITY_Community 300|Community 300]]
- [[_COMMUNITY_Community 301|Community 301]]
- [[_COMMUNITY_Community 302|Community 302]]
- [[_COMMUNITY_Community 303|Community 303]]
- [[_COMMUNITY_Community 304|Community 304]]
- [[_COMMUNITY_Community 305|Community 305]]
- [[_COMMUNITY_Community 306|Community 306]]
- [[_COMMUNITY_Community 307|Community 307]]
- [[_COMMUNITY_Community 308|Community 308]]
- [[_COMMUNITY_Community 309|Community 309]]
- [[_COMMUNITY_Community 310|Community 310]]
- [[_COMMUNITY_Community 311|Community 311]]
- [[_COMMUNITY_Community 312|Community 312]]
- [[_COMMUNITY_Community 313|Community 313]]
- [[_COMMUNITY_Community 314|Community 314]]
- [[_COMMUNITY_Community 315|Community 315]]
- [[_COMMUNITY_Community 316|Community 316]]

## God Nodes (most connected - your core abstractions)
1. `get_invoice()` - 244 edges
2. `build_output_set_status()` - 182 edges
3. `update_invoice_json()` - 161 edges
4. `sleep()` - 137 edges
5. `JobCreateRequest` - 136 edges
6. `add_invoice_log()` - 131 edges
7. `ERPAutoApp` - 92 edges
8. `safe_filename()` - 84 edges
9. `UplusEdocuHandler` - 82 edges
10. `EtaxUnipostHandler` - 79 edges

## Surprising Connections (you probably didn't know these)
- `api_regular_due_status()` --calls--> `regular_due_status()`  [INFERRED]
  _codex_app_zoom_auto_print_after_upload_fix196.py → _codex_stage_zoom_oneclick_enable_fix195_20260622_131614\web_v1\backend\regular_due_monitor.py
- `api_regular_due_history()` --calls--> `regular_due_history()`  [INFERRED]
  _codex_app_zoom_auto_print_after_upload_fix196.py → _codex_stage_zoom_oneclick_enable_fix195_20260622_131614\web_v1\backend\regular_due_monitor.py
- `api_regular_due_vendor_alert_sample()` --calls--> `send_regular_due_vendor_alert_sample()`  [INFERRED]
  _codex_app_zoom_auto_print_after_upload_fix196.py → _codex_stage_zoom_oneclick_enable_fix195_20260622_131614\web_v1\backend\regular_due_monitor.py
- `api_setup_installer()` --calls--> `find_installer()`  [INFERRED]
  _codex_app_zoom_auto_print_after_upload_fix196.py → _codex_stage_zoom_billing_manual_amount_fix184_20260617_154500\web_v1\backend\setup_state.py
- `api_list_invoices()` --calls--> `list_invoices()`  [INFERRED]
  _codex_app_zoom_auto_print_after_upload_fix196.py → C:\Users\user\Desktop\개발파일\회계업무 자동화_WEB_Version\_release_fix9_stage\web_v1\backend\invoice_db.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (681): add_invoice_log(), get_invoice(), update_invoice_json(), JobEvent, JobRecord, JobStore, utc_now(), InvoiceIdsRequest (+673 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (96): _active_invoice_items(), claim_next_erp_task(), now_text(), _read_task(), _task_files(), update_erp_task(), _write_task(), _app_version() (+88 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (98): _connection_error_message(), _download_job_source(), _execute_admin_command(), _heartbeat(), _install_agent_task(), _latest_agent_log(), main(), _popen_hidden() (+90 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (49): BaseTaxInvoiceHandler, sleep(), 메일 본문에서 법인 키워드를 찾아 사업자번호 후보 dict 반환., AutoEverHandler, _clean_password_candidate(), _normalize_cell(), portal_name(), _table_cells() (+41 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (133): AccountStore, AccountUser, hash_password(), make_temporary_password(), now_text(), protect_secret(), unprotect_secret(), verify_password() (+125 more)

### Community 5 - "Community 5"
Cohesion: 0.38
Nodes (124): _add_installer_file(), _add_installer_tree(), _admin_db_conn(), admin_db_page(), _admin_table_names(), _agent_bootstrap_script(), _agent_cmd_launcher(), _agent_exe_launcher() (+116 more)

### Community 6 - "Community 6"
Cohesion: 0.22
Nodes (136): accountOptions(), addLog(), agentConnectedFromSetup(), agentUpdateRequiredFromSetup(), applyDetailMode(), applyModeUi(), approvalPaths(), approvalStatusText() (+128 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (121): addLog(), agentConnectedFromSetup(), agentUpdateRequiredFromSetup(), applyDetailMode(), applyModeUi(), approvalPaths(), approvalStatusText(), autoStartAgentAfterLogin() (+113 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (121): addLog(), agentConnectedFromSetup(), agentUpdateRequiredFromSetup(), applyDetailMode(), applyModeUi(), approvalPaths(), approvalStatusText(), autoStartAgentAfterLogin() (+113 more)

### Community 9 - "Community 9"
Cohesion: 0.32
Nodes (90): _add_months(), _alert_hour(), _alert_start_date(), _alias_matches_text(), _amount(), build_regular_due_report(), _clean_text(), _compact() (+82 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (69): _active_install_job(), _add_check(), _age_seconds(), authenticate_user(), change_initial_password(), claim_install_job(), _columns(), complete_install_job() (+61 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (15): UplusEDocuHandler, _format_biz_no(), _format_date(), parse_tax_invoice_xml(), 반환: (supplier_dict, buyer_dict, content_dict)     content_dict 안에 '항목' 리스트 포함., _text(), child_text(), clean_text() (+7 more)

### Community 12 - "Community 12"
Cohesion: 0.19
Nodes (55): _check_playwright_runtime(), fetch_approval_documents(), _ai_parse(), analyze_purchase_documents(), _clean_match_text(), _clean_text(), _collapse_duplicate_total_prices(), _collapse_repeated_words() (+47 more)

### Community 13 - "Community 13"
Cohesion: 0.22
Nodes (73): _apply_company_erp_credentials(), _archive_pdf(), _clean_management_items(), _clipboard_account_name(), _clipboard_vendor_value(), _fallback_bank_management_items(), _fallback_line_management_items(), _file_uri() (+65 more)

### Community 14 - "Community 14"
Cohesion: 0.11
Nodes (35): ABC, _add_months(), BaseTaxInvoiceHandler, digits_only(), _do_process(), _get_chromedriver_service(), _is_stable(), _period_rule_key() (+27 more)

### Community 15 - "Community 15"
Cohesion: 0.48
Nodes (53): _aggregate_expense_items(), _appdata_template_candidates(), _build_expense_report_text(), _build_zoom_expense_report_text(), _clean_expense_item_name(), _clean_path(), _copy_or_merge_doc(), _docs_for_output() (+45 more)

### Community 16 - "Community 16"
Cohesion: 0.34
Nodes (51): _acquire_single_instance(), _agent_bundle_hash(), _agent_update_required(), AgentTray, _apply_server_setup_config(), _browser_pdf_print_app_candidates(), _cert_cache_path(), _cert_store_has_thumbprint() (+43 more)

### Community 17 - "Community 17"
Cohesion: 0.08
Nodes (14): portal_name(), LG U+ eDocu tax invoice portal adapter.  This adapter intentionally routes edo, UplusPortalHandler, main(), print_result(), 세금계산서 크롤링 모듈 개별 테스트 도구 실행: python test.py  포털별로 URL/파일경로를 직접 입력해서 단독 테스트 가능., URL 자동 감지 테스트 (crawler_main 사용), test_auto() (+6 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (4): _digits_only(), LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler

### Community 19 - "Community 19"
Cohesion: 0.12
Nodes (6): EtaxUnipostHandler, format_biz_no(), format_date_yyyymmdd(), safe_filename(), split_classification(), text_or_none()

### Community 20 - "Community 20"
Cohesion: 0.15
Nodes (6): decode_mime_header(), extract_target_links(), InvoiceMailWatcher, log(), read_part_text(), _split_csv()

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
Cohesion: 0.11
Nodes (4): _digits_only(), LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler

### Community 29 - "Community 29"
Cohesion: 0.21
Nodes (6): CsbillHandler, _parse_amount(), _parse_field(), _parse_item_name(), portal_name(), _write_text()

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (37): appendErpCredentials(), applyAuthUi(), askErpCredentials(), badge(), canUseApp(), changePassword(), commandStatus(), commandTitle() (+29 more)

### Community 31 - "Community 31"
Cohesion: 0.21
Nodes (5): HometaxHandler, _parse_amount(), _parse_field(), portal_name(), _write_text()

### Community 32 - "Community 32"
Cohesion: 0.36
Nodes (9): _file_uri_to_path(), _font(), _guess_account(), _line(), _money(), _normalize_mail_date(), portal_name(), _to_int() (+1 more)

### Community 33 - "Community 33"
Cohesion: 0.06
Nodes (1): WEB v1 backend package.

### Community 34 - "Community 34"
Cohesion: 0.06
Nodes (1): main()

### Community 35 - "Community 35"
Cohesion: 0.06
Nodes (1): Backend maintenance tools.

### Community 36 - "Community 36"
Cohesion: 0.06
Nodes (1): Accounting automation WEB v1 package.

### Community 37 - "Community 37"
Cohesion: 0.52
Nodes (12): _clean_text(), _decode_filename(), _extract_pdf_text(), extract_zoom_billing_invoice(), _first_match(), is_zoom_billing_mail(), _mail_date_to_iso(), _parse_date() (+4 more)

### Community 38 - "Community 38"
Cohesion: 0.4
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 39 - "Community 39"
Cohesion: 0.15
Nodes (2): Resolve-EnvValue(), Resolve-EnvValueAllowBlank()

### Community 40 - "Community 40"
Cohesion: 0.15
Nodes (2): Resolve-PythonExe(), Resolve-PythonwExe()

### Community 41 - "Community 41"
Cohesion: 0.11
Nodes (1): Program

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Excel voucher web application.

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): 이 핸들러가 처리 가능한 URL인지 반환.

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): 실제 크롤링 로직. result dict를 직접 채운다.

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): 캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치.

### Community 284 - "Community 284"
Cohesion: 1.0
Nodes (1): Run a dry-run print preview or the real legacy ERP automation on the voucher PC

### Community 285 - "Community 285"
Cohesion: 1.0
Nodes (1): Run a dry-run print preview or the real legacy ERP automation on the voucher PC

### Community 286 - "Community 286"
Cohesion: 1.0
Nodes (1): Run a dry-run print preview or the real legacy ERP automation on the voucher PC

### Community 287 - "Community 287"
Cohesion: 1.0
Nodes (1): Run a dry-run print preview or the real legacy ERP automation on the voucher PC

### Community 288 - "Community 288"
Cohesion: 1.0
Nodes (1): Run a dry-run print preview or the real legacy ERP automation on the voucher PC

### Community 289 - "Community 289"
Cohesion: 1.0
Nodes (1): Run a dry-run print preview or the real legacy ERP automation on the voucher PC

### Community 290 - "Community 290"
Cohesion: 1.0
Nodes (1): Run a dry-run print preview or the real legacy ERP automation on the voucher PC

### Community 291 - "Community 291"
Cohesion: 1.0
Nodes (1): 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)

### Community 292 - "Community 292"
Cohesion: 1.0
Nodes (1): 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)

### Community 293 - "Community 293"
Cohesion: 1.0
Nodes (1): Run a dry-run print preview or the real legacy ERP automation on the voucher PC

### Community 294 - "Community 294"
Cohesion: 1.0
Nodes (1): 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)

### Community 295 - "Community 295"
Cohesion: 1.0
Nodes (1): Run a dry-run print preview or the real legacy ERP automation on the voucher PC

### Community 296 - "Community 296"
Cohesion: 1.0
Nodes (1): Run a dry-run print preview or the real legacy ERP automation on the voucher PC

### Community 297 - "Community 297"
Cohesion: 1.0
Nodes (1): Placeholder for the real ERP UI automation run on the automatic voucher PC Agent

### Community 298 - "Community 298"
Cohesion: 1.0
Nodes (1): Placeholder for the real ERP UI automation run on the automatic voucher PC Agent

### Community 299 - "Community 299"
Cohesion: 1.0
Nodes (1): Placeholder for the real ERP UI automation run on the automatic voucher PC Agent

### Community 300 - "Community 300"
Cohesion: 1.0
Nodes (1): Placeholder for the real ERP UI automation run on the 담당자 PC Agent.

### Community 301 - "Community 301"
Cohesion: 1.0
Nodes (1): Placeholder for the real ERP UI automation run on the 담당자 PC Agent.

### Community 302 - "Community 302"
Cohesion: 1.0
Nodes (1): 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)

### Community 303 - "Community 303"
Cohesion: 1.0
Nodes (1): ?멸툑怨꾩궛??URL(?먮뒗 濡쒖뺄 file:// 寃쎈줈) ??PDF ?ㅼ슫濡쒕뱶 ??寃곌낵 dict 諛섑솚.      諛섑솚媛?

### Community 304 - "Community 304"
Cohesion: 1.0
Nodes (1): KT 硫붿씪 紐낆꽭??PDF 泥⑤?瑜???ν븯怨?file:// URI 紐⑸줉 諛섑솚.     ?쒕ぉ ?먮뒗 泥⑤??뚯씪紐낆뿉 'KT emai

### Community 305 - "Community 305"
Cohesion: 1.0
Nodes (1): Save tax-invoice XML attachments and return file:// URIs.

### Community 306 - "Community 306"
Cohesion: 1.0
Nodes (1): 硫붿씪 HTML 蹂몃Ц?먯꽌 ?멸툑怨꾩궛???ы꽭 留곹겕留?異붿텧.

### Community 307 - "Community 307"
Cohesion: 1.0
Nodes (1): ?대찓??硫붿떆吏?먯꽌 NTS_eTaxInvoice.html 泥⑤??뚯씪??李얠븘 ?????     file:// URI 諛섑솚. ?놁쑝硫

### Community 308 - "Community 308"
Cohesion: 1.0
Nodes (1): 硫붿씪 ?섏떊????yymmdd ?뺤떇.

### Community 309 - "Community 309"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 310 - "Community 310"
Cohesion: 1.0
Nodes (1): 분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)

### Community 311 - "Community 311"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 312 - "Community 312"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 313 - "Community 313"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 314 - "Community 314"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 315 - "Community 315"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 316 - "Community 316"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

## Knowledge Gaps
- **73 isolated node(s):** `DueRule`, `DueContact`, `DueRule`, `DueContact`, `Run a dry-run print preview or the real legacy ERP automation on the voucher PC` (+68 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 33`** (34 nodes): `WEB v1 backend package.`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (34 nodes): `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `main()`, `create_https_cert.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (34 nodes): `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `Backend maintenance tools.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (31 nodes): `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `Accounting automation WEB v1 package.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (25 nodes): `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `install_operating_server.ps1`, `Resolve-EnvValue()`, `Resolve-EnvValueAllowBlank()`, `install_operating_server.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (25 nodes): `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `start_user_erp_agent.ps1`, `Resolve-PythonExe()`, `Resolve-PythonwExe()`, `start_user_erp_agent.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (20 nodes): `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `AccountingWebRequiredSetup.cs`, `Program`, `.Main()`, `.ReadServerUrl()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (2 nodes): `Excel voucher web application.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `이 핸들러가 처리 가능한 URL인지 반환.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `실제 크롤링 로직. result dict를 직접 채운다.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 284`** (1 nodes): `Run a dry-run print preview or the real legacy ERP automation on the voucher PC`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 285`** (1 nodes): `Run a dry-run print preview or the real legacy ERP automation on the voucher PC`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 286`** (1 nodes): `Run a dry-run print preview or the real legacy ERP automation on the voucher PC`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 287`** (1 nodes): `Run a dry-run print preview or the real legacy ERP automation on the voucher PC`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 288`** (1 nodes): `Run a dry-run print preview or the real legacy ERP automation on the voucher PC`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 289`** (1 nodes): `Run a dry-run print preview or the real legacy ERP automation on the voucher PC`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 290`** (1 nodes): `Run a dry-run print preview or the real legacy ERP automation on the voucher PC`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 291`** (1 nodes): `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 292`** (1 nodes): `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 293`** (1 nodes): `Run a dry-run print preview or the real legacy ERP automation on the voucher PC`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 294`** (1 nodes): `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 295`** (1 nodes): `Run a dry-run print preview or the real legacy ERP automation on the voucher PC`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 296`** (1 nodes): `Run a dry-run print preview or the real legacy ERP automation on the voucher PC`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 297`** (1 nodes): `Placeholder for the real ERP UI automation run on the automatic voucher PC Agent`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 298`** (1 nodes): `Placeholder for the real ERP UI automation run on the automatic voucher PC Agent`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 299`** (1 nodes): `Placeholder for the real ERP UI automation run on the automatic voucher PC Agent`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 300`** (1 nodes): `Placeholder for the real ERP UI automation run on the 담당자 PC Agent.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 301`** (1 nodes): `Placeholder for the real ERP UI automation run on the 담당자 PC Agent.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 302`** (1 nodes): `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 303`** (1 nodes): `?멸툑怨꾩궛??URL(?먮뒗 濡쒖뺄 file:// 寃쎈줈) ??PDF ?ㅼ슫濡쒕뱶 ??寃곌낵 dict 諛섑솚.      諛섑솚媛?`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 304`** (1 nodes): `KT 硫붿씪 紐낆꽭??PDF 泥⑤?瑜???ν븯怨?file:// URI 紐⑸줉 諛섑솚.     ?쒕ぉ ?먮뒗 泥⑤??뚯씪紐낆뿉 'KT emai`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 305`** (1 nodes): `Save tax-invoice XML attachments and return file:// URIs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 306`** (1 nodes): `硫붿씪 HTML 蹂몃Ц?먯꽌 ?멸툑怨꾩궛???ы꽭 留곹겕留?異붿텧.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 307`** (1 nodes): `?대찓??硫붿떆吏?먯꽌 NTS_eTaxInvoice.html 泥⑤??뚯씪??李얠븘 ?????     file:// URI 諛섑솚. ?놁쑝硫`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 308`** (1 nodes): `硫붿씪 ?섏떊????yymmdd ?뺤떇.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 309`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 310`** (1 nodes): `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 311`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 312`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 313`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 314`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 315`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 316`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `sleep()` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 5`, `Community 6`, `Community 11`, `Community 13`, `Community 14`, `Community 15`, `Community 16`, `Community 17`, `Community 18`, `Community 19`, `Community 26`, `Community 28`, `Community 29`, `Community 31`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 3` to `Community 0`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 16` to `Community 0`, `Community 3`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 205 inferred relationships involving `get_invoice()` (e.g. with `_start_purchase_approval_fetch_background()` and `_queue_expense_report_after_erp()`) actually correct?**
  _`get_invoice()` has 205 INFERRED edges - model-reasoned connections that need verification._
- **Are the 131 inferred relationships involving `build_output_set_status()` (e.g. with `_invoice_output_set_ready()` and `_queue_expense_report_after_erp()`) actually correct?**
  _`build_output_set_status()` has 131 INFERRED edges - model-reasoned connections that need verification._
- **Are the 128 inferred relationships involving `update_invoice_json()` (e.g. with `_regular_auto_mark_skip()` and `_queue_regular_auto_job()`) actually correct?**
  _`update_invoice_json()` has 128 INFERRED edges - model-reasoned connections that need verification._
- **Are the 117 inferred relationships involving `sleep()` (e.g. with `api_generate_expense_report()` and `api_generate_expense_report()`) actually correct?**
  _`sleep()` has 117 INFERRED edges - model-reasoned connections that need verification._