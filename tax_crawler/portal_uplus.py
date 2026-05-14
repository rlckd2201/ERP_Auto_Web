"""
LG U+ eDocu tax invoice portal adapter.

This adapter intentionally routes edocu.uplus.co.kr mails through the legacy
UplusEDocuHandler module that already knows how to authenticate, download XML,
and save the portal-produced original PDF.
"""
from types import SimpleNamespace


class UplusPortalHandler:
    DOMAIN = "edocu.uplus.co.kr"

    @property
    def portal_name(self) -> str:
        return "uplus"

    def supports(self, url: str) -> bool:
        return self.DOMAIN in str(url or "").lower()

    def process(self, url: str, mail_text: str = "", mail_date: str = "", mail_subject: str = "") -> dict:
        from uplus_handler import UplusEDocuHandler

        payload = SimpleNamespace(
            url=url,
            mail_text=mail_text or "",
            mail_date=mail_date or "",
            mail_subject=mail_subject or "",
        )
        raw = UplusEDocuHandler().process(payload)
        ok = bool(raw.get("ok") or raw.get("success"))
        data = raw.get("data") or raw.get("client_data") or {}
        error = raw.get("error") or raw.get("message")

        if not data and isinstance(raw.get("xml_data"), dict):
            data = raw["xml_data"]

        return {
            "ok": ok,
            "portal": "uplus",
            "pdf_path": raw.get("pdf_path"),
            "subject": raw.get("subject") or "",
            "data": data,
            "error": None if ok else (error or "U+ eDocu processing failed"),
            "raw": raw,
        }
