import os
import re
import time
import json
import base64
from pathlib import Path
from urllib.parse import unquote

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_handler import BaseTaxInvoiceHandler
from xml_parser import parse_tax_invoice_xml


class HometaxHandler(BaseTaxInvoiceHandler):

    @property
    def portal_name(self) -> str:
        return "hometax"

    def supports(self, url: str) -> bool:
        raw = unquote(str(url or ""))
        lower = raw.lower()
        return (
            "nts_etaxinvoice" in lower
            and (lower.startswith("file://") or lower.endswith((".html", ".htm")))
        )

    def _do_process(self, driver, url, mail_text, mail_date, result):
        candidates = self.build_candidate_nos(mail_text)
        dump_dir = self._make_debug_dir(mail_date)
        result["debug_dir"] = str(dump_dir)

        self._write_text(
            dump_dir / "00_candidates.json",
            json.dumps(
                {"mail_text": mail_text, "candidates": candidates},
                ensure_ascii=False,
                indent=2,
            ),
        )

        if not candidates:
            result["error"] = "홈택스 법인 후보를 찾지 못했습니다."
            return

        file_url = url if url.startswith("file://") else Path(url).as_uri()
        driver.get(file_url)
        time.sleep(2)
        self._dump_state(driver, dump_dir, "01_before_auth")

        matched = self._auth_secure_mail(driver, candidates, dump_dir)
        if not matched:
            self._dump_state(driver, dump_dir, "02_auth_failed")
            result["error"] = "홈택스 보안메일 인증에 실패했습니다."
            return

        self._write_text(dump_dir / "02_auth_result.txt", f"matched={matched}\n")
        time.sleep(2)
        self._dump_state(driver, dump_dir, "03_after_auth")

        temp_pdf = dump_dir / "05_rendered_invoice.pdf"
        if not self._save_pdf_from_page(driver, temp_pdf, dump_dir):
            self._dump_state(driver, dump_dir, "05_pdf_render_failed")
            result["error"] = "홈택스 PDF 렌더링 실패"
            return

        parsed = self._parse_invoice_from_xml_attachment(driver, dump_dir)
        if parsed:
            supplier_name = parsed["supplier_name"]
            buyer_name = parsed["buyer_name"]
            buyer_biz_no = parsed["buyer_biz_no"]
            issue_date = parsed["issue_date"] or mail_date
            item_name = parsed["item_name"] or "세금계산서"
            total_amount = parsed["total_amount"]
            supply_amount = parsed["supply_amount"]
            tax_amount = parsed["tax_amount"]
        else:
            self._dump_state(driver, dump_dir, "04_xml_parse_failed_no_fallback")
            result["error"] = f"홈택스 XML 파싱 실패: 임의 HTML 숫자 fallback 저장 차단 ({dump_dir})"
            return

        self._write_text(
            dump_dir / "04_parse_result.json",
            json.dumps(
                {
                    "source": "xml_attachment" if parsed else "page_source_fallback",
                    "supplier_name": supplier_name,
                    "buyer_name": buyer_name,
                    "buyer_biz_no": buyer_biz_no,
                    "issue_date": issue_date,
                    "item_name": item_name,
                    "supply_amount": supply_amount,
                    "tax_amount": tax_amount,
                    "total_amount": total_amount,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )

        final_name = self.build_pdf_filename(
            issue_date=issue_date,
            buyer=buyer_name or "사업장",
            supplier=supplier_name or "매입처",
            item=item_name,
            extra="",
            amount=str(total_amount),
            buyer_biz_no=buyer_biz_no,
        )
        final_path = self.dedupe_path(self.download_dir / final_name)
        time.sleep(1)
        temp_pdf.rename(final_path)
        self._write_text(dump_dir / "07_pdf_saved.txt", str(final_path))

        try:
            local_path = url.replace("file:///", "").replace("file://", "").replace("/", os.sep)
            if os.path.exists(local_path):
                os.remove(local_path)
        except Exception:
            pass

        amount_int = int(re.sub(r"[^\d]", "", str(total_amount)) or "0")
        supply_int = int(re.sub(r"[^\d]", "", str(supply_amount)) or "0")
        tax_int = int(re.sub(r"[^\d]", "", str(tax_amount)) or "0")
        if amount_int > 10_000_000_000:
            amount_int = 0
        if not amount_int and (supply_int or tax_int):
            amount_int = supply_int + tax_int
        result.update(
            {
                "ok": True,
                "pdf_path": str(final_path),
                "subject": f"[{buyer_name or '사업장'}] {supplier_name or '매입처'} 세금계산서({amount_int:,}원)",
                "data": {
                    "vendor_name": supplier_name or "",
                    "site_name": buyer_name or "",
                    "total_tax": tax_int,
                    "total_sum": amount_int,
                    "items": [
                        {
                            "name": item_name,
                            "qty": 1,
                            "inc_vat": amount_int or (supply_int + tax_int),
                            "account": "소모품비",
                        }
                    ],
                },
            }
        )

    def _parse_invoice_from_xml_attachment(self, driver, dump_dir: Path) -> dict | None:
        xml_path = self._download_xml_attachment(driver, dump_dir)
        if not xml_path:
            return None

        try:
            supplier, buyer, content = parse_tax_invoice_xml(str(xml_path))
            items = content.get("항목") or []
            first_item = items[0] if items else {}
            parsed = {
                "xml_path": str(xml_path),
                "supplier_name": supplier.get("상호") or "",
                "buyer_name": buyer.get("상호") or "",
                "buyer_biz_no": buyer.get("등록번호") or "",
                "issue_date": content.get("작성일자") or "",
                "item_name": first_item.get("품목") or content.get("비고") or "세금계산서",
                "supply_amount": content.get("공급가액") or first_item.get("공급가액") or "0",
                "tax_amount": content.get("세액") or first_item.get("세액") or "0",
                "total_amount": content.get("합계금액") or "0",
                "raw": {
                    "supplier": supplier,
                    "buyer": buyer,
                    "content": content,
                },
            }
            self._write_text(
                dump_dir / "04_xml_parse_result.json",
                json.dumps(parsed, ensure_ascii=False, indent=2),
            )
            return parsed
        except Exception as exc:
            self._write_text(dump_dir / "04_xml_parse_error.txt", repr(exc))
            return None

    def _download_xml_attachment(self, driver, dump_dir: Path) -> Path | None:
        before_files = self.snapshot(".xml")

        attempts = []
        try:
            direct = driver.execute_script(
                """
                if (typeof CriGetFileName !== 'function' || typeof CriGetFileData !== 'function') {
                    return null;
                }
                return {
                    name: CriGetFileName(0),
                    data: CriGetFileData(0)
                };
                """
            )
            if direct and direct.get("data"):
                raw_name = str(direct.get("name") or "hometax_attachment.xml")
                file_name = Path(raw_name).name or "hometax_attachment.xml"
                if not file_name.lower().endswith(".xml"):
                    file_name += ".xml"
                xml_path = dump_dir / file_name
                file_data = str(direct.get("data") or "")
                try:
                    xml_path.write_bytes(base64.b64decode(file_data))
                except Exception:
                    xml_path.write_text(file_data, encoding="utf-8", errors="replace")
                if xml_path.exists() and xml_path.stat().st_size > 0:
                    self._write_text(
                        dump_dir / "04_xml_download_success.txt",
                        f"direct_js={xml_path}",
                    )
                    return xml_path
            attempts.append("direct CriGetFileData(0): no data")
        except Exception as exc:
            attempts.append(f"direct CriGetFileData(0) failed: {exc!r}")

        try:
            if driver.execute_script("return typeof CriDownFile === 'function';"):
                driver.execute_script("CriDownFile(0);")
                attempts.append("CriDownFile(0)")
                downloaded = self.wait_new_file(".xml", before_files, timeout=12)
                if downloaded:
                    self._write_text(dump_dir / "04_xml_download_success.txt", str(downloaded))
                    return downloaded
        except Exception as exc:
            attempts.append(f"CriDownFile(0) failed: {exc!r}")

        for selector in (
            "a[onclick*='CriDownFile']",
            "button[onclick*='CriDownFile']",
            "input[onclick*='CriDownFile']",
        ):
            try:
                for elem in driver.find_elements(By.CSS_SELECTOR, selector):
                    onclick = elem.get_attribute("onclick") or ""
                    if "CriDownFile" not in onclick:
                        continue
                    driver.execute_script("arguments[0].click();", elem)
                    attempts.append(f"click {selector}: {onclick}")
                    downloaded = self.wait_new_file(".xml", before_files, timeout=12)
                    if downloaded:
                        self._write_text(dump_dir / "04_xml_download_success.txt", str(downloaded))
                        return downloaded
            except Exception as exc:
                attempts.append(f"{selector} failed: {exc!r}")

        self._write_text(
            dump_dir / "04_xml_download_failed.json",
            json.dumps({"attempts": attempts}, ensure_ascii=False, indent=2),
        )
        return None

    def _auth_secure_mail(self, driver, candidates: dict, dump_dir: Path) -> str | None:
        try:
            inp = WebDriverWait(driver, 6).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "input[type='text'], input[type='password'], input[type='number']")
                )
            )
        except Exception as exc:
            self._write_text(dump_dir / "01_auth_locator_error.txt", repr(exc))
            return None

        for name, no in candidates.items():
            try:
                inp.clear()
                inp.send_keys(no)
                btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[normalize-space()='확인'] | //input[@value='확인']")
                    )
                )
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)

                src = driver.page_source
                if "올바르지 않" in src or "일치하지 않" in src or "오류" in src:
                    self._write_text(
                        dump_dir / f"01_auth_fail_{name}.txt",
                        f"candidate={name}\nnumber={no}\n",
                    )
                    continue

                auth_inputs = [
                    elem
                    for elem in driver.find_elements(
                        By.CSS_SELECTOR, "input[type='text'], input[type='password'], input[type='number']"
                    )
                    if elem.is_displayed()
                ]
                if not auth_inputs:
                    return name
                inp = auth_inputs[0]
            except Exception as exc:
                self._write_text(
                    dump_dir / f"01_auth_exception_{name}.txt",
                    f"candidate={name}\nnumber={no}\nerror={exc!r}\n",
                )
                continue
        return None

    def _save_pdf_from_page(self, driver, output_path: Path, dump_dir: Path) -> bool:
        try:
            payload = driver.execute_cdp_cmd(
                "Page.printToPDF",
                {
                    "printBackground": True,
                    "paperWidth": 8.27,
                    "paperHeight": 11.69,
                    "marginTop": 0.2,
                    "marginBottom": 0.2,
                    "marginLeft": 0.2,
                    "marginRight": 0.2,
                    "preferCSSPageSize": True,
                },
            )
            import base64

            pdf_bytes = base64.b64decode(payload["data"])
            output_path.write_bytes(pdf_bytes)
            self._write_text(
                dump_dir / "05_pdf_render_success.json",
                json.dumps(
                    {
                        "size": len(pdf_bytes),
                        "output_path": str(output_path),
                        "title": driver.title,
                        "url": driver.current_url,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            return output_path.exists() and output_path.stat().st_size > 0
        except Exception as exc:
            self._write_text(dump_dir / "05_pdf_render_error.txt", repr(exc))
            return False

    def _iter_frames(self, driver: WebDriver):
        yield "default", driver
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for idx, frame in enumerate(frames):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                frame_name = frame.get_attribute("name") or frame.get_attribute("id") or f"frame_{idx}"
                yield frame_name, driver
            except Exception:
                driver.switch_to.default_content()
                continue

    def _make_debug_dir(self, mail_date: str) -> Path:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        dump_dir = self.download_dir / "_debug_hometax" / f"{mail_date or 'nodate'}_{stamp}"
        dump_dir.mkdir(parents=True, exist_ok=True)
        return dump_dir

    def _dump_state(self, driver, dump_dir: Path, label: str) -> None:
        try:
            driver.save_screenshot(str(dump_dir / f"{label}.png"))
        except Exception:
            pass
        try:
            self._write_text(dump_dir / f"{label}.html", driver.page_source)
        except Exception:
            pass
        try:
            summary = {
                "title": driver.title,
                "url": driver.current_url,
                "buttons": [],
                "frames": [],
            }
            for btn in driver.find_elements(By.CSS_SELECTOR, "button, a, input[type='button'], input[type='submit'], img"):
                try:
                    if not btn.is_displayed():
                        continue
                    txt = " ".join(
                        filter(
                            None,
                            [
                                (btn.text or "").strip(),
                                (btn.get_attribute("value") or "").strip(),
                                (btn.get_attribute("alt") or "").strip(),
                                (btn.get_attribute("title") or "").strip(),
                                (btn.get_attribute("onclick") or "").strip(),
                            ],
                        )
                    )
                    if txt:
                        summary["buttons"].append(txt)
                except Exception:
                    continue
            for idx, frame in enumerate(driver.find_elements(By.CSS_SELECTOR, "iframe, frame")):
                summary["frames"].append(
                    {
                        "index": idx,
                        "name": frame.get_attribute("name"),
                        "id": frame.get_attribute("id"),
                        "src": frame.get_attribute("src"),
                    }
                )
            self._write_text(
                dump_dir / f"{label}_summary.json",
                json.dumps(summary, ensure_ascii=False, indent=2),
            )
        except Exception:
            pass

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8", errors="replace")

    @staticmethod
    def _parse_field(html: str, keywords: list[str]) -> str:
        for kw in keywords:
            match = re.search(rf"{kw}[^가-힣A-Za-z()]*([가-힣A-Za-z(주)\s]{{2,25}})", html)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _parse_amount(html: str) -> int:
        nums = [
            int(n.replace(",", ""))
            for n in re.findall(r"[\d,]{6,15}", html)
            if 10000 < int(n.replace(",", "")) <= 10_000_000_000
        ]
        return max(nums) if nums else 0


if __name__ == "__main__":
    print("[홈택스 보안메일 단독 테스트]")
    path_str = input("파일 경로: ").strip().strip('"')
    p = Path(path_str)
    if not p.exists():
        print(f"파일 없음: {p}")
        raise SystemExit
    mail_text = input("메일 키워드[엔터=대승]: ").strip() or "대승"
    handler = HometaxHandler()
    res = handler.process(url=p.as_uri(), mail_text=mail_text, mail_date=time.strftime("%y%m%d"))
    print(f"\nok={res['ok']} | pdf={res.get('pdf_path')} | error={res.get('error')} | debug={res.get('debug_dir')}")
