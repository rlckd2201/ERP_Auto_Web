# Project State

Updated: 2026-05-07

## Purpose

Tax invoice crawler/integration module for an accounting automation workflow. It detects supported invoice portal links or local attachments from email, downloads or generates PDFs, parses key invoice fields, and returns a normalized result dictionary.

## Main Entry Points

- `crawler_main.py`: public API for `crawl_invoice`, mail link extraction, HomeTax HTML attachment extraction, KT PDF attachment extraction, and mail date parsing.
- `base_handler.py`: shared Selenium/Chrome setup, download handling, filename helpers, business-number candidate lookup, and common handler contract.
- `test.py`: manual smoke-test runner for portal handlers.

## Portal Handlers

- `portal_uplus.py`: legacy LG U+ eDocu handler kept for reference, excluded from active automation.
- `portal_unipost.py`: Unipost eTax handler.
- `portal_wehago.py`: WEHAGO handler with XML parsing and Chrome/Windows print automation helpers.
- `portal_hometax.py`: HomeTax/NTS HTML attachment handler. It authenticates the secure HTML mail, renders the invoice view to PDF, and uses the decrypted XML attachment for reliable parsing.
- `portal_csbill.py`: CSBill handler. It authenticates with the buyer business number, downloads CSBill XML for parsing, and renders the print page to PDF.
- `portal_autoever.py`: AutoEver handler. It extracts the one-time password from mail text, opens the non-member invoice popup, parses the rendered table, and saves the popup as PDF.
- `portal_kt.py`: KT password-protected PDF attachment handler. It decrypts local attachments without Chrome and parses the tax-invoice summary rows from the PDF text.
- `xml_parser.py`: shared XML invoice parser used by several portal handlers.
- `biz_groups.py`: company keyword to business-number mapping.

## Current Notes

- 2026-05-07: WEB v1.0 SmartBill purchase-mail collection is verified through the difficult PDF-save step on the operating server. The active SmartBill marker is `SMARTBILL_FORM_POST_PRINT_V4`.
- 2026-05-07: SmartBill print must preserve the page's real `fnPrint()` behavior: set `hdnCheckedIds`, open the `DTIPrint` target, and POST `document.forms[0]` to `/xDTI/arap_repo/common/prt_prev.aspx`. Do not replace this with direct `dti_prev.aspx` navigation or a plain `prt_prev.aspx` GET.
- 2026-05-07: Working backup after SmartBill V4 success is `C:\Tmp\accounting_web_v1_working_smartbill_v4_20260507_171727.zip`; single-file backup marker is `portal_smartbill.py.WORKING_SMARTBILL_FORM_POST_V4_20260507_171727`.
- 2026-05-07: Next WEB v1.0 implementation target is purchase workflow completion: persist collected invoices reliably, show refreshable purchase invoice rows, then queue selected invoices for ERP entry.

