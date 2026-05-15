"""
?멸툑怨꾩궛???щ·留??듯빀 吏꾩엯??

?ъ슜踰?
    from crawler_main import crawl_invoice, extract_links_from_mail, extract_hometax_attachment

?쒕쾭(?꾪몴 ?먮룞??v3.1) check_email_background() ?곕룞:
    links  = extract_links_from_mail(body)
    attach = extract_hometax_attachment(msg, save_dir)
    targets = links + ([attach] if attach else [])
    for url in targets:
        result = crawl_invoice(url, mail_text=body, mail_date=...)
"""
import email
import email.header
import email.message
import html
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
log = logging.getLogger(__name__)


class _LazyHandler:
    def __init__(self, module_name: str, class_name: str):
        self.module_name = module_name
        self.class_name = class_name
        self._instance = None
        self._error = None

    def _load(self):
        if self._instance is not None:
            return self._instance
        if self._error:
            return None
        try:
            module = __import__(self.module_name, fromlist=[self.class_name])
            self._instance = getattr(module, self.class_name)()
            log.info(f"[crawler] handler loaded: {self.module_name}.{self.class_name} | {getattr(module, '__file__', '')}")
            return self._instance
        except Exception as e:
            self._error = str(e)
            log.error(f"[crawler] handler disabled: {self.module_name}.{self.class_name} | {e}")
            return None

    @property
    def portal_name(self):
        handler = self._load()
        return handler.portal_name if handler else self.module_name

    def supports(self, url: str) -> bool:
        handler = self._load()
        return bool(handler and handler.supports(url))

    def process(self, *args, **kwargs):
        handler = self._load()
        if not handler:
            return {"ok": False, "portal": self.module_name, "pdf_path": None, "subject": "", "data": {}, "error": self._error}
        return handler.process(*args, **kwargs)


def UnipostHandler():
    return _LazyHandler("portal_unipost", "UnipostHandler")


def UplusHandler():
    return _LazyHandler("portal_uplus", "UplusPortalHandler")


def WehagoHandler():
    return _LazyHandler("portal_wehago", "WehagoHandler")


def CsbillHandler():
    return _LazyHandler("portal_csbill", "CsbillHandler")


def AutoEverHandler():
    return _LazyHandler("portal_autoever", "AutoEverHandler")


def KtAttachmentHandler():
    return _LazyHandler("portal_kt", "KtAttachmentHandler")


def HometaxHandler():
    return _LazyHandler("portal_hometax", "HometaxHandler")

def XmlAttachmentHandler():
    return _LazyHandler("portal_xml", "XmlAttachmentHandler")

def SmartBillHandler():
    return _LazyHandler("portal_smartbill", "SmartBillHandler")


def SmileEdiHandler():
    return _LazyHandler("portal_smileedi", "SmileEdiHandler")


_HANDLERS = [
    UplusHandler(),
    XmlAttachmentHandler(),
    UnipostHandler(),
    WehagoHandler(),
    CsbillHandler(),
    AutoEverHandler(),
    KtAttachmentHandler(),
    SmartBillHandler(),
    SmileEdiHandler(),
    HometaxHandler(),   # 마지막 file:// URL 감지
]

# 留곹겕濡?媛먯????ы꽭 ?꾨찓??
_LINK_DOMAINS = [
    "etax.unipost.co.kr",
    "edocu.uplus.co.kr",
    "autoever.com",
]
_WEHAGO_INVOICE_PREFIX = "https://www.wehago.com/invoice/"
_CSBILL_LINK_PREFIX = "https://www.csbill.co.kr/"
_SMILEEDI_DOMAIN = "smileedi.com"
_SMILEEDI_PATH_HINT = "/dtiemail.do"
_LINK_ASSET_EXTENSIONS = (".png", ".jpg", ".gif", ".jpeg", ".css", ".js")


def _csbill_link_bill_no(link: str) -> str:
    try:
        qs = parse_qs(urlparse(link).query)
    except Exception:
        return ""
    return (qs.get("mana_Bill_Numb") or qs.get("mana_bill_numb") or [""])[0]


def _csbill_link_priority(link: str) -> int:
    path = (urlparse(link).path or "").lower()
    if path in {"/loginsave.do", "/noregissueview.do"}:
        return 0
    if path == "/mailreceive.do":
        return 1
    return 9


def _dedupe_csbill_links(links: list[str]) -> list[str]:
    best_by_bill: dict[str, tuple[int, str]] = {}
    drop: set[str] = set()

    for link in links:
        if not link.lower().startswith(_CSBILL_LINK_PREFIX):
            continue
        bill_no = _csbill_link_bill_no(link)
        if not bill_no:
            continue
        priority = _csbill_link_priority(link)
        current = best_by_bill.get(bill_no)
        if current is None or priority < current[0]:
            if current is not None:
                drop.add(current[1])
            best_by_bill[bill_no] = (priority, link)
        else:
            drop.add(link)

    return [link for link in links if link not in drop]


