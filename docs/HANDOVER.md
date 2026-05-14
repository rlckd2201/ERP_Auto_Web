# Handover

Updated: 2026-05-07

This folder contains the final working files for an unfinished Python module set that saves PDF copies of tax invoices received by email.

## Final Source Files

- `base_handler.py`: common base for Selenium driver setup, download directory, file naming, and business-number candidate handling.
- `biz_groups.py`: company/site/business-number/keyword mapping.
- `config.ini`: shared crawler settings.
- `crawler_main.py`: integration entry point. Detects mail links/attachments and routes to portal handlers.
- `portal_uplus.py`: legacy U+ eDocu handler kept in the folder, but U+ is excluded from the active automation scope.
- `portal_unipost.py`: Unipost tax invoice handling.
- `portal_wehago.py`: WEHAGO entry, XML parsing, Chrome permission handling, Duzon preview, PDF saving.
- `portal_hometax.py`: HomeTax HTML secure mail authentication, rendered PDF saving, and XML attachment parsing.
- `portal_csbill.py`: CSBill authentication, XML parsing, and print-page PDF saving.
- `portal_autoever.py`: Hyundai AutoEver non-member one-time password entry, popup table parsing, and popup PDF saving.
- `portal_kt.py`: KT encrypted PDF attachment decryption, PDF text parsing, and saving.
- `test.py`: per-portal manual test menu.
- `xml_parser.py`: XML tax invoice parsing.

## Current Status

Stable direction:
- Unipost, WEHAGO, HomeTax, CSBill, AutoEver, and KT all have a first-pass path for entry and PDF saving.
- U+ is intentionally excluded from active mail detection and automation.
- WEB v1.0 SmartBill purchase-mail collection has a verified PDF-save path on the operating server. The active SmartBill marker is `SMARTBILL_FORM_POST_PRINT_V4`.

Needs refinement:
- WEB v1.0 must finish purchase collection result persistence/list refresh, then connect selected purchase invoices to ERP input jobs.
- End-to-end production scheduling still needs to be built around these handlers.

## SmartBill WEB v1.0 Print Note

The SmartBill print button is:

```html
<img id="ibtnPrint" onclick="fnPrint();" src="/image/common/btn_print.gif" alt="print">
```

The important behavior is inside `fnPrint()`: it sets `hdnCheckedIds` to
`dtiid;dtiWday;status;dtiType;arap;dtiDocType;BrkDtiYn;`, opens the popup target
`DTIPrint`, and submits `document.forms[0]` to `/xDTI/arap_repo/common/prt_prev.aspx`.
The crawler must preserve this form POST behavior. Directly opening
`dti_prev.aspx` or doing a plain GET to `prt_prev.aspx` is not the verified path.

## PDF Filename Rule

Use this common pattern:

```text
세금계산서 - 업체명(시스템명)_법인명(사업자명)_기간.pdf
```

Examples:
- `세금계산서 - KT(new kt biz GiGAoffice Compact)_대승정밀(주)(P1공장)_2026년 04월.pdf`
- `세금계산서 - KT(new kt biz GiGAoffice Compact)_대승정밀(주)(P4공장)_2026년 04월.pdf`

The `사업자명` part is important because one legal entity can have multiple business registrations/sites.

Period rules are based primarily on the tax invoice item/product name:
- Groupware/DaouOffice: issue-date month.
- NAC: issue-date month.
- DLP: issue-date month mapped to `03~05월 1차`, `06~08월 2차`, `09~11월 3차`, `12~02월 4차`.
- KT: previous month from issue date.
- Customer VPN: previous month from issue date.
- Watching-On: previous month from issue date.
- Acronis: previous month from issue date.

## Samples In This Folder

- Four KT encrypted PDF samples.
- One HomeTax `NTS_eTaxInvoice.html` sample.

Known test URLs:
- WEHAGO: `https://www.wehago.com/invoice/#/eTaxMail/VFgyMDI2MDQ2OTQ5MjI3JjEyNTgxMDU2MTk=`
- AutoEver customer VPN: `https://etax.autoever.com/?flag=noMbr`
- CSBill: `https://www.csbill.co.kr/noRegIssueView.do?mode=view&mana_Bill_Numb=202640254004&mail=ds1500@dae-seung.co.kr&listYn=N&supp_Mail=N`

## Authentication Notes

- HomeTax: mail subject contains the company name; test by entering that company's business number.
  - Current implementation authenticates the secure HTML, renders the visible invoice page to PDF, then downloads and parses the XML attachment for supplier/buyer/site/item/amount fields.
- WEHAGO: mail body contains the company name; test by entering that company's business number.
  - Current implementation prefers the URL token for the buyer business number, downloads XML after authentication, and uses XML issue date/item/tax/total for output data and filename period rules.
- CSBill: mail body contains the company name; test by entering that company's business number.
  - Current implementation authenticates, downloads CSBill XML through `/download.do`, parses the XML for invoice fields, and renders `/billPrint.do` to PDF.
- AutoEver: mail body contains a one-time non-member password that changes each time.
  - Current implementation extracts that password, opens the non-member invoice popup, parses the rendered table for supplier/buyer/item/date/amounts, and saves the popup as PDF.
- KT:
  - `(704100003***)`: Daeseung Precision. Try P1 password `32697`, then P4 password `07029`.
  - `(W00127***)`: ignore in automation; user will handle manually.
  - `(W00115***)`: Ilgang 1 factory password `51622`.
  - `(z!23820968***)`: Daeseung corporate registration password `0003577`.
  - Current implementation parses the decrypted PDF's tax-invoice summary rows for buyer business number, issue date, supply amount, and VAT, then maps the buyer business number to site names like `P1공장`, `P4공장`, `일강1공장`, and `D1공장`.

## Important Current Gaps

- `crawler_main.py` now routes AutoEver and KT, and U+ is excluded from active detection.
- `KtAttachmentHandler` now overrides `process()` and does not start Chrome for local PDF decryption.
- HomeTax secure HTML relies on remote scripts from `srtk.hometax.go.kr`; tests may depend on network access and browser script execution. The local sample has been verified through secure-mail authentication, XML download, XML parsing, and rendered PDF save.
- CSBill sample URL has been verified through business-number authentication, XML download, XML parsing, print-page rendering, and final PDF naming.
- WEHAGO sample URL has been verified through token-derived business-number authentication and XML download/parsing. Full PDF save still depends on the local Duzon print preview dialog being available.
- AutoEver sample URL has been verified through one-time password login, popup table parsing, rendered PDF saving, and final filename period/site naming.
- KT sample PDFs have been verified through token-specific password candidates, local PDF decryption, tax summary parsing, final filename period/site naming, and W00127 manual skip behavior.