- 2026-05-06: Active product naming reset to `회계업무 자동화 WEB v1.0`. New active development root is `web_v1`; existing manager v6.2/server v3.2 files remain as CS reference sources.
- 2026-04-30: Manager v6.2 Compuzone purchase slip generation now treats monitor arms as `소모품비` and uses all purchase item names for VAT/payable summaries, e.g. `터치모니터, 모니터암(공급가액 - 수량)`.
- 2026-04-30: Manager v6.2 KT management vendor fields now input `케이티` and select the 거래처 row with business number `102-81-42945` for all corporations.
- 2026-04-30: KT encrypted source PDF test confirmed password `51622` opens the Ilgang sample and preserving the decrypted PDF text yields `명세서 작성일자`/tax approval date `2026-04-06`. KT handler now saves text-preserved decrypted PDFs before any image fallback, and manager v6.2 blocks today's-date fallback.
- 2026-04-30: Server `C:\ERP_DB` copy confirmed CSBill failures were caused by same-name XML overwrite detection, not no XML download. `portal_csbill.py` now watches XML mtime/size changes and renders the invoice frame directly to PDF.
- 2026-04-30: KT handler now prefers real service/product text lines such as `biz Managed 보안` and returns `통신비` for ERP item account. The old server DB row with item `86028466273` was produced by pre-fix parsing.
- 2026-04-30: Manager v6.2 purchase tab now displays row numbers instead of DB ids, keeps invoice ids in tree item ids, extracts Compuzone approval lookup numbers only from the PDF `견적번호` label's adjacent 8 digits before filename fallback, and handles Ilgang KT management fields/deduped vendor selection.
- Graphify has been installed for this project and generated `graphify-out/`.
- `AGENTS.md` now contains Project Memory Lite plus Graphify usage rules.
- Existing backup material is kept in `세금계산서_크롤러_백업_20260428_kt_cleanup/`.
- User clarified this project is unfinished and will be completed iteratively with Codex. Primary goal is saving PDFs for tax invoices received by email.
- User clarified U+ should be excluded from future active automation work.
- Before code edits, create a timestamped backup of files to be changed.
- Active auto-routing currently covers Unipost, WEHAGO, CSBill, AutoEver, KT PDF attachments, and HomeTax HTML attachments.
- KT PDF handling no longer starts Chrome and skips `W00127***` as manual.
- HomeTax sample parsing now uses the XML attachment after authentication. The verified sample resolves supplier `주식회사 시큐어포인트`, buyer `(주)대승`, buyer site `D1공장`, issue month `2026년 04월`, total `1,039,390`, and tax `94,490`.
- CSBill sample parsing now uses CSBill's XML download after authentication. The verified sample resolves supplier `(주)다우기술`, buyer `(주)대승`, buyer site `D1공장`, item `그룹웨어 서비스 이용료`, issue month `2026년 04월`, total `3,542,000`, and tax `322,000`.
- WEHAGO sample URL authenticates and downloads XML. The verified XML resolves supplier `(주)에티버스`, buyer `(주)대승`, buyer site `D1공장`, item `Watching-On 모니터링 서비스`, issue month `2026년 03월` by previous-month rule, total `163,350`, and tax `14,850`.
- AutoEver sample URL with one-time password `2026042098s6hv0m399p` resolves supplier `현대오토에버(주)`, buyer `(주)대승`, buyer site `D1공장`, item `(주)대승_평택_SDWAN`, issue month `2026년 03월` by previous-month rule, total `148,830`, and tax `13,530`.
- KT samples now resolve buyer site labels and VAT from the decrypted PDF tax-invoice summary: P1 `603,220`/VAT `54,838`, Ilgang1 `1,878,800`/VAT `170,800`, P4 `2,511,300`/VAT `228,300`, and Daeseung D1 `2,427,940`/VAT `220,722`.
- PDF filename rule: `세금계산서 - 업체명(시스템명)_법인명(사업자명)_현재월.pdf`. The business/site name should distinguish multiple business registrations under the same legal entity, such as `대승정밀(주)(P1공장)` and `대승정밀(주)(P4공장)`.
- Period labels in filenames are determined mostly from the tax invoice item/product name, with supplier/vendor name as a fallback.
- Sample files currently present: 4 KT encrypted PDF attachments and 1 HomeTax `NTS_eTaxInvoice.html`.
- Known sample URLs:
  - WEHAGO: `https://www.wehago.com/invoice/#/eTaxMail/VFgyMDI2MDQ2OTQ5MjI3JjEyNTgxMDU2MTk=`
  - AutoEver customer VPN: `https://etax.autoever.com/?flag=noMbr`
  - CSBill: `https://www.csbill.co.kr/noRegIssueView.do?mode=view&mana_Bill_Numb=202640254004&mail=ds1500@dae-seung.co.kr&listYn=N&supp_Mail=N`
- KT mail subject token rules:
  - `(704100003***)`: Daeseung Precision. Try P1 business-number last 5 digits `32697`, then P4 last 5 digits `07029`.
  - `(W00127***)`: ignore for automation; user will handle manually.
  - `(W00115***)`: Ilgang. Use Ilgang 1 factory business-number last 5 digits `51622`.
  - `(z!23820968***)`: Daeseung. Use corporate registration number last 7 digits `0003577` from `134711-0003577`.
- HomeTax, WEHAGO, and CSBill identify the buyer/company from the mail subject/body and should test with that company's business number.
- AutoEver customer VPN receives a different one-time non-member password in the mail body each time.

## Verification Habit

For code edits, prefer at least `py_compile` on touched Python files. For portal changes, use focused manual or scripted smoke tests when browser/network dependencies are available.
