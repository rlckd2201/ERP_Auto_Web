# Graph Report - 회계업무 자동화_WEB_Version  (2026-05-15)

## Corpus Check
- 231 files · ~261,828 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1330 nodes · 4238 edges · 34 communities detected
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 727 edges (avg confidence: 0.78)
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
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]

## God Nodes (most connected - your core abstractions)
1. `ERPAutoApp` - 85 edges
2. `SmileEdiHandler` - 48 edges
3. `BaseTaxInvoiceHandler` - 41 edges
4. `get_invoice()` - 41 edges
5. `WehagoHandler` - 32 edges
6. `add_invoice_log()` - 27 edges
7. `update_invoice_json()` - 27 edges
8. `init_db()` - 25 edges
9. `build_output_set_status()` - 25 edges
10. `UplusEdocuHandler` - 24 edges

## Surprising Connections (you probably didn't know these)
- `BaseTaxInvoiceHandler` --uses--> `SMILE EDI tax invoice crawler prototype.  This module is intentionally not regis`  [INFERRED]
  _backup_working_smartbill_v4_20260507_171727\tax_crawler\base_handler.py → tax_crawler\portal_smileedi.py
- `ERPLoginBot` --calls--> `run_invoice_erp_input()`  [INFERRED]
  _release_fix9_stage\manager_server\전표 자동화 프로그램(담당자용)_v6.2.py → _release_fix9_stage\web_v1\backend\erp_runner.py
- `BaseTaxInvoiceHandler` --uses--> `AutoEverHandler`  [INFERRED]
  _backup_working_smartbill_v4_20260507_171727\tax_crawler\base_handler.py → _backup_working_smartbill_v4_20260507_171727\tax_crawler\portal_autoever.py
- `BaseTaxInvoiceHandler` --uses--> `CsbillHandler`  [INFERRED]
  _backup_working_smartbill_v4_20260507_171727\tax_crawler\base_handler.py → _backup_working_smartbill_v4_20260507_171727\tax_crawler\portal_csbill.py