def _normalize_csbill_links(links: list[str]) -> list[str]:
    normalized: list[str] = []
    csbill_by_bill: dict[str, list[str]] = {}

    for link in links:
        if link.lower().startswith(_CSBILL_LINK_PREFIX):
            bill_no = _csbill_link_bill_no(link)
            if bill_no:
                csbill_by_bill.setdefault(bill_no, []).append(link)
                continue
        normalized.append(link)

    for bill_no, bill_links in csbill_by_bill.items():
        canonical = ""
        for link in bill_links:
            qs = parse_qs(urlparse(link).query)
            mail = (qs.get("mail") or [""])[0]
            if mail:
                query = urlencode(
                    {
                        "mode": "view",
                        "mana_Bill_Numb": bill_no,
                        "mail": mail,
                        "listYn": "N",
                        "supp_Mail": "N",
                    },
                    safe="@",
                )
                canonical = f"{_CSBILL_LINK_PREFIX}noRegIssueView.do?{query}"
                break
        normalized.append(canonical or bill_links[0])

    return normalized


def detect_handler(url: str):
    for h in _HANDLERS:
        if h.supports(url):
            return h
    return None


def crawl_invoice(url: str, mail_text: str = "", mail_date: str = "", mail_subject: str = "") -> dict:
    """
    ?멸툑怨꾩궛??URL(?먮뒗 濡쒖뺄 file:// 寃쎈줈) ??PDF ?ㅼ슫濡쒕뱶 ??寃곌낵 dict 諛섑솚.

    諛섑솚媛?
        ok        : bool
        portal    : str
        pdf_path  : str | None
        subject   : str
        data      : dict
        error     : str | None
    """
    if not mail_date:
        mail_date = time.strftime("%y%m%d")

    handler = detect_handler(url)
    if handler is None:
        log.warning(f"[crawler] unsupported portal: {url}")
        return {"ok": False, "portal": "unknown", "pdf_path": None,
                "subject": "", "data": {}, "error": f"지원하지 않는 포털: {url}"}

    log.info(f"[crawler] portal={handler.portal_name} | {url[:70]}...")
    result = handler.process(url=url, mail_text=mail_text, mail_date=mail_date, mail_subject=mail_subject)

    if result["ok"]:
        log.info(f"[crawler] done | {result.get('pdf_path')}")
    else:
        log.error(f"[crawler] failed | {result.get('error')}")

    return result


# ------------------------------------------------------------------
# ?대찓???뚯떛 ?ы띁
# ------------------------------------------------------------------

def decode_mime_header(value: str) -> str:
    if not value:
        return ""
    decoded_parts = email.header.decode_header(value)
    text = ""
    for bdata, charset in decoded_parts:
        if isinstance(bdata, bytes):
            text += bdata.decode(charset or "utf-8", errors="replace")
        else:
            text += bdata
    return text


def extract_kt_attachments(
    msg: email.message.Message,
    save_dir: str,
) -> list[str]:
    """
    KT 硫붿씪 紐낆꽭??PDF 泥⑤?瑜???ν븯怨?file:// URI 紐⑸줉 諛섑솚.
    ?쒕ぉ ?먮뒗 泥⑤??뚯씪紐낆뿉 'KT email 紐낆꽭??媛 ?덉뼱???쒕떎.
    """
    subject = decode_mime_header(msg.get("Subject", ""))
    is_kt_subject = "kt email" in subject.lower()
    token_match = re.search(r"\(([^)]+)\*{3}\)", subject)
    if token_match and token_match.group(1).startswith("W00127"):
        log.info("[attachment] KT W00127 mail skipped for manual processing")
        return []

    uris: list[str] = []

    for part in msg.walk():
        filename_raw = part.get_filename()
        if not filename_raw:
            continue

        filename = decode_mime_header(filename_raw)
        lower_name = filename.lower()
        if not lower_name.endswith(".pdf"):
            continue
        if "kt email" not in lower_name and not is_kt_subject:
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        save_path = Path(save_dir) / filename
        idx = 1
        while save_path.exists():
            save_path = Path(save_dir) / f"{save_path.stem}_{idx}{save_path.suffix}"
            idx += 1
        save_path.write_bytes(payload)
        log.info(f"[attachment] KT PDF saved: {save_path}")
        uris.append(save_path.as_uri())

    return uris


def extract_xml_attachments(
    msg: email.message.Message,
    save_dir: str,
) -> list[str]:
    """Save tax-invoice XML attachments and return file:// URIs."""
    uris: list[str] = []

    for part in msg.walk():
        filename_raw = part.get_filename()
        if not filename_raw:
            continue

        filename = decode_mime_header(filename_raw)
        if not filename.lower().endswith(".xml"):
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        save_path = Path(save_dir) / filename
        idx = 1
        while save_path.exists():
            save_path = Path(save_dir) / f"{save_path.stem}_{idx}{save_path.suffix}"
            idx += 1
        save_path.write_bytes(payload)
        log.info(f"[attachment] XML saved: {save_path}")
        uris.append(save_path.as_uri())

    return uris


