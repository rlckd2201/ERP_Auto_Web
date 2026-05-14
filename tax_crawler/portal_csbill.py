import re
import time
import json
import base64
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_handler import BaseTaxInvoiceHandler
from xml_parser import parse_tax_invoice_xml


class CsbillHandler(BaseTaxInvoiceHandler):

    DOMAIN = "https://www.csbill.co.kr/"

    @property
    def portal_name(self) -> str:
        return "csbill"

    def supports(self, url: str) -> bool:
        return str(url or "").lower().startswith(self.DOMAIN)

    def _do_process(self, driver, url, mail_text, mail_date, result):
        candidates = self.build_candidate_nos(mail_text)
        dump_dir = self._make_debug_dir(mail_date)
        result["debug_dir"] = str(dump_dir)
        self._write_text(
            dump_dir / "00_candidates.json",
            json.dumps(
                {"mail_text": mail_text, "candidates": candidates, "url": url},
                ensure_ascii=False,
                indent=2,
            ),
        )

        if not candidates:
            result["error"] = "CSBill 법인 후보를 찾지 못했습니다."
            return

        driver.get(url)
        time.sleep(3)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])

        self._dump_state(driver, dump_dir, "01_before_auth")

        matched = self._auth_biz_modal(driver, candidates, dump_dir)
        if not matched:
            self._dump_state(driver, dump_dir, "02_auth_failed")
            result["error"] = "CSBill 사업자번호 인증에 실패했습니다."
            return

        self._write_text(dump_dir / "02_auth_result.txt", f"matched={matched}\n")
        time.sleep(2)
        self._dump_state(driver, dump_dir, "03_after_auth")

        parsed = self._parse_invoice_from_xml_download(driver, dump_dir)
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
            frame_text = self._visible_invoice_text(driver, dump_dir)
            src = "\n".join([driver.page_source, frame_text])
            if "정보가 올바르지 않습니다" in src:
                self._write_text(dump_dir / "04_invalid_page.txt", src[:2000])
                result["error"] = "CSBill 오류 페이지 감지: 정보가 올바르지 않습니다."
                return
            supplier_name = self._parse_field(src, ["공급자", "상호", "사업자명"])
            buyer_name = self._parse_field(src, ["공급받는자", "수신자"])
            buyer_biz_no = candidates.get(matched, "")
            issue_date = mail_date
            item_name = self._parse_item_name(src) or "세금계산서"
            total_amount = self._parse_amount(src)
            supply_amount = total_amount
            tax_amount = 0

        self._write_text(
            dump_dir / "04_parse_result.json",
            json.dumps(
                {
                    "source": "xml_download" if parsed else "visible_text_fallback",
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

        temp_pdf = dump_dir / "05_rendered_invoice.pdf"
        if not self._render_bill_print_pdf(driver, temp_pdf, dump_dir):
            self._dump_state(driver, dump_dir, "06_pdf_not_created")
            result["error"] = "CSBill PDF 렌더링 실패"
            return

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

        amount_int = int(re.sub(r"[^\d]", "", str(total_amount)) or "0")
        supply_int = int(re.sub(r"[^\d]", "", str(supply_amount)) or "0")
        tax_int = int(re.sub(r"[^\d]", "", str(tax_amount)) or "0")
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

    def _parse_invoice_from_xml_download(self, driver, dump_dir: Path) -> dict | None:
        xml_path = self._download_xml(driver, dump_dir)
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

    def _snapshot_xml_state(self) -> dict[str, tuple[int, int]]:
        state: dict[str, tuple[int, int]] = {}
        for path in self.download_dir.glob("*.xml"):
            try:
                stat = path.stat()
                state[str(path.resolve())] = (stat.st_mtime_ns, stat.st_size)
            except Exception:
                continue
        return state

    def _wait_xml_change(self, before_state: dict[str, tuple[int, int]], timeout: int = 12) -> Path | None:
        end_at = time.time() + timeout
        while time.time() < end_at:
            for path in self.download_dir.glob("*.xml"):
                try:
                    stat = path.stat()
                    key = str(path.resolve())
                    current = (stat.st_mtime_ns, stat.st_size)
                except Exception:
                    continue
                if key not in before_state or before_state.get(key) != current:
                    if self._is_stable(path):
                        return path
            time.sleep(0.5)
        return None

    def _execute_in_default_and_frames(self, driver, script: str) -> list[str]:
        results: list[str] = []
        try:
            driver.switch_to.default_content()
            driver.execute_script(script)
            results.append("default")
        except Exception as exc:
            results.append(f"default failed: {exc!r}")

        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for idx, frame in enumerate(frames):
            try:
                driver.switch_to.default_content()
                name = frame.get_attribute("name") or frame.get_attribute("id") or f"frame_{idx}"
                driver.switch_to.frame(frame)
                driver.execute_script(script)
                results.append(name)
            except Exception as exc:
                results.append(f"frame_{idx} failed: {exc!r}")
        driver.switch_to.default_content()
        return results

    def _download_xml(self, driver, dump_dir: Path) -> Path | None:
        before_state = self._snapshot_xml_state()
        attempts = []

        scripts = [
            "goSave(document.billForm, 'save', '/download.do', 'tmpFrm2');",
            "goSave(billForm, 'save', '/download.do', 'tmpFrm2');",
        ]
        for script in scripts:
            try:
                contexts = self._execute_in_default_and_frames(driver, script)
                attempts.append(f"{script} | contexts={contexts}")
                downloaded = self._wait_xml_change(before_state, timeout=12)
                if downloaded:
                    self._write_text(dump_dir / "04_xml_download_success.txt", str(downloaded))
                    return downloaded
            except Exception as exc:
                attempts.append(f"{script} failed: {exc!r}")

        self._write_text(
            dump_dir / "04_xml_download_failed.json",
            json.dumps({"attempts": attempts}, ensure_ascii=False, indent=2),
        )
        return None

    def _auth_biz_modal(self, driver, candidates: dict, dump_dir: Path) -> str | None:
        try:
            inp = WebDriverWait(driver, 8).until(
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
                confirm = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[normalize-space()='확인'] | //input[@value='확인'] | //a[normalize-space()='확인']")
                    )
                )
                driver.execute_script("arguments[0].click();", confirm)
                time.sleep(2)

                still = [
                    elem
                    for elem in driver.find_elements(
                        By.CSS_SELECTOR, "input[type='text'], input[type='password'], input[type='number']"
                    )
                    if elem.is_displayed()
                ]
                if not still:
                    return name

                visible_text = " ".join(
                    el.text.strip()
                    for el in driver.find_elements(By.XPATH, "//*[not(self::script) and not(self::style)]")
                    if el.is_displayed()
                )
                if "올바르지 않" in visible_text or "일치하지 않" in visible_text or "오류" in visible_text:
                    self._write_text(
                        dump_dir / f"01_auth_fail_{name}.txt",
                        f"candidate={name}\nnumber={no}\nvisible_text={visible_text[:500]}\n",
                    )
                    inp = still[0]
                    continue

                inp = still[0]
            except Exception as exc:
                self._write_text(
                    dump_dir / f"01_auth_exception_{name}.txt",
                    f"candidate={name}\nnumber={no}\nerror={exc!r}\n",
                )
                continue

        return None

    def _render_bill_print_pdf(self, driver, output_path: Path, dump_dir: Path) -> bool:
        original = driver.current_url
        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": '''
                        window.print = function(){ console.log("window.print blocked by CSBill handler"); };
                        window.close = function(){ console.log("window.close blocked by CSBill handler"); };
                    '''
                },
            )
            frame_src = ""
            for frame in driver.find_elements(By.CSS_SELECTOR, "iframe, frame"):
                name = frame.get_attribute("name") or frame.get_attribute("id") or ""
                src = frame.get_attribute("src") or ""
                if name == "fraView" or "taxInvoiceHTMLNoActive.do" in src:
                    frame_src = src
                    break

            if frame_src:
                sep = "&" if "?" in frame_src else "?"
                driver.get(frame_src + sep + "printYn=Y&pre_Url=noRegIssueList.do")
                WebDriverWait(driver, 10).until(lambda d: "taxInvoiceHTMLNoActive.do" in (d.current_url or ""))
            else:
                driver.execute_script(
                    '''
                    var f = document.forms['billForm'];
                    if (!f) { throw new Error('billForm not found'); }
                    f.target = '_self';
                    f.action = '/billPrint.do';
                    f.submit();
                    '''
                )
                WebDriverWait(driver, 10).until(lambda d: "billPrint.do" in (d.current_url or ""))
            time.sleep(2)
            self._dump_state(driver, dump_dir, "05_billprint_page")
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
            pdf_bytes = base64.b64decode(payload["data"])
            output_path.write_bytes(pdf_bytes)
            self._write_text(
                dump_dir / "06_pdf_render_success.json",
                json.dumps(
                    {
                        "billprint_url": driver.current_url,
                        "size": len(pdf_bytes),
                        "output_path": str(output_path),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            return output_path.exists() and output_path.stat().st_size > 0
        except Exception as exc:
            self._write_text(dump_dir / "06_pdf_render_error.txt", repr(exc))
            return False
        finally:
            try:
                driver.get(original)
                time.sleep(1)
            except Exception:
                pass

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

    def _visible_invoice_text(self, driver, dump_dir: Path) -> str:
        chunks = []
        try:
            for frame_name, frame_driver in self._iter_frames(driver):
                try:
                    text = frame_driver.find_element(By.TAG_NAME, "body").text
                    if text.strip():
                        chunks.append(f"[{frame_name}]\n{text}")
                except Exception as exc:
                    chunks.append(f"[{frame_name} error] {exc!r}")
            driver.switch_to.default_content()
        except Exception as exc:
            chunks.append(f"[frame iteration error] {exc!r}")
        text = "\n\n".join(chunks)
        self._write_text(dump_dir / "04_visible_invoice_text.txt", text)
        return text

    def _make_debug_dir(self, mail_date: str) -> Path:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        dump_dir = self.download_dir / "_debug_csbill" / f"{mail_date or 'nodate'}_{stamp}"
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
            if int(n.replace(",", "")) > 10000
        ]
        return max(nums) if nums else 0

    @staticmethod
    def _parse_item_name(text: str) -> str:
        clean = re.sub(r"\s+", " ", str(text or ""))
        match = re.search(r"\b\d{2}\s+\d{2}\s+(.+?)\s+\d+\s+[\d,]+\s+[\d,]+\s+[\d,]+", clean)
        if match:
            return match.group(1).strip()
        return ""


if __name__ == "__main__":
    print("[CSBill 단독 테스트]")
    url = input("URL: ").strip()
    mail_text = input("메일 키워드[엔터=대승]: ").strip() or "대승"
    handler = CsbillHandler()
    res = handler.process(url=url, mail_text=mail_text, mail_date=time.strftime("%y%m%d"))
    print(f"\nok={res['ok']} | pdf={res.get('pdf_path')} | error={res.get('error')} | debug={res.get('debug_dir')}")