- `BaseTaxInvoiceHandler` --uses--> `KtAttachmentHandler`  [INFERRED]
  _backup_working_smartbill_v4_20260507_171727\tax_crawler\base_handler.py → _backup_working_smartbill_v4_20260507_171727\tax_crawler\portal_kt.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (50): main(), _aggregate_expense_items(), _appdata_template_candidates(), _build_expense_report_text(), _clean_expense_item_name(), _clean_path(), _copy_or_merge_doc(), _ensure_appdata_expense_template() (+42 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (63): ABC, BaseTaxInvoiceHandler, _add_months(), BaseTaxInvoiceHandler, digits_only(), _do_process(), _get_chromedriver_service(), _is_stable() (+55 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (71): _add_installer_file(), _add_installer_tree(), _agent_bootstrap_script(), _agent_cmd_launcher(), _agent_exe_launcher(), _agent_installer_script(), _agent_self_contained_cmd(), _agent_update_notes() (+63 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (103): accountOptions(), addLog(), agentConnectedFromSetup(), agentUpdateRequiredFromSetup(), applyDetailMode(), applyModeUi(), approvalPaths(), approvalStatusText() (+95 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (72): api_create_manual_purchase_invoice(), _save_pdf_upload(), _check_playwright_runtime(), fetch_approval_documents(), build_purchase_erp_payload(), build_regular_erp_payload(), _clean_text(), _configure_pyautogui_for_server() (+64 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (18): _clean_html_cell(), _clean_text(), _date_after(), _element_label(), _field_after(), _font_rows(), _format_biz_no(), _hidden_values() (+10 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (45): _acquire_single_instance(), _agent_bundle_hash(), _agent_update_required(), AgentTray, _apply_server_setup_config(), _cert_cache_path(), _cert_store_has_thumbprint(), _cert_thumbprint() (+37 more)

### Community 7 - "Community 7"
Cohesion: 0.16
Nodes (49): _active_invoice_items(), claim_next_erp_task(), now_text(), _read_task(), _task_files(), update_erp_task(), _write_task(), api_agent_job_complete() (+41 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (23): _app_version(), _env(), _env_bool(), _env_int(), _legacy_manager_path(), _load_env_file(), Settings, _version_file_default() (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.1
Nodes (20): decode_mime_header(), extract_target_links(), InvoiceMailWatcher, log(), read_part_text(), _split_csv(), portal_name(), LG U+ eDocu tax invoice portal adapter.  This adapter intentionally routes edo (+12 more)

### Community 10 - "Community 10"
Cohesion: 0.1
Nodes (37): AutoEverHandler(), crawl_invoice(), _csbill_link_bill_no(), _csbill_link_priority(), CsbillHandler(), decode_mime_header(), _dedupe_csbill_links(), detect_handler() (+29 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (37): api_agent_heartbeat(), api_agent_setup_install_complete(), api_login(), api_setup_installer(), api_setup_printers(), _active_install_job(), _add_check(), _age_seconds() (+29 more)

### Community 12 - "Community 12"
Cohesion: 0.17
Nodes (13): _customer_name_from_lines(), _extract_kt_statement_date(), _file_uri_to_path(), _find_sequence(), _fitz(), KtAttachmentHandler, _normalize_issue(), _normalize_mail_date() (+5 more)

### Community 13 - "Community 13"
Cohesion: 0.19
Nodes (27): auto_attach_compuzone_quote(), _clean_order_no(), _click_print_button(), _close_context(), _compuzone_accounts(), CompuzoneQuoteError, _emit(), fetch_compuzone_quote_pdf() (+19 more)

### Community 14 - "Community 14"
Cohesion: 0.16
Nodes (4): _digits_only(), LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler

### Community 15 - "Community 15"
Cohesion: 0.2
Nodes (14): build_pdf_filename(), clean_token(), dedupe_path(), parse_pdf(), patch_crawler_file(), repair_db_rows(), safe_name(), site_from_biz_no() (+6 more)

### Community 16 - "Community 16"
Cohesion: 0.18
Nodes (6): EtaxUnipostHandler, format_biz_no(), format_date_yyyymmdd(), safe_filename(), split_classification(), text_or_none()

### Community 17 - "Community 17"
Cohesion: 0.17
Nodes (4): _digits_only(), LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler

### Community 18 - "Community 18"
Cohesion: 0.19
Nodes (6): AutoEverHandler, _normalize_cell(), portal_name(), _table_cells(), _to_int(), _write_text()

### Community 19 - "Community 19"
Cohesion: 0.16
Nodes (6): UplusEDocuHandler, _format_biz_no(), _format_date(), parse_tax_invoice_xml(), 반환: (supplier_dict, buyer_dict, content_dict)     content_dict 안에 '항목' 리스트 포함., _text()

### Community 20 - "Community 20"
Cohesion: 0.22
Nodes (6): CsbillHandler, _parse_amount(), _parse_field(), _parse_item_name(), portal_name(), _write_text()

### Community 21 - "Community 21"
Cohesion: 0.51
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 22 - "Community 22"
Cohesion: 0.44
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 23 - "Community 23"
Cohesion: 0.22
Nodes (1): WEB v1 backend package.

### Community 24 - "Community 24"
Cohesion: 0.22
Nodes (1): main()

### Community 25 - "Community 25"
Cohesion: 0.22
Nodes (1): Backend maintenance tools.

### Community 26 - "Community 26"
Cohesion: 0.33
Nodes (1): Accounting automation WEB v1 package.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): 이 핸들러가 처리 가능한 URL인지 반환.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): 실제 크롤링 로직. result dict를 직접 채운다.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): 캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치.

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

## Knowledge Gaps
- **35 isolated node(s):** `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`, `지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다.`, `LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름`, `세금계산서 포털별 핸들러 공통 베이스.     각 포털 핸들러는 이 클래스를 상속하고 supports() / _do_process() 를 구현`, `이 핸들러가 처리 가능한 URL인지 반환.` (+30 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 23`** (9 nodes): `WEB v1 backend package.`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (9 nodes): `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `create_https_cert.py`, `main()`, `create_https_cert.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (9 nodes): `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `Backend maintenance tools.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (6 nodes): `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `Accounting automation WEB v1 package.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `이 핸들러가 처리 가능한 URL인지 반환.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `실제 크롤링 로직. result dict를 직접 채운다.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SmileEdiHandler` connect `Community 5` to `Community 1`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Why does `BaseTaxInvoiceHandler` connect `Community 1` to `Community 5`, `Community 12`, `Community 15`, `Community 18`, `Community 20`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `JobStore` connect `Community 2` to `Community 0`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `RuntimeError` (e.g. with `.run()` and `._setup_slip_form()`) actually correct?**
  _`RuntimeError` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `BaseTaxInvoiceHandler` (e.g. with `AutoEverHandler` and `CsbillHandler`) actually correct?**
  _`BaseTaxInvoiceHandler` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `get_invoice()` (e.g. with `_active_invoice_items()` and `claim_next_erp_task()`) actually correct?**
  _`get_invoice()` has 29 INFERRED edges - model-reasoned connections that need verification._
- **What connects `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`, `지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다.`, `LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름` to the rest of the system?**
  _35 weakly-connected nodes found - possible documentation gaps or missing edges._