def extract_links_from_mail(body: str) -> list[str]:
    """硫붿씪 HTML 蹂몃Ц?먯꽌 ?멸툑怨꾩궛???ы꽭 留곹겕留?異붿텧."""
    links = re.findall(r'https?://[^\s"\'<>]+', body)
    valid = []
    for link in links:
        link = html.unescape(link).strip().strip("\"'<>").rstrip(".,;)")
        link = re.sub(r"(?i)(?:&quot|quot)+$", "", link).rstrip(".,;)")
        lower_link = link.lower()

        if lower_link.startswith(_WEHAGO_INVOICE_PREFIX):
            valid.append(link)
            continue

        if _SMILEEDI_DOMAIN in lower_link and _SMILEEDI_PATH_HINT in lower_link:
            valid.append(link)
            continue

        if "smartbill.co.kr" in lower_link:
            if "smartbill.co.kr/xdti/n_mem" in lower_link:
                valid.append(link)
            continue

        if "csbill" in lower_link:
            if not lower_link.startswith(_CSBILL_LINK_PREFIX):
                continue
            if "/images/" in lower_link or "/imgs/" in lower_link:
                continue
            if lower_link.endswith(_LINK_ASSET_EXTENSIONS):
                continue
            valid.append(link)
            continue

        if not any(d in lower_link for d in _LINK_DOMAINS):
            continue
        if "/images/" in lower_link or "/imgs/" in lower_link:
            continue
        if lower_link.endswith(_LINK_ASSET_EXTENSIONS):
            continue
            
        # Uplus의 경우 실제 영수증 열람 링크만 허용 (고객센터, 서비스 안내 링크 무시)
        if "edocu.uplus.co.kr" in lower_link and "main.invoiceinfo.do" not in lower_link:
            continue
            
        valid.append(link)
    return _normalize_csbill_links(list(dict.fromkeys(valid)))


def extract_hometax_attachment(
    msg: email.message.Message,
    save_dir: str,
) -> Optional[str]:
    """
    ?대찓??硫붿떆吏?먯꽌 NTS_eTaxInvoice.html 泥⑤??뚯씪??李얠븘 ?????
    file:// URI 諛섑솚. ?놁쑝硫?None.

    ?ъ슜 ??
        import email
        msg = email.message_from_bytes(raw_bytes)
        file_uri = extract_hometax_attachment(msg, r"C:\\ERP_DB\\downloads")
        if file_uri:
            result = crawl_invoice(file_uri, mail_text=body)
    """
    for part in msg.walk():
        content_disp = part.get("Content-Disposition", "")
        filename_raw = part.get_filename()
        if not filename_raw:
            continue

        # ?몄퐫?⑸맂 ?뚯씪紐??붿퐫??
        decoded_parts = email.header.decode_header(filename_raw)
        filename = ""
        for bdata, charset in decoded_parts:
            if isinstance(bdata, bytes):
                filename += bdata.decode(charset or "utf-8", errors="replace")
            else:
                filename += bdata

        if "NTS_eTaxInvoice" not in filename and "nts_etaxinvoice" not in filename.lower():
            continue

        # ???
        payload = part.get_payload(decode=True)
        if not payload:
            continue

        save_path = Path(save_dir) / filename
        # 以묐났 諛⑹?
        idx = 1
        while save_path.exists():
            save_path = Path(save_dir) / f"{save_path.stem}_{idx}{save_path.suffix}"
            idx += 1

        save_path.write_bytes(payload)
        log.info(f"[attachment] HomeTax HTML saved: {save_path}")
        return save_path.as_uri()

    return None


def parse_mail_date(msg: email.message.Message) -> str:
    """硫붿씪 ?섏떊????yymmdd ?뺤떇."""
    date_str = msg.get("Date", "")
    import email.utils
    try:
        parsed = email.utils.parsedate(date_str)
        if parsed:
            return time.strftime("%y%m%d", parsed)
    except Exception:
        pass
    return time.strftime("%y%m%d")


# ------------------------------------------------------------------
# ?⑤룆 ?ㅽ뻾 ?뚯뒪??
# ------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    test_url  = sys.argv[1] if len(sys.argv) > 1 else "https://www.csbill.co.kr/TEST"
    test_text = sys.argv[2] if len(sys.argv) > 2 else "대승"

    res = crawl_invoice(url=test_url, mail_text=test_text)
    print("\n=== 寃곌낵 ===")
    for k, v in res.items():
        if k == "data":
            print("  data:")
            for dk, dv in (v or {}).items():
                print(f"    {dk}: {dv}")
        else:
            print(f"  {k}: {v}")
