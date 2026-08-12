# Graph Report - 회계업무 자동화_WEB_Version  (2026-08-12)

## Corpus Check
- 64 files · ~172,078 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1458 nodes · 4187 edges · 32 communities detected
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 1028 edges (avg confidence: 0.78)
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
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]

## God Nodes (most connected - your core abstractions)
1. `sleep()` - 108 edges
2. `ERPAutoApp` - 83 edges
3. `BaseTaxInvoiceHandler` - 48 edges
4. `SmileEdiHandler` - 48 edges
5. `get_invoice()` - 46 edges
6. `WehagoHandler` - 38 edges
7. `collect_mail_once()` - 34 edges
8. `update_invoice_json()` - 31 edges
9. `build_output_set_status()` - 31 edges
10. `add_invoice_log()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `SMILE EDI tax invoice crawler.  Approval is opt-in because SMILE EDI approval` --uses--> `BaseTaxInvoiceHandler`  [INFERRED]
  tax_crawler\portal_smileedi.py → tax_crawler\base_handler.py
- `_move_window_to_erp_monitor()` --calls--> `sleep()`  [INFERRED]
  manager_server\전표 자동화 프로그램(담당자용)_v6.2.py → web_v1\frontend\app.js
- `run_invoice_erp_input()` --calls--> `ERPLoginBot`  [INFERRED]
  web_v1\backend\erp_runner.py → manager_server\전표 자동화 프로그램(담당자용)_v6.2.py
- `_build_data()` --calls--> `to_int()`  [INFERRED]
  tax_crawler\portal_unipost.py → support\smartbill_server_hotfix.py
- `AutoEverHandler` --uses--> `BaseTaxInvoiceHandler`  [INFERRED]
  tax_crawler\portal_autoever.py → tax_crawler\base_handler.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (155): _add_installer_file(), _add_installer_tree(), _admin_db_conn(), _admin_table_names(), _agent_bootstrap_script(), _agent_cmd_launcher(), _agent_exe_launcher(), _agent_installer_script() (+147 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (75): ABC, sleep(), EtaxUnipostHandler, format_biz_no(), format_date_yyyymmdd(), safe_filename(), split_classification(), text_or_none() (+67 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (130): addLog(), agentConnectedFromSetup(), agentUpdateRequiredFromSetup(), applyDetailMode(), applyModeUi(), approvalPaths(), approvalStatusText(), autoStartAgentAfterLogin() (+122 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (18): _validate_install_info(), showError(), AppManager, _detect_erp_target_monitor(), ERPAutoApp, ERPConfig, ERPLoginBot, _is_sane_amount() (+10 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (65): _acquire_single_instance(), _agent_bundle_hash(), _agent_update_required(), AgentTray, _apply_server_setup_config(), _browser_pdf_print_app_candidates(), _cert_cache_path(), _cert_store_has_thumbprint() (+57 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (72): api_regular_due_check(), api_regular_due_history(), api_regular_due_status(), api_regular_due_vendor_alert_sample(), _add_months(), _alert_hour(), _alert_start_date(), _alias_matches_text() (+64 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (19): _site_name_from_biz_no(), _clean_html_cell(), _clean_text(), _date_after(), _element_label(), _field_after(), _font_rows(), _format_biz_no() (+11 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (19): BaseTaxInvoiceHandler, UplusEDocuHandler, CsbillHandler, _parse_amount(), _parse_field(), _parse_item_name(), _write_text(), _file_uri_to_path() (+11 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (52): _aggregate_expense_items(), _appdata_template_candidates(), _build_expense_report_text(), _build_zoom_expense_report_text(), _clean_expense_item_name(), _clean_path(), _copy_or_merge_doc(), _display_date() (+44 more)

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (46): _resolve_purchase_site_name(), _check_playwright_runtime(), fetch_approval_documents(), build_purchase_erp_payload(), build_regular_erp_payload(), _clean_text(), _configure_pyautogui_for_server(), _corp_codes() (+38 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (44): api_mail_collect_history(), _allow_xml_attachment_fallback(), _clear_failure(), collect_mail_once(), CollectResult, _compact_text(), _crawl_invoice_with_retry(), _crawled_invoice_text() (+36 more)

### Community 11 - "Community 11"
Cohesion: 0.1
Nodes (48): api_agent_heartbeat(), api_agent_setup_install_complete(), api_login(), api_password_change_initial(), api_password_find(), api_password_reset_with_code(), api_setup_installer(), api_setup_printers() (+40 more)

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (18): decode_mime_header(), extract_target_links(), InvoiceMailWatcher, log(), read_part_text(), _split_csv(), LG U+ eDocu tax invoice portal adapter.  This adapter intentionally routes edo, UplusPortalHandler (+10 more)

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (37): api_create_manual_purchase_invoice(), _ai_parse(), analyze_purchase_documents(), _clean_match_text(), _clean_text(), _collapse_duplicate_total_prices(), _collapse_repeated_words(), _extract_amounts_from_tax() (+29 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (31): AutoEverHandler(), crawl_invoice(), _csbill_link_bill_no(), _csbill_link_priority(), CsbillHandler(), decode_mime_header(), _dedupe_csbill_links(), detect_handler() (+23 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (27): _active_invoice_items(), _age_seconds(), claim_next_erp_task(), now_text(), _read_task(), _task_files(), update_erp_task(), _write_task() (+19 more)

### Community 16 - "Community 16"
Cohesion: 0.14
Nodes (12): _customer_name_from_lines(), _extract_kt_statement_date(), _file_uri_to_path(), _find_sequence(), _fitz(), KtAttachmentHandler, _normalize_issue(), _normalize_mail_date() (+4 more)

### Community 17 - "Community 17"
Cohesion: 0.19
Nodes (27): auto_attach_compuzone_quote(), _clean_order_no(), _click_print_button(), _close_context(), _compuzone_accounts(), CompuzoneQuoteError, _emit(), fetch_compuzone_quote_pdf() (+19 more)

### Community 18 - "Community 18"
Cohesion: 0.17
Nodes (4): _digits_only(), LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (4): _digits_only(), LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler

### Community 20 - "Community 20"
Cohesion: 0.17
Nodes (7): AutoEverHandler, _clean_password_candidate(), _normalize_cell(), _table_cells(), _to_int(), _valid_password_candidate(), _write_text()

### Community 21 - "Community 21"
Cohesion: 0.4
Nodes (8): build_pdf_filename(), clean_token(), dedupe_path(), parse_pdf(), repair_db_rows(), safe_name(), site_from_biz_no(), to_int()

### Community 22 - "Community 22"
Cohesion: 0.36
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 23 - "Community 23"
Cohesion: 0.36
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 24 - "Community 24"
Cohesion: 0.43
Nodes (5): loadOverview(), loadTable(), renderRows(), renderTables(), requestJson()

### Community 25 - "Community 25"
Cohesion: 0.67
Nodes (1): Program

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Accounting automation WEB v1 package.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): WEB v1 backend package.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Backend maintenance tools.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): 이 핸들러가 처리 가능한 URL인지 반환.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): 실제 크롤링 로직. result dict를 직접 채운다.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): 캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치.

## Knowledge Gaps
- **36 isolated node(s):** `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`, `지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다.`, `LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름`, `세금계산서 포털별 핸들러 공통 베이스.     각 포털 핸들러는 이 클래스를 상속하고 supports() / _do_process() 를 구현`, `이 핸들러가 처리 가능한 URL인지 반환.` (+31 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 25`** (4 nodes): `Program`, `.Main()`, `.ReadServerUrl()`, `AccountingWebRequiredSetup.cs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (2 nodes): `__init__.py`, `Accounting automation WEB v1 package.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (2 nodes): `WEB v1 backend package.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (2 nodes): `Backend maintenance tools.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `이 핸들러가 처리 가능한 URL인지 반환.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `실제 크롤링 로직. result dict를 직접 채운다.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `sleep()` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 10`, `Community 12`, `Community 17`, `Community 18`, `Community 19`, `Community 20`?**
  _High betweenness centrality (0.285) - this node is a cross-community bridge._
- **Why does `BaseTaxInvoiceHandler` connect `Community 1` to `Community 16`, `Community 20`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `api_generate_expense_report()` connect `Community 0` to `Community 8`, `Community 1`, `Community 3`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 105 inferred relationships involving `sleep()` (e.g. with `_move_window_to_erp_monitor()` and `._force_erp_window_maximized()`) actually correct?**
  _`sleep()` has 105 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `RuntimeError` (e.g. with `_detect_erp_target_monitor()` and `._force_erp_window_maximized()`) actually correct?**
  _`RuntimeError` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `BaseTaxInvoiceHandler` (e.g. with `AutoEverHandler` and `CsbillHandler`) actually correct?**
  _`BaseTaxInvoiceHandler` has 33 INFERRED edges - model-reasoned connections that need verification._
- **What connects `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`, `지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다.`, `LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름` to the rest of the system?**
  _36 weakly-connected nodes found - possible documentation gaps or missing edges._