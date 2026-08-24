# Graph Report - 회계업무 자동화_WEB_Version  (2026-08-24)

## Corpus Check
- 71 files · ~160,740 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1505 nodes · 4181 edges · 38 communities detected
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 1095 edges (avg confidence: 0.78)
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
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]

## God Nodes (most connected - your core abstractions)
1. `sleep()` - 106 edges
2. `ERPAutoApp` - 83 edges
3. `BaseTaxInvoiceHandler` - 68 edges
4. `SmileEdiHandler` - 48 edges
5. `get_invoice()` - 45 edges
6. `WehagoHandler` - 41 edges
7. `update_invoice_json()` - 31 edges
8. `build_output_set_status()` - 30 edges
9. `add_invoice_log()` - 25 edges
10. `api_agent_job_complete()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `BaseTaxInvoiceHandler` --uses--> `SMILE EDI tax invoice crawler.  Approval is opt-in because SMILE EDI approval`  [INFERRED]
  tax_crawler\base_handler.py → tax_crawler\portal_smileedi.py
- `_move_window_to_erp_monitor()` --calls--> `sleep()`  [INFERRED]
  manager_server\전표 자동화 프로그램(담당자용)_v6.2.py → web_v1\frontend\app.js
- `to_int()` --calls--> `_build_data()`  [INFERRED]
  support\smartbill_server_hotfix.py → tax_crawler\portal_unipost.py
- `BaseTaxInvoiceHandler` --uses--> `AutoEverHandler`  [INFERRED]
  tax_crawler\base_handler.py → tax_crawler\portal_autoever.py
- `BaseTaxInvoiceHandler` --uses--> `CsbillHandler`  [INFERRED]
  tax_crawler\base_handler.py → tax_crawler\portal_csbill.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (178): _active_invoice_items(), claim_next_erp_task(), now_text(), _read_task(), _task_files(), update_erp_task(), _write_task(), _add_installer_file() (+170 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (100): ABC, sleep(), EtaxUnipostHandler, format_biz_no(), format_date_yyyymmdd(), safe_filename(), split_classification(), text_or_none() (+92 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (130): addLog(), agentConnectedFromSetup(), agentUpdateRequiredFromSetup(), applyDetailMode(), applyModeUi(), approvalPaths(), approvalStatusText(), autoStartAgentAfterLogin() (+122 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (13): _validate_install_info(), loadOverview(), loadTable(), renderRows(), renderTables(), requestJson(), showError(), ERPAutoApp (+5 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (81): api_regular_due_check(), api_regular_due_history(), api_regular_due_status(), _acquire_scheduler_process_lock(), _add_months(), _alert_hour(), _alert_start_date(), _alias_matches_text() (+73 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (29): BaseTaxInvoiceHandler, safe_name(), _site_name_from_biz_no(), _clean_html_cell(), _clean_text(), _date_after(), _element_label(), _field_after() (+21 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (62): auto_attach_compuzone_quote(), _clean_order_no(), _click_print_button(), _close_context(), _compuzone_accounts(), CompuzoneQuoteError, _emit(), fetch_compuzone_quote_pdf() (+54 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (53): _check_playwright_runtime(), fetch_approval_documents(), build_purchase_erp_payload(), build_regular_erp_payload(), _clean_text(), _configure_pyautogui_for_server(), _corp_codes(), _extract_invoice_date() (+45 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (23): decode_mime_header(), extract_target_links(), InvoiceMailWatcher, log(), read_part_text(), _split_csv(), HometaxHandler, _write_text() (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (47): _acquire_single_instance(), _agent_bundle_hash(), _agent_update_required(), AgentTray, _apply_server_setup_config(), _cert_cache_path(), _cert_store_has_thumbprint(), _cert_thumbprint() (+39 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (27): configure_page_setup(), main(), normalize_pdf_to_portrait_a4(), zoom_expense_retry_wait_seconds(), build_pdf_filename(), clean_token(), dedupe_path(), parse_pdf() (+19 more)

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (38): api_create_manual_purchase_invoice(), _ai_parse(), analyze_purchase_documents(), _clean_match_text(), _clean_text(), _collapse_duplicate_total_prices(), _extract_amounts_from_tax(), _extract_compuzone_quote_items() (+30 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (40): _aggregate_expense_items(), _appdata_template_candidates(), _build_expense_report_text(), _clean_expense_item_name(), _copy_or_merge_doc(), _docs_for_output(), _ensure_appdata_expense_template(), _excel_process_ids() (+32 more)

### Community 13 - "Community 13"
Cohesion: 0.1
Nodes (10): UplusEDocuHandler, CsbillHandler, _parse_amount(), _parse_field(), _parse_item_name(), _write_text(), _format_date(), parse_tax_invoice_xml() (+2 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (31): AutoEverHandler(), crawl_invoice(), _csbill_link_bill_no(), _csbill_link_priority(), CsbillHandler(), decode_mime_header(), _dedupe_csbill_links(), detect_handler() (+23 more)

### Community 15 - "Community 15"
Cohesion: 0.15
Nodes (34): api_setup_installer(), _active_install_job(), _add_check(), _age_seconds(), authenticate_user(), change_initial_password(), claim_install_job(), _columns() (+26 more)

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (4): _digits_only(), LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler

### Community 17 - "Community 17"
Cohesion: 0.17
Nodes (4): _digits_only(), LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름, _safe_name(), UplusEdocuHandler

### Community 18 - "Community 18"
Cohesion: 0.17
Nodes (7): AutoEverHandler, _clean_password_candidate(), _normalize_cell(), _table_cells(), _to_int(), _valid_password_candidate(), _write_text()

### Community 19 - "Community 19"
Cohesion: 0.36
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.36
Nodes (9): clean_amount(), find_text(), format_biz_no(), format_date_yyyymmdd(), parse_tax_invoice_xml(), parse_tax_invoice_xml_to_dict(), 지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다., split_classification() (+1 more)

### Community 21 - "Community 21"
Cohesion: 0.67
Nodes (1): Program

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Accounting automation WEB v1 package.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): WEB v1 backend package.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Backend maintenance tools.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): 이 핸들러가 처리 가능한 URL인지 반환.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): 실제 크롤링 로직. result dict를 직접 채운다.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): 캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): ?멸툑怨꾩궛??URL(?먮뒗 濡쒖뺄 file:// 寃쎈줈) ??PDF ?ㅼ슫濡쒕뱶 ??寃곌낵 dict 諛섑솚.      諛섑솚媛?

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): KT 硫붿씪 紐낆꽭??PDF 泥⑤?瑜???ν븯怨?file:// URI 紐⑸줉 諛섑솚.     ?쒕ぉ ?먮뒗 泥⑤??뚯씪紐낆뿉 'KT emai

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Save tax-invoice XML attachments and return file:// URIs.

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): 硫붿씪 HTML 蹂몃Ц?먯꽌 ?멸툑怨꾩궛???ы꽭 留곹겕留?異붿텧.

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): ?대찓??硫붿떆吏?먯꽌 NTS_eTaxInvoice.html 泥⑤??뚯씪??李얠븘 ?????     file:// URI 諛섑솚. ?놁쑝硫

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): 硫붿씪 ?섏떊????yymmdd ?뺤떇.

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Return the current local Windows spooler job ids for the selected printer.

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Wait until the Windows spooler exposes a job created after an output request.

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Install missing runtime packages into the exact Python used by the Agent.

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): The legacy UI module imports fitz at module load, but ERP input does not use it

## Knowledge Gaps
- **62 isolated node(s):** `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`, `지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다.`, `LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름`, `세금계산서 포털별 핸들러 공통 베이스.     각 포털 핸들러는 이 클래스를 상속하고 supports() / _do_process() 를 구현`, `이 핸들러가 처리 가능한 URL인지 반환.` (+57 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 21`** (4 nodes): `Program`, `.Main()`, `.ReadServerUrl()`, `AccountingWebRequiredSetup.cs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (2 nodes): `__init__.py`, `Accounting automation WEB v1 package.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (2 nodes): `WEB v1 backend package.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `Backend maintenance tools.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `이 핸들러가 처리 가능한 URL인지 반환.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `실제 크롤링 로직. result dict를 직접 채운다.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `캐시된 드라이버 우선 탐색 → 없으면 ChromeDriverManager 자동 설치.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `?멸툑怨꾩궛??URL(?먮뒗 濡쒖뺄 file:// 寃쎈줈) ??PDF ?ㅼ슫濡쒕뱶 ??寃곌낵 dict 諛섑솚.      諛섑솚媛?`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `KT 硫붿씪 紐낆꽭??PDF 泥⑤?瑜???ν븯怨?file:// URI 紐⑸줉 諛섑솚.     ?쒕ぉ ?먮뒗 泥⑤??뚯씪紐낆뿉 'KT emai`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Save tax-invoice XML attachments and return file:// URIs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `硫붿씪 HTML 蹂몃Ц?먯꽌 ?멸툑怨꾩궛???ы꽭 留곹겕留?異붿텧.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `?대찓??硫붿떆吏?먯꽌 NTS_eTaxInvoice.html 泥⑤??뚯씪??李얠븘 ?????     file:// URI 諛섑솚. ?놁쑝硫`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `硫붿씪 ?섏떊????yymmdd ?뺤떇.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Return the current local Windows spooler job ids for the selected printer.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Wait until the Windows spooler exposes a job created after an output request.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Install missing runtime packages into the exact Python used by the Agent.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `The legacy UI module imports fitz at module load, but ERP input does not use it`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `sleep()` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 12`, `Community 13`, `Community 16`, `Community 17`, `Community 18`?**
  _High betweenness centrality (0.232) - this node is a cross-community bridge._
- **Why does `BaseTaxInvoiceHandler` connect `Community 1` to `Community 5`, `Community 8`, `Community 10`, `Community 13`, `Community 18`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `api_generate_expense_report()` connect `Community 0` to `Community 1`, `Community 12`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Are the 103 inferred relationships involving `sleep()` (e.g. with `_move_window_to_erp_monitor()` and `._force_erp_window_maximized()`) actually correct?**
  _`sleep()` has 103 INFERRED edges - model-reasoned connections that need verification._
- **Are the 53 inferred relationships involving `BaseTaxInvoiceHandler` (e.g. with `AutoEverHandler` and `CsbillHandler`) actually correct?**
  _`BaseTaxInvoiceHandler` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Are the 51 inferred relationships involving `RuntimeError` (e.g. with `_detect_erp_target_monitor()` and `._force_erp_window_maximized()`) actually correct?**
  _`RuntimeError` has 51 INFERRED edges - model-reasoned connections that need verification._
- **What connects `분개전표입력 화면 자동 세팅 (v6.1 - Clipboard & UI ID Independence)`, `지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다.`, `LG U+ eDocu 전용 처리기.      기준 원칙     - 사업자번호 입력 / 새 사이트 진입 / PDF 저장은 테스트 완료본 흐름` to the rest of the system?**
  _62 weakly-connected nodes found - possible documentation gaps or missing edges._
