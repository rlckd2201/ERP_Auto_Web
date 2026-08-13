# Graph Report - 회계업무 자동화_WEB_Version  (2026-08-13)

## Corpus Check
- 89 files · ~233,255 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1889 nodes · 5417 edges · 34 communities detected
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 1383 edges (avg confidence: 0.79)
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
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]

## God Nodes (most connected - your core abstractions)
1. `sleep()` - 108 edges
2. `ERPAutoApp` - 83 edges
3. `_load_nested_functions()` - 80 edges
4. `_FakeLogger` - 70 edges
5. `index()` - 53 edges
6. `SmileEdiHandler` - 48 edges
7. `get_invoice()` - 42 edges
8. `BaseTaxInvoiceHandler` - 40 edges
9. `_FakeRect` - 32 edges
10. `WehagoHandler` - 31 edges

## Surprising Connections (you probably didn't know these)
- `SMILE EDI tax invoice crawler.  Approval is opt-in because SMILE EDI approval` --uses--> `BaseTaxInvoiceHandler`  [INFERRED]
  tax_crawler\portal_smileedi.py → tax_crawler\base_handler.py
- `visible text input 중 마지막 = 모달 입력창.         확인 클릭 후 visible inputs 수가 줄면 인증 성공.` --uses--> `BaseTaxInvoiceHandler`  [INFERRED]
  tax_crawler\portal_wehago.py → tax_crawler\base_handler.py
- `Chrome 외부 앱 실행 권한 팝업에서 '허용' 버튼을 자동 클릭.         WEHAGO 인쇄 버튼 이후 1회성 팝업이 뜨는 구조라,` --uses--> `BaseTaxInvoiceHandler`  [INFERRED]
  tax_crawler\portal_wehago.py → tax_crawler\base_handler.py
- `UIA? ? ?? ?? Chrome ?? ??? ?? ??? ??? ??.` --uses--> `BaseTaxInvoiceHandler`  [INFERRED]
  tax_crawler\portal_wehago.py → tax_crawler\base_handler.py
