# Feature Ledger

## Tax Invoice Crawling Core

- Intent: normalize invoice retrieval across multiple portals and attachments into one `crawl_invoice(...)` result shape.
- Main files: `crawler_main.py`, `base_handler.py`, active `portal_*.py`, `xml_parser.py`, `biz_groups.py`.
- Current behavior: detects portal support, runs the selected handler, downloads/creates a PDF, and returns invoice metadata plus status.
- Current unfinished refinement targets: WEHAGO parsing precision, HomeTax parsing precision, CSBill filename/parsing precision, AutoEver parsing precision, and KT parsing precision.
- U+ is excluded from active automation by user instruction; `portal_uplus.py` is retained only as legacy/reference code.

## Current Portal Test Inputs

- HomeTax sample: local `NTS_eTaxInvoice.html`; mail subject contains buyer company name, so test with that company's business number.
- KT samples: four local encrypted PDFs; subject token determines password candidates.
- WEHAGO sample URL: `https://www.wehago.com/invoice/#/eTaxMail/VFgyMDI2MDQ2OTQ5MjI3JjEyNTgxMDU2MTk=`
- AutoEver customer VPN sample URL: `https://etax.autoever.com/?flag=noMbr`
- CSBill sample URL: `https://www.csbill.co.kr/noRegIssueView.do?mode=view&mana_Bill_Numb=202640254004&mail=ds1500@dae-seung.co.kr&listYn=N&supp_Mail=N`

## KT Password Rules

- `704100003***`: Daeseung Precision. Try `32697` then `07029`.
- `W00127***`: skip automation; manual user handling.
- `W00115***`: Ilgang 1 factory, password `51622`.
- `z!23820968***`: Daeseung corporate registration last 7 digits, password `0003577`.

## Mail Target Routing

- Active link domains: Unipost, WEHAGO, CSBill, AutoEver.
- Active attachment types: HomeTax `NTS_eTaxInvoice.html`, KT encrypted PDF.
- Excluded: U+ eDocu.
- KT is handled without Selenium/Chrome.

## PDF Filename Rule

- Pattern: `세금계산서 - 업체명(시스템명)_법인명(사업자명)_기간.pdf`.
- Implemented in `BaseTaxInvoiceHandler.build_pdf_filename()`.
- XML-based portals should pass buyer business registration numbers so `FACTORY_MAP` can add the site/business name.
- KT passes the site/business name determined by its password rule.
- The period classifier should primarily use the tax invoice item/product name, with supplier/vendor name as fallback.

## Project Memory Lite

- Intent: preserve durable project context for future AI coding sessions.
- Main files: `AGENTS.md`, `PROJECT_STATE.md`, `DEVLOG.md`, `docs/AI_HANDOFF.md`, `docs/FEATURE_LEDGER.md`, `docs/DECISIONS.md`, `docs/USER_FEEDBACK.md`.
- Applied: 2026-04-28.

## Graphify Code Map

- Intent: provide a structural map of the codebase for architecture questions and refactor planning.
- Main files: `graphify-out/GRAPH_REPORT.md`, `graphify-out/graph.html`, `graphify-out/graph.json`.
- Applied: 2026-04-28.
