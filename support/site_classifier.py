import os
import re
import json
import time
import imaplib
import email
import configparser
from urllib.parse import urlparse
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr

import uplus_handler

try:
    import etax_unipost_handler
except Exception:
    etax_unipost_handler = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")


class InvoiceMailWatcher:
    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.read(config_file, encoding="utf-8")

        self.imap_server = self.config.get("EMAIL", "imap_server")
        self.email_id = self.config.get("EMAIL", "email_id")
        self.email_pw = self.config.get("EMAIL", "email_pw")

        self.sender_filters = self._split_csv(
            self.config.get("FILTER", "sender_keywords", fallback="")
        )
        self.subject_filters = self._split_csv(
            self.config.get("FILTER", "subject_keywords", fallback="")
        )

        self.handlers = {
            "edocu.uplus.co.kr": uplus_handler.UplusEDocuHandler(config_file=config_file),
        }

        if etax_unipost_handler is not None and hasattr(etax_unipost_handler, "EtaxUnipostHandler"):
            self.handlers["etax.unipost.co.kr"] = etax_unipost_handler.EtaxUnipostHandler(
                config_file=config_file
            )

    @staticmethod
    def log(msg: str):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

    @staticmethod
    def _split_csv(value: str):
        return [x.strip().lower() for x in value.split(",") if x.strip()]

    @staticmethod
    def decode_mime_header(value: str) -> str:
        decoded = decode_header(value or "")
        parts = []

        for text, enc in decoded:
            if isinstance(text, bytes):
                for codec in [enc, "utf-8", "cp949", "euc-kr", "latin1"]:
                    if not codec:
                        continue
                    try:
                        parts.append(text.decode(codec))
                        break
                    except Exception:
                        continue
                else:
                    parts.append(text.decode("utf-8", errors="ignore"))
            else:
                parts.append(text)

        return "".join(parts).strip()

    @staticmethod
    def read_part_text(part) -> str:
        payload = part.get_payload(decode=True)
        if payload is None:
            raw = part.get_payload()
            return raw if isinstance(raw, str) else ""

        charset = part.get_content_charset()
        for codec in [charset, "utf-8", "cp949", "euc-kr", "latin1"]:
            if not codec:
                continue
            try:
                return payload.decode(codec)
            except Exception:
                continue

        return payload.decode("utf-8", errors="ignore")

    def is_invoice_mail(self, msg, subject: str = "") -> bool:
        raw_from = self.decode_mime_header(msg.get("From", ""))
        raw_subject = subject or self.decode_mime_header(msg.get("Subject", ""))

        from_name, from_addr = parseaddr(raw_from)
        from_blob = f"{from_name} {from_addr} {raw_from}".lower()
        subject_blob = raw_subject.lower()

        sender_hit = any(keyword in from_blob for keyword in self.sender_filters) if self.sender_filters else False
        subject_hit = any(keyword in subject_blob for keyword in self.subject_filters) if self.subject_filters else False

        if self.sender_filters:
            return sender_hit or subject_hit
        return subject_hit

    @staticmethod
    def extract_target_links(full_text: str):
        text = full_text or ""

        links = re.findall(r'href=[\'"]?(https?://[^\'" >]+)', text, flags=re.I)
        if not links:
            links = re.findall(r'(https?://[^\s"\'<>]+)', text, flags=re.I)

        result = []
        for link in links:
            link = link.replace("&amp;", "&").strip()
            hostname = (urlparse(link).hostname or "").lower()
            if hostname in {"edocu.uplus.co.kr", "etax.unipost.co.kr"}:
                result.append(link)

        return list(dict.fromkeys(result))

    def get_handler(self, domain: str):
        return self.handlers.get(domain)

    def fetch_unseen_invoice_mails(self):
        self.log("========================================================")
        self.log("[메일] 읽지 않은 메일 스캔 시작")

        mail = imaplib.IMAP4_SSL(self.imap_server)
        mail.login(self.email_id, self.email_pw)
        mail.select("inbox")

        _, data = mail.search(None, "UNSEEN")
        email_ids = data[0].split()

        self.log(f"[메일] 읽지 않은 메일 수: {len(email_ids)}")

        for num in email_ids:
            try:
                _, msg_data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                subject = self.decode_mime_header(msg.get("Subject", ""))
                date_header = self.decode_mime_header(msg.get("Date", ""))

                if not self.is_invoice_mail(msg, subject):
                    self.log(f"[SKIP] 필터 제외: {subject}")
                    continue

                try:
                    mail_date = parsedate_to_datetime(date_header).strftime("%y%m%d")
                except Exception:
                    mail_date = time.strftime("%y%m%d")

                self.log(f"[메일] 대상 메일: {subject} / 수신일: {mail_date}")

                full_text_parts = []
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype in ("text/html", "text/plain"):
                        txt = self.read_part_text(part)
                        if txt:
                            full_text_parts.append(txt)

                full_text = "\n".join(full_text_parts)

                links = self.extract_target_links(full_text)
                if not links:
                    self.log(f"[SKIP] 링크 없음: {subject}")
                    continue

                for link in links:
                    source_domain = (urlparse(link).hostname or "").lower()
                    handler = self.get_handler(source_domain)

                    if handler is None:
                        self.log(f"[SKIP] 지원하지 않는 도메인: {source_domain}")
                        continue

                    request_data = {
                        "url": link,
                        "mail_subject": subject,
                        "mail_date": mail_date,
                        "mail_text": full_text,
                        "source_domain": source_domain,
                    }

                    self.log(f"[RUN] {subject} -> {link}")
                    self.log(f"      source_domain={source_domain}")

                    result = handler.process(request_data)
                    print(json.dumps(result, ensure_ascii=False, indent=2))

            except Exception as e:
                self.log(f"[ERROR] 메일 처리 실패: {e}")

        mail.logout()
        self.log("[시스템] 모든 작업 종료")
        self.log("========================================================")


if __name__ == "__main__":
    watcher = InvoiceMailWatcher()
    watcher.fetch_unseen_invoice_mails()