- `Microsoft Print to PDF sometimes ignores the target folder.         If the corr` --uses--> `BaseTaxInvoiceHandler`  [INFERRED]
  tax_crawler\portal_wehago.py → tax_crawler\base_handler.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (187): Return read-only top-level window metadata for ERP connection diagnosis., _top_level_window_diagnostics(), index(), main(), sleep(), _detect_erp_target_monitor(), ERPLoginBot, _find_existing_erp_top_level_window() (+179 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (164): _active_invoice_items(), claim_next_erp_task(), now_text(), _read_task(), _task_files(), update_erp_task(), _write_task(), _add_installer_file() (+156 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (98): AccountStore, AccountUser, hash_password(), make_temporary_password(), now_text(), protect_secret(), unprotect_secret(), verify_password() (+90 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (130): addLog(), agentConnectedFromSetup(), agentUpdateRequiredFromSetup(), applyDetailMode(), applyModeUi(), approvalPaths(), approvalStatusText(), autoStartAgentAfterLogin() (+122 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (64): ABC, BaseTaxInvoiceHandler, build_pdf_filename(), clean_token(), dedupe_path(), parse_pdf(), repair_db_rows(), safe_name() (+56 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (24): on_startup(), _start_mail_collect_scheduler(), _start_regular_auto_scheduler(), _validate_install_info(), start_regular_due_scheduler(), loadOverview(), loadTable(), renderRows() (+16 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (83): AdminAgentCommandRequest, AdminResetJobsRequest, AgentAdminCommandCompleteRequest, AgentCompleteRequest, AgentEventRequest, BankTransfer, ChangePasswordRequest, ErpCredentialRequest (+75 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (63): _connection_error_message(), _download_job_source(), _execute_admin_command(), _heartbeat(), _install_agent_task(), _latest_agent_log(), main(), _normalize_printer_name() (+55 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (19): _site_name_from_biz_no(), _clean_html_cell(), _clean_text(), _date_after(), _element_label(), _field_after(), _font_rows(), _format_biz_no() (+11 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (47): _acquire_single_instance(), _agent_bundle_hash(), _agent_update_required(), AgentTray, _apply_server_setup_config(), _cert_cache_path(), _cert_store_has_thumbprint(), _cert_thumbprint() (+39 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (56): api_regular_due_check(), api_regular_due_history(), api_regular_due_status(), _add_months(), _alert_hour(), _alert_start_date(), _amount(), build_regular_due_report() (+48 more)

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (45): appendErpCredentials(), applyAuthUi(), askErpCredentials(), badge(), canUseApp(), changePassword(), commandStatus(), commandTitle() (+37 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (17): CsbillHandler, _parse_amount(), _parse_field(), _parse_item_name(), _write_text(), LG U+ eDocu tax invoice portal adapter.  This adapter intentionally routes edo, UplusPortalHandler, print_result() (+9 more)

### Community 13 - "Community 13"
Cohesion: 0.1
Nodes (43): api_setup_installer(), _app_version(), _env(), _env_bool(), _env_int(), _legacy_manager_path(), Settings, _version_file_default() (+35 more)

### Community 14 - "Community 14"
Cohesion: 0.11
Nodes (43): _check_playwright_runtime(), fetch_approval_documents(), _ai_parse(), analyze_purchase_documents(), _clean_match_text(), _clean_text(), _collapse_duplicate_total_prices(), _extract_amounts_from_tax() (+35 more)

### Community 15 - "Community 15"
Cohesion: 0.1
Nodes (39): build_purchase_erp_payload(), build_regular_erp_payload(), _clean_text(), _configure_pyautogui_for_server(), _corp_codes(), _extract_invoice_date(), _extract_invoice_date_from_text(), _extract_pdf_text_for_date() (+31 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (39): auto_attach_compuzone_quote(), _clean_order_no(), _click_print_button(), _close_context(), _compuzone_accounts(), CompuzoneQuoteError, _emit(), fetch_compuzone_quote_pdf() (+31 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (40): _aggregate_expense_items(), _appdata_template_candidates(), _build_expense_report_text(), _clean_expense_item_name(), _clean_path(), _copy_or_merge_doc(), _docs_for_output(), _ensure_appdata_expense_template() (+32 more)

### Community 18 - "Community 18"
Cohesion: 0.09
Nodes (29): AutoEverHandler(), _csbill_link_bill_no(), _csbill_link_priority(), CsbillHandler(), decode_mime_header(), _dedupe_csbill_links(), detect_handler(), extract_hometax_attachment() (+21 more)

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (12): _customer_name_from_lines(), _extract_kt_statement_date(), _file_uri_to_path(), _find_sequence(), _fitz(), KtAttachmentHandler, _normalize_issue(), _normalize_mail_date() (+4 more)

### Community 20 - "Community 20"
Cohesion: 0.17
Nodes (4): _digits_only(), LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler

### Community 21 - "Community 21"
Cohesion: 0.16
Nodes (6): EtaxUnipostHandler, format_biz_no(), format_date_yyyymmdd(), safe_filename(), split_classification(), text_or_none()

### Community 22 - "Community 22"
Cohesion: 0.17
Nodes (7): AutoEverHandler, _clean_password_candidate(), _normalize_cell(), _table_cells(), _to_int(), _valid_password_candidate(), _write_text()

### Community 23 - "Community 23"
Cohesion: 0.17
Nodes (4): _digits_only(), LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler

### Community 24 - "Community 24"
Cohesion: 0.33
Nodes (1): UplusEDocuHandler

### Community 25 - "Community 25"
Cohesion: 0.36
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 26 - "Community 26"
Cohesion: 0.36
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Excel voucher web application.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Accounting automation WEB v1 package.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): WEB v1 backend package.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Backend maintenance tools.

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): 이 핸들러가 처리 가능한 URL인지 반환.

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): 실제 크롤링 로직. result dict를 직접 채운다.

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): 캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치.

## Knowledge Gaps
- **37 isolated node(s):** `Return read-only top-level window metadata for ERP connection diagnosis.`, `Parse a payload flag without treating strings such as ``"0"`` as true.`, `Return whether this job is an explicitly authorized print-only recovery.`, `Return whether the open voucher needs management input, save, and print.`, `Run a dry-run print preview or the real legacy ERP automation on the voucher PC` (+32 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 24`** (12 nodes): `uplus_handler.py`, `UplusEDocuHandler`, `.build_pdf_filename_from_xml()`, `.click_approve_button()`, `.click_preview_print_button()`, `.click_xml_button()`, `.get_latest_downloaded_file()`, `.infer_and_build_nos()`, `.__init__()`, `.load_config()`, `.log()`, `.process()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (2 nodes): `Excel voucher web application.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (2 nodes): `__init__.py`, `Accounting automation WEB v1 package.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (2 nodes): `WEB v1 backend package.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (2 nodes): `Backend maintenance tools.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `이 핸들러가 처리 가능한 URL인지 반환.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `실제 크롤링 로직. result dict를 직접 채운다.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `sleep()` connect `Community 0` to `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 8`, `Community 9`, `Community 12`, `Community 16`, `Community 20`, `Community 21`, `Community 22`, `Community 23`, `Community 24`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Why does `_runtime_calibration_state()` connect `Community 0` to `Community 1`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `test_vendor_ds_foreground_activates_background_same_pid_window_with_win32()` connect `Community 0` to `Community 1`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 105 inferred relationships involving `sleep()` (e.g. with `_tail_log_admin_loop()` and `run_loop()`) actually correct?**
  _`sleep()` has 105 INFERRED edges - model-reasoned connections that need verification._
- **Are the 71 inferred relationships involving `RuntimeError` (e.g. with `_upload_job_artifact()` and `_install_agent_task()`) actually correct?**
  _`RuntimeError` has 71 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Return read-only top-level window metadata for ERP connection diagnosis.`, `Parse a payload flag without treating strings such as ``"0"`` as true.`, `Return whether this job is an explicitly authorized print-only recovery.` to the rest of the system?**
  _37 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.02 - nodes in this community are weakly interconnected._
