"""
WEHAGO (더존비즈온) 세금계산서 핸들러
대상: www.wehago.com/invoice/#/eTaxMail/...
메일 수신 업체: Acronis, Watching-On

인증 방식:
  - URL의 Base64 토큰에 사업자번호가 인코딩됨 → 디코딩하면 1번 트라이로 인증 완료
    예: VFgyMDI2MDQ2OTQ5MjI3JjEyNTgxMDU2MTk= → TX2026046949227&1258105619
  - 페이지 로드 후 visible text input 중 마지막이 사업자번호 모달 입력창
  - 확인 버튼 클릭 후 visible inputs 수가 줄면 인증 성공
인증 후 버튼:
  - [XML]  → XML 다운로드 (공급자/수신자/금액 정확히 파싱 가능)
  - [인쇄] → PDF 자동 다운로드 (class=WSC_LUXButton)
"""
import base64
import hashlib
import re
import shutil
import subprocess
import time
import winreg
from pathlib import Path

import pyautogui
from pywinauto import Desktop
from pywinauto.findwindows import ElementNotFoundError
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_handler import BaseTaxInvoiceHandler
from xml_parser import parse_tax_invoice_xml


class WehagoHandler(BaseTaxInvoiceHandler):

    DOMAIN = "wehago.com"
    INVOICE_PREFIX = "https://www.wehago.com/invoice/"

    @property
    def portal_name(self) -> str:
        return "wehago"

    def supports(self, url: str) -> bool:
        return str(url or "").lower().startswith(self.INVOICE_PREFIX)

    def _prepare_browser_environment(self) -> None:
        """Allow Chrome to reach WEHAGO's local Duzon print agents."""
        policy_path = r"Software\Policies\Google\Chrome"
        policy_names = (
            "LocalNetworkAccessAllowedForUrls",
            "LocalNetworkAllowedForUrls",
            "LoopbackNetworkAllowedForUrls",
        )
        for policy_name in policy_names:
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                rf"{policy_path}\{policy_name}",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(
                    key,
                    "1",
                    0,
                    winreg.REG_SZ,
                    "https://www.wehago.com",
                )

        # Chrome 142~152 blocks local/loopback requests unless the LNA
        # permission has already been granted.  The allowlists above are the
        # long-term setting; the temporary opt-out covers Chrome builds where
        # that permission prompt is still shown before the per-origin policy
        # takes effect.  This is scoped to Chrome's documented enterprise LNA
        # policy and disappears automatically after the transition period.
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            policy_path,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(
                key,
                "LocalNetworkAccessRestrictionsTemporaryOptOut",
                0,
                winreg.REG_DWORD,
                1,
            )

    def _do_process(self, driver, url, mail_text, mail_date, result):
        # URL Base64 디코딩 우선 → 실패 시 메일 본문 키워드 매칭
        candidates = self._candidates_from_url(url) or self.build_candidate_nos(mail_text)
        if not candidates:
            result["error"] = "WEHAGO 법인명 식별 실패 (mail_text에 법인명 포함 필요)"
            return

        self._grant_local_print_permissions(driver)
        driver.get(url)
        time.sleep(5)  # SPA 렌더링 대기

        matched = self._auth_modal(driver, candidates)
        if not matched:
            result["error"] = "WEHAGO 사업자번호 인증 실패"
            return

        time.sleep(2)
        self._dismiss_notice_dialog(driver)

        # XML 다운로드 → 정확한 거래처/금액 파싱
        supplier_name, buyer_name, buyer_biz_no = "", "", ""
        issue_date = mail_date
        total_amount = 0
        tax_amount = 0
        supply_amount = 0
        items_raw = []
        metadata_from_xml = False
        xml_snap = self.snapshot(".xml")
        if self._click_xml(driver):
            xml_file = self.wait_new_file(".xml", xml_snap, timeout=10)
            if xml_file:
                try:
                    supplier, buyer, content = parse_tax_invoice_xml(str(xml_file))
                    supplier_name = supplier.get("상호", "")
                    buyer_name    = buyer.get("상호", "")
                    buyer_biz_no  = buyer.get("등록번호", "")
                    issue_date    = content.get("작성일자") or mail_date
                    supply_amount = self._to_int(content.get("공급가액", "0"))
                    tax_amount    = self._to_int(content.get("세액", "0"))
                    total_amount  = self._to_int(content.get("합계금액", "0"))
                    items_raw     = content.get("항목", [])
                    metadata_from_xml = bool(supplier_name and buyer_name)
                    xml_file.unlink()
                except Exception:
                    xml_file.unlink() if xml_file.exists() else None

        # XML 실패 시 페이지 소스에서 추출
        if not supplier_name:
            src = driver.page_source
            supplier_name = self._parse_field(src, ["공급자", "발급업무대행사"])
            buyer_name    = self._parse_field(src, ["공급받는자"])
            total_amount  = self._parse_amount(src)
            items_raw     = []

        items = [
            {
                "name": it.get("품목", ""),
                "qty": 1,
                "inc_vat": self._to_int(it.get("공급가액", "0")) + self._to_int(it.get("세액", "0")),
                "account": "소모품비",
            }
            for it in items_raw
        ] or [{"name": "세금계산서", "qty": 1, "inc_vat": total_amount, "account": "소모품비"}]

        first_item = items_raw[0].get("품목", "세금계산서") if items_raw else "세금계산서"
        extra = f"_외{len(items_raw)-1}건" if len(items_raw) > 1 else ""

        final_name = self.build_pdf_filename(
            issue_date=issue_date,
            buyer=buyer_name or "사업장미상",
            supplier=supplier_name or "매입처",
            item=first_item,
            extra=extra,
            amount=str(total_amount),
            buyer_biz_no=buyer_biz_no,
        )
        source_document_id = self._document_id_from_url(url)
        base_final_path = self.download_dir / final_name
        final_path = base_final_path.with_name(
            f"{base_final_path.stem}__WEHAGO_{source_document_id}{base_final_path.suffix}"
        )

        # A failed Seen-flag update or forwarded duplicate must not reopen the
        # external print helper for a PDF that is already stored.
        existing_pdf = self._existing_invoice_pdf(final_path, base_final_path)
        if existing_pdf:
            if not metadata_from_xml:
                recovered = self._parse_saved_pdf_metadata(existing_pdf)
                if recovered:
                    supplier_name = recovered.get("supplier_name") or supplier_name
                    buyer_name = recovered.get("buyer_name") or buyer_name
                    buyer_biz_no = recovered.get("buyer_biz_no") or buyer_biz_no
                    issue_date = recovered.get("issue_date") or issue_date
                    supply_amount = recovered.get("supply_amount") or supply_amount
                    tax_amount = recovered.get("tax_amount") or tax_amount
                    total_amount = recovered.get("total_amount") or total_amount
                    recovered_item = recovered.get("item_name") or "세금계산서"
                    items = [{
                        "name": recovered_item,
                        "qty": 1,
                        "inc_vat": total_amount,
                        "account": "소모품비",
                    }]
                    corrected_name = self.build_pdf_filename(
                        issue_date=issue_date,
                        buyer=buyer_name or "사업장미상",
                        supplier=supplier_name or "매입처",
                        item=recovered_item,
                        extra="",
                        amount=str(total_amount),
                        buyer_biz_no=buyer_biz_no,
                    )
                    corrected_base = self.download_dir / corrected_name
                    corrected_path = corrected_base.with_name(
                        f"{corrected_base.stem}__WEHAGO_{source_document_id}{corrected_base.suffix}"
                    )
                    existing_pdf = self._rename_saved_pdf(existing_pdf, corrected_path)
            result.update({
                "ok": True,
                "pdf_path": str(existing_pdf),
                "subject": f"[{buyer_name or '사업장미상'}] {supplier_name or '매입처'} 세금계산서 ({total_amount:,}원)",
                "source_document_id": source_document_id,
                "data": {
                    "vendor_name": supplier_name or "",
                    "site_name": buyer_name or "",
                    "total_tax": tax_amount,
                    "total_sum": total_amount,
                    "items": items,
                },
            })
            return

        # 인쇄 버튼 → 더존 미리보기 → 네이티브 세금계산서 PDF 저장.
        # Chrome Page.printToPDF는 WEHAGO 웹 화면 전체를 저장하므로 계산서로
        # 인정하지 않는다. 네이티브 출력이 실패하면 메일을 재시도할 수 있도록
        # 명시적으로 실패를 반환한다.
        pdf_file, native_detail = self._export_native_pdf_with_retry(
            driver,
            final_path,
            attempts=2,
        )
        if not pdf_file:
            result["error"] = (
                "WEHAGO 네이티브 PDF 출력 실패: "
                f"{native_detail or '더존 전용 인쇄 PDF를 생성하지 못했습니다'}"
            )
            return

        if not metadata_from_xml:
            recovered = self._parse_saved_pdf_metadata(pdf_file)
            if recovered:
                supplier_name = recovered.get("supplier_name") or supplier_name
                buyer_name = recovered.get("buyer_name") or buyer_name
                buyer_biz_no = recovered.get("buyer_biz_no") or buyer_biz_no
                issue_date = recovered.get("issue_date") or issue_date
                supply_amount = recovered.get("supply_amount") or supply_amount
                tax_amount = recovered.get("tax_amount") or tax_amount
                total_amount = recovered.get("total_amount") or total_amount
                recovered_item = recovered.get("item_name") or "세금계산서"
                items = [{
                    "name": recovered_item,
                    "qty": 1,
                    "inc_vat": total_amount,
                    "account": "소모품비",
                }]
                corrected_name = self.build_pdf_filename(
                    issue_date=issue_date,
                    buyer=buyer_name or "사업장미상",
                    supplier=supplier_name or "매입처",
                    item=recovered_item,
                    extra="",
                    amount=str(total_amount),
                    buyer_biz_no=buyer_biz_no,
                )
                corrected_base = self.download_dir / corrected_name
                corrected_path = corrected_base.with_name(
                    f"{corrected_base.stem}__WEHAGO_{source_document_id}{corrected_base.suffix}"
                )
                pdf_file = self._rename_saved_pdf(pdf_file, corrected_path)

        result.update({
            "ok": True,
            "pdf_path": str(pdf_file),
            "source_document_id": source_document_id,
            "subject": f"[{buyer_name or '사업장미상'}] {supplier_name or '매입처'} 세금계산서 ({total_amount:,}원)",
            "data": {
                "vendor_name": supplier_name or "",
                "site_name":   buyer_name or "",
                "total_tax":   tax_amount,
                "total_sum":   total_amount,
                "items":       items,
            },
        })

    @staticmethod
    def _grant_local_print_permissions(driver) -> None:
        """Allow WEHAGO to call its local BMS/Duzon print agents on Chrome 142+."""
        origin = "https://www.wehago.com"
        for permission_name in (
            "localNetworkAccess",
            "localNetwork",
            "loopbackNetwork",
        ):
            try:
                driver.execute_cdp_cmd(
                    "Browser.setPermission",
                    {
                        "permission": {"name": permission_name},
                        "setting": "granted",
                        "origin": origin,
                    },
                )
            except Exception:
                # Chrome versions before split LNA permissions may reject one
                # of the newer names. Grant every name supported by that build.
                continue

    # ------------------------------------------------------------------
    @staticmethod
    def _document_id_from_url(url: str) -> str:
        """Return WEHAGO's stable tax-invoice token, with a URL hash fallback."""
        raw_url = str(url or "").strip()
        try:
            token = raw_url.rstrip("/").split("/")[-1]
            padded = token + "=" * (-len(token) % 4)
            decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
            match = re.search(r"\b(TX[A-Za-z0-9_-]{6,})\b", decoded, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        except Exception:
            pass
        return "URL" + hashlib.sha1(raw_url.encode("utf-8", errors="ignore")).hexdigest()[:16].upper()

    def _existing_invoice_pdf(self, canonical_path: Path, legacy_path: Path) -> Path | None:
        candidates = [canonical_path, legacy_path]
        try:
            document_suffix = canonical_path.stem.rsplit("__WEHAGO_", 1)[-1]
            if document_suffix and document_suffix != canonical_path.stem:
                candidates.extend(self.download_dir.glob(f"*__WEHAGO_{document_suffix}.pdf"))
            candidates.extend(
                sorted(
                    legacy_path.parent.glob(f"{legacy_path.stem}_*.pdf"),
                    key=lambda path: path.stat().st_mtime if path.exists() else 0,
                    reverse=True,
                )
            )
        except Exception:
            pass
        for path in candidates:
            try:
                if not (
                    path.exists()
                    and path.is_file()
                    and self._is_stable(path, interval=0.2)
                ):
                    continue
                valid, reason = self._is_native_wehago_pdf(path)
                if valid:
                    return path
                self._last_existing_pdf_rejection = f"{path.name}: {reason}"
            except Exception:
                continue
        return None

    @staticmethod
    def _rename_saved_pdf(source_path: Path, target_path: Path) -> Path:
        try:
            source_path = Path(source_path)
            target_path = Path(target_path)
            if source_path.resolve() == target_path.resolve():
                return source_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if target_path.exists() and target_path.stat().st_size > 0:
                return target_path
            source_path.replace(target_path)
            return target_path
        except Exception:
            return Path(source_path)

    @staticmethod
    def _assess_native_wehago_pdf(metadata: dict, text: str) -> tuple[bool, str]:
        """Classify a WEHAGO PDF without accepting a browser-printed web page."""
        metadata = metadata if isinstance(metadata, dict) else {}
        producer = str(metadata.get("Producer") or metadata.get("producer") or "").strip()
        creator = str(metadata.get("Creator") or metadata.get("creator") or "").strip()
        producer_key = producer.lower()
        creator_key = creator.lower()
        compact = re.sub(r"\s+", "", str(text or ""))

        if "skia/pdf" in producer_key or "chrome" in creator_key:
            return False, f"Chrome 웹 화면 PDF 감지 (producer={producer or '-'}, creator={creator or '-'})"

        browser_markers = (
            "상태확인",
            "국세청전송일자",
            "신고상태전송성공",
            "[확인]버튼",
        )
        if sum(marker in compact for marker in browser_markers) >= 2:
            return False, "WEHAGO 상태/확인 웹 화면이 포함된 PDF"

        if not (
            "developer express" in producer_key
            or "dxperience" in producer_key
        ):
            return False, f"더존 네이티브 PDF 생성기 불일치 (producer={producer or '-'})"

        required_markers = (
            "전자세금계산서",
            "공급받는자보관용",
            "작성일자",
            "공급가액",
            "세액",
            "승인번호",
            "관리번호",
        )
        missing = [marker for marker in required_markers if marker not in compact]
        if missing:
            return False, f"세금계산서 필수 표식 누락: {', '.join(missing)}"
        return True, f"더존 네이티브 PDF 확인 (producer={producer})"

    @classmethod
    def _is_native_wehago_pdf(cls, pdf_path: Path) -> tuple[bool, str]:
        try:
            import pdfplumber

            with pdfplumber.open(str(pdf_path)) as pdf:
                metadata = dict(pdf.metadata or {})
                text = "\n".join((page.extract_text() or "") for page in pdf.pages)
        except Exception as exc:
            return False, f"PDF 파싱 실패: {exc!r}"
        return cls._assess_native_wehago_pdf(metadata, text)

    def _quarantine_rejected_wehago_pdf(self, pdf_path: Path, reason: str) -> Path | None:
        """Preserve a rejected web-page PDF while clearing the canonical target."""
        path = Path(pdf_path)
        try:
            if not path.exists() or not path.is_file():
                return None
            stamp = time.strftime("%Y%m%d_%H%M%S")
            target = path.with_name(
                f"{path.stem}__REJECTED_NON_NATIVE_{stamp}{path.suffix}"
            )
            sequence = 1
            while target.exists():
                target = path.with_name(
                    f"{path.stem}__REJECTED_NON_NATIVE_{stamp}_{sequence}{path.suffix}"
                )
                sequence += 1
            path.replace(target)
            self._write_saveas_debug(
                target,
                f"rejected_non_native_pdf source={path.name} reason={reason}",
            )
            return target
        except Exception as exc:
            self._write_saveas_debug(
                path,
                f"rejected_non_native_pdf_quarantine_failed reason={reason} error={exc!r}",
            )
            return None

    def _export_native_pdf_with_retry(
        self,
        driver,
        final_path: Path,
        attempts: int = 2,
    ) -> tuple[Path | None, str]:
        """Export and validate only the native Duzon/WEHAGO invoice PDF."""
        errors = []
        final_path = Path(final_path)

        if final_path.exists():
            valid, reason = self._is_native_wehago_pdf(final_path)
            if valid:
                return final_path, reason
            rejected = self._quarantine_rejected_wehago_pdf(final_path, reason)
            if rejected:
                errors.append(f"기존 비정상 PDF 격리: {rejected.name} ({reason})")
            else:
                errors.append(f"기존 비정상 PDF 감지: {reason}")

        total_attempts = max(1, int(attempts or 1))
        for attempt in range(1, total_attempts + 1):
            self._close_all_print_dialogs()
            if attempt > 1:
                # The WEHAGO updater can need tens of seconds before the
                # interactive print runtime is ready.  Killing it between
                # retries creates an endless updater/restart loop.
                self._ensure_wehago_print_runtime()
                time.sleep(1.0)

            if not self._click_print(driver):
                detail = str(getattr(self, "_last_print_click_detail", "") or "").strip()
                errors.append(f"{attempt}차 인쇄 미리보기 실행 실패{': ' + detail if detail else ''}")
                continue

            candidate = self._export_pdf_from_print_dialog(final_path, timeout=30)
            if not candidate:
                detail = str(getattr(self, "_last_pdf_export_error", "") or "").strip()
                errors.append(f"{attempt}차 네이티브 저장 실패{': ' + detail if detail else ''}")
                continue

            valid, reason = self._is_native_wehago_pdf(candidate)
            if valid:
                return Path(candidate), reason

            rejected = self._quarantine_rejected_wehago_pdf(candidate, reason)
            if rejected:
                errors.append(f"{attempt}차 비정상 PDF 격리: {rejected.name} ({reason})")
            else:
                errors.append(f"{attempt}차 비정상 PDF 거부: {reason}")

        errors.append("Chrome 웹 화면 PDF 대체 저장은 차단되었습니다")
        return None, " / ".join(errors[-6:])

    @staticmethod
    def _parse_saved_pdf_metadata(pdf_path: Path) -> dict:
        """Recover invoice metadata from the generated PDF when XML download fails."""
        try:
            import pdfplumber

            with pdfplumber.open(str(pdf_path)) as pdf:
                text = "\n".join((page.extract_text() or "") for page in pdf.pages)
        except Exception:
            return {}

        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
        merged = "\n".join(lines)
        recovered = {}

        for line in lines:
            if "상 호" not in line or line.count("성명") < 2:
                continue
            match = re.search(
                r"상\s*호\s+(.+?)\s+성명\s+.+?\s+상\s*호\s+(.+?)\s+성명(?:\s|$)",
                line,
            )
            if match:
                recovered["supplier_name"] = match.group(1).strip()
                recovered["buyer_name"] = match.group(2).strip()
                break

        biz_match = re.search(
            r"등록번호\s+([0-9-]{10,12}).*?등록번호\s+([0-9-]{10,12})",
            merged,
            re.DOTALL,
        )
        if biz_match:
            recovered["supplier_biz_no"] = biz_match.group(1)
            recovered["buyer_biz_no"] = biz_match.group(2)

        date_amount_match = re.search(
            r"작성일자\s+공급가액\s+세액\s+"
            r"(\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+([\d,]+)\s+([\d,]+)",
            merged,
        )
        if date_amount_match:
            year, month, day = date_amount_match.group(1, 2, 3)
            supply_amount = int(date_amount_match.group(4).replace(",", ""))
            tax_amount = int(date_amount_match.group(5).replace(",", ""))
            recovered.update({
                "issue_date": f"{int(year):04d}/{int(month):02d}/{int(day):02d}",
                "supply_amount": supply_amount,
                "tax_amount": tax_amount,
                "total_amount": supply_amount + tax_amount,
            })

        for line in lines:
            item_match = re.match(
                r"^\d{1,2}\s+\d{1,2}\s+(.+?)\s+\S+\s+"
                r"[\d,.]+\s+[\d,]+\s+[\d,]+\s+[\d,]+(?:\s|$)",
                line,
            )
            if item_match:
                recovered["item_name"] = item_match.group(1).strip()
                break

        return recovered

    # ------------------------------------------------------------------
    @staticmethod
    def _candidates_from_url(url: str) -> dict[str, str] | None:
        """
        WEHAGO URL의 Base64 토큰에서 사업자번호(10자리) 추출.
        예: .../eTaxMail/VFgyMDI2MDQ2OTQ5MjI3JjEyNTgxMDU2MTk=
            → TX2026046949227&1258105619 → {"url_0": "1258105619"}
        성공하면 1번만 트라이하면 됨.
        """
        try:
            token = url.rstrip("/").split("/")[-1]
            padded = token + "=" * (-len(token) % 4)
            decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
            parts = [p.strip() for p in decoded.split("&") if p.strip()]
            if parts:
                tail = parts[-1]
                m = re.search(r"(\d{10})$", tail)
                if m:
                    return {"url_0": m.group(1)}
            nos = re.findall(r"\d{10}", decoded)
            if nos:
                return {"url_0": nos[-1]}
        except Exception:
            pass
        return None

    def _auth_modal(self, driver, candidates: dict) -> str | None:
        """
        visible text input 중 마지막 = 모달 입력창.
        확인 클릭 후 visible inputs 수가 줄면 인증 성공.
        """
        visible = [i for i in driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                   if i.is_displayed()]
        if not visible:
            return "no_modal"

        modal_inp = visible[-1]
        before_count = len(visible)

        for name, no in candidates.items():
            try:
                modal_inp.clear()
                modal_inp.send_keys(no)
                time.sleep(0.3)

                confirm = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='확인']"))
                )
                driver.execute_script("arguments[0].click();", confirm)
                time.sleep(2)
                if self._is_invoice_view_ready(driver):
                    return name

                after = [i for i in driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                         if i.is_displayed()]
                if len(after) < before_count:
                    return name  # 모달 사라짐 = 인증 성공

                if self._is_invoice_view_ready(driver):
                    return name

                # 실패: 다음 번호를 위해 입력창 갱신
                modal_inp = after[-1] if after else modal_inp

            except Exception:
                continue

        return None

    def _is_invoice_view_ready(self, driver) -> bool:
        try:
            elems = driver.find_elements(By.XPATH, "//*[self::button or self::a or self::span]")
            texts = [(elem.text or "").strip() for elem in elems if elem.is_displayed()]
            if any("XML" in text.upper() for text in texts):
                return True
            if any("인쇄" in text or "출력" in text or "전자세금계산서" in text for text in texts):
                return True
            return False
        except Exception:
            return False

    def _dismiss_notice_dialog(self, driver) -> None:
        for _ in range(4):
            accepted = self._accept_alert(driver, timeout=1)
            clicked = self._click_confirm_button(driver, timeout=2, reverse=True)
            if not accepted and not clicked:
                break
            time.sleep(1.0)

    def _accept_alert(self, driver, timeout: int = 1) -> bool:
        try:
            WebDriverWait(driver, timeout).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
            return True
        except Exception:
            return False

    def _click_confirm_button(self, driver, timeout: int = 3, reverse: bool = True) -> bool:
        selectors = [
            (By.CSS_SELECTOR, "button#confirm"),
            (By.XPATH, "//button[normalize-space()='확인' or contains(normalize-space(.),'확인')]"),
            (By.XPATH, "//a[normalize-space()='확인' or contains(normalize-space(.),'확인')]"),
            (By.XPATH, "//*[self::button or self::a or self::span or self::div][contains(@value,'확인') or contains(@title,'확인')]"),
        ]
        deadline = time.time() + timeout

        def try_current_context() -> bool:
            for by, sel in selectors:
                try:
                    elems = driver.find_elements(by, sel)
                    if reverse:
                        elems = list(reversed(elems))
                    for elem in elems:
                        try:
                            if not elem.is_displayed():
                                continue
                            driver.execute_script("arguments[0].click();", elem)
                            return True
                        except Exception:
                            continue
                except Exception:
                    continue
            return False

        while time.time() < deadline:
            try:
                driver.switch_to.default_content()
                if try_current_context():
                    return True
                frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
                for frame in frames:
                    try:
                        driver.switch_to.default_content()
                        driver.switch_to.frame(frame)
                        if try_current_context():
                            driver.switch_to.default_content()
                            return True
                    except Exception:
                        driver.switch_to.default_content()
                driver.switch_to.default_content()
            except Exception:
                pass
            time.sleep(0.3)
        return False

    def _click_xml(self, driver) -> bool:
        try:
            btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='XML']"))
            )
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)
            return True
        except Exception:
            return False

    def _click_print(self, driver) -> bool:
        self._last_print_click_detail = ""

        runtime = self._ensure_wehago_print_runtime()
        runtime_detail = str(runtime.get("detail") or "").strip()
        if runtime_detail:
            self._last_print_click_detail = runtime_detail

        agent_probe = self._probe_local_print_agent(driver)
        if not agent_probe.get("reachable"):
            reason = str(agent_probe.get("error") or "connection failed").strip()
            self._last_print_click_detail += (
                " / " if self._last_print_click_detail else ""
            ) + (
                "WEHAGO local print agent unavailable"
                f" ({reason[:180]})"
            )
            return False

        probe_status = agent_probe.get("status")
        self._last_print_click_detail += (
            " / " if self._last_print_click_detail else ""
        ) + (
            "WEHAGO local print agent reachable"
            f" (HTTP {probe_status})"
        )
        selectors_print = [
            "//button[normalize-space()='인쇄' or normalize-space()='출력']",
            "//a[normalize-space()='인쇄' or normalize-space()='출력']",
            "//span[normalize-space()='인쇄' or normalize-space()='출력']",
            "//*[@role='button' and (normalize-space()='인쇄' or normalize-space()='출력')]",
            "//*[contains(concat(' ', normalize-space(@class), ' '), ' WSC_LUXButton ') and "
            "(normalize-space()='인쇄' or normalize-space()='출력')]",
            "//*[self::input or self::img][contains(@title, '인쇄') or contains(@alt, '인쇄') "
            "or contains(@value, '인쇄')]",
        ]
        selectors_confirm = [
            "//button[contains(.,'확인')]",
            "//a[contains(.,'확인')]",
            "//span[contains(.,'확인')]",
            "//*[contains(@value, '확인')]",
        ]
        windows_before = len(driver.window_handles)

        def click_element(elem, selector):
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                    elem,
                )
            except Exception:
                pass

            try:
                elem.click()
            except Exception:
                try:
                    ActionChains(driver).move_to_element(elem).pause(0.2).click().perform()
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", elem)
                    except Exception:
                        return False

            try:
                tag = str(elem.tag_name or "")
            except Exception:
                tag = ""
            try:
                text = str(elem.text or elem.get_attribute("value") or "").strip()
            except Exception:
                text = ""
            click_detail = (
                f"WEHAGO click tag={tag or '?'} text={text or '?'} selector={selector}"
            )
            self._last_print_click_detail += f" / {click_detail}"
            return True

        def search_and_click(selectors, timeout=10, reverse=False):
            deadline = time.time() + timeout
            while time.time() < deadline:
                for sel in selectors:
                    try:
                        elems = driver.find_elements(By.XPATH, sel)
                        if reverse:
                            elems = list(reversed(elems))
                        for elem in elems:
                            if elem.is_displayed() and click_element(elem, sel):
                                return True
                    except Exception:
                        pass
                
                try:
                    frames = driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame")
                    for frame in frames:
                        try:
                            driver.switch_to.frame(frame)
                            for sel in selectors:
                                elems = driver.find_elements(By.XPATH, sel)
                                if reverse:
                                    elems = list(reversed(elems))
                                for elem in elems:
                                    if elem.is_displayed() and click_element(elem, sel):
                                        driver.switch_to.default_content()
                                        return True
                            driver.switch_to.default_content()
                        except Exception:
                            driver.switch_to.default_content()
                except Exception:
                    pass
                time.sleep(0.5)
            return False

        if not search_and_click(selectors_print, timeout=5):
            if self._click_confirm_button(driver, timeout=5, reverse=True) or search_and_click(selectors_confirm, timeout=2):
                time.sleep(1.5)
                self._accept_alert(driver, timeout=1)
                self._dismiss_notice_dialog(driver)
                 
                # 추가: 두 번째 모달 '확인' 버튼 클릭 (DOM의 마지막에 생성되는 모달 우선 클릭)
                self._click_confirm_button(driver, timeout=3, reverse=True) or search_and_click(selectors_confirm, timeout=3, reverse=True)
                
                if not search_and_click(selectors_print, timeout=15):
                    return False
            else:
                return False

        launch_steps = []
        launch_ready = self._settle_print_launch(driver, timeout=35, steps=launch_steps)
        if launch_ready:
            self._last_print_click_detail += f" / launch={' > '.join(launch_steps)}"
        else:
            launch_steps.append("preview-not-open")
            runtime = self._ensure_wehago_print_runtime()
            launch_steps.append(str(runtime.get("state") or "runtime-checked"))
            time.sleep(1.0)
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            if search_and_click(selectors_print, timeout=3, reverse=True):
                launch_steps.append("print-retry")
                launch_ready = self._settle_print_launch(driver, timeout=35, steps=launch_steps)
            else:
                launch_steps.append("print-retry-button-not-found")
            self._last_print_click_detail += f" / launch={' > '.join(launch_steps)}"

        if len(driver.window_handles) > windows_before:
            driver.switch_to.window(driver.window_handles[-1])
        return launch_ready

    @staticmethod
    def _ensure_wehago_print_runtime() -> dict:
        """Keep WEHAGO's interactive print runtime alive in the backend session."""
        executable = Path(r"C:\Douzone\Wehago\WehagoPrint\WehagoPrint.exe")
        if not executable.is_file():
            return {
                "state": "runtime-missing",
                "detail": f"WEHAGO print runtime missing ({executable})",
            }

        try:
            import psutil

            executable_key = str(executable.resolve()).lower()
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    name = str(proc.info.get("name") or "").lower()
                    process_exe = str(proc.info.get("exe") or "").lower()
                    if name == "wehagoprint.exe" and process_exe == executable_key:
                        return {
                            "state": "runtime-running",
                            "detail": f"WEHAGO print runtime running (PID {proc.pid})",
                        }
                except Exception:
                    continue
        except Exception:
            pass

        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            process = subprocess.Popen(
                [str(executable)],
                cwd=str(executable.parent),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=flags,
            )
            deadline = time.time() + 5
            while time.time() < deadline:
                if process.poll() is not None:
                    return {
                        "state": "runtime-exited",
                        "detail": f"WEHAGO print runtime exited (code {process.returncode})",
                    }
                time.sleep(0.25)
            return {
                "state": "runtime-started",
                "detail": f"WEHAGO print runtime started (PID {process.pid})",
            }
        except Exception as exc:
            return {
                "state": "runtime-start-failed",
                "detail": f"WEHAGO print runtime start failed ({exc!r})",
            }

    @staticmethod
    def _probe_local_print_agent(driver, timeout: int = 5) -> dict:
        """Probe WEHAGO's HTTPS loopback agent from the invoice origin."""
        script = """
            const done = arguments[arguments.length - 1];
            const timeoutMs = arguments[0];
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), timeoutMs);
            fetch('https://127.0.0.1:8233/DCloudClientAgent', {
                method: 'POST',
                headers: {'Content-Type': 'application/json; charset=utf-8'},
                body: '{}',
                signal: controller.signal,
                cache: 'no-store'
            }).then(async response => {
                clearTimeout(timer);
                let body = '';
                try { body = await response.text(); } catch (_) {}
                done({
                    reachable: true,
                    status: response.status,
                    body: body.slice(0, 200)
                });
            }).catch(error => {
                clearTimeout(timer);
                done({reachable: false, error: String(error)});
            });
        """
        previous_script_timeout = None
        try:
            previous_timeout = getattr(driver, "timeouts", None)
            previous_script_timeout = (
                getattr(previous_timeout, "script", None)
                if previous_timeout is not None
                else None
            )
            driver.set_script_timeout(max(1, timeout + 1))
            result = driver.execute_async_script(script, int(timeout * 1000))
            if isinstance(result, dict):
                return result
            return {"reachable": False, "error": "invalid probe response"}
        except Exception as exc:
            return {"reachable": False, "error": repr(exc)}
        finally:
            try:
                if previous_script_timeout is not None:
                    driver.set_script_timeout(previous_script_timeout)
            except Exception:
                pass

    def _settle_print_launch(self, driver, timeout: int, steps: list[str]) -> bool:
        """Handle the confirmations between the WEHAGO print click and preview."""
        time.sleep(0.7)
        if self._print_preview_is_open():
            steps.append("preview-open")
            return True

        if self._accept_alert(driver, timeout=1):
            steps.append("js-alert-accepted")
            time.sleep(0.5)

        if self._click_confirm_button(driver, timeout=2, reverse=True):
            steps.append("web-confirm-clicked")
            time.sleep(0.7)
            if self._accept_alert(driver, timeout=1):
                steps.append("post-confirm-alert-accepted")

        if self._print_preview_is_open():
            steps.append("preview-open")
            return True

        if self._allow_chrome_permission_popup(driver, timeout=timeout):
            steps.append("external-app-prompt-handled")

        deadline = time.time() + 4
        while time.time() < deadline:
            if self._print_preview_is_open():
                steps.append("preview-open")
                return True
            time.sleep(0.4)
        return False

    def _export_browser_pdf(self, driver, final_path: Path) -> Path | None:
        """Disabled: a Chrome print is the WEHAGO web page, not the invoice PDF."""
        self._last_browser_pdf_error = (
            "Chrome 웹 화면 PDF 대체 저장은 비활성화되었습니다. "
            "더존 네이티브 인쇄 PDF만 허용됩니다."
        )
        return None

    def _print_preview_is_open(self) -> bool:
        title_hints = (
            "duzon - printdialog",
            "wehagoprint",
            "인쇄 기본 설정 / 미리보기",
            "print preview",
            "tx2a.drf",
        )
        for backend in ("uia", "win32"):
            try:
                windows = Desktop(backend=backend).windows()
            except Exception:
                continue
            for win in windows:
                try:
                    if hasattr(win, "is_visible") and not win.is_visible():
                        continue
                    wrapper = win.wrapper_object()
                    title = str(wrapper.window_text() or "").strip().lower()
                    if any(hint in title for hint in title_hints):
                        return True
                    if self._looks_like_print_preview(wrapper):
                        return True
                except Exception:
                    continue
        return False

    def _allow_chrome_permission_popup(self, driver, timeout: int = 8) -> bool:
        """
        Chrome 외부 앱 실행 권한 팝업에서 '허용' 버튼을 자동 클릭.
        WEHAGO 인쇄 버튼 이후 1회성 팝업이 뜨는 구조라, 브라우저 DOM이 아닌
        Chrome UI Automation 트리에서 탐색해야 한다.
        """
        prompt_hints = (
            "wehago.com",
            "다른 앱",
            "서비스에 액세스",
            "권한",
            "애플리케이션",
            "앱을 열",
            "열도록 허용",
            "duzon",
            "wehagoprint",
            "외부 프로토콜",
        )
        button_hints = ("허용", "allow", "열기", "open")
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._print_preview_is_open():
                return True
            try:
                desktop = Desktop(backend="uia")
                for win in desktop.windows():
                    try:
                        if not win.is_visible():
                            continue
                        wrapper = win.wrapper_object()
                        texts = []
                        for node in [wrapper, *wrapper.descendants()]:
                            try:
                                txt = (node.window_text() or "").strip()
                                if txt:
                                    texts.append(txt)
                            except Exception:
                                continue
                        merged = " ".join(texts).lower()
                        if not any(h.lower() in merged for h in prompt_hints):
                            continue

                        for btn in wrapper.descendants(control_type="Button"):
                            try:
                                caption = (btn.window_text() or "").strip()
                                normalized = caption.replace("&", "").strip().lower()
                                if not any(hint in normalized for hint in button_hints):
                                    continue
                                try:
                                    btn.set_focus()
                                    btn.click_input()
                                except Exception:
                                    btn.invoke()
                                deadline_after_click = time.time() + 4
                                while time.time() < deadline_after_click:
                                    if self._print_preview_is_open():
                                        return True
                                    time.sleep(0.4)
                                break
                            except Exception:
                                continue
                    except Exception:
                        continue
            except Exception:
                pass
            time.sleep(0.4)
        if self._print_preview_is_open():
            return True
        return False

    def _allow_chrome_permission_popup_by_xy(self, driver, timeout: int = 8) -> bool:
        """Deprecated: coordinate clicks can hit page content, so never use them."""
        return False

    def _export_pdf_from_print_dialog(self, final_path, timeout: int = 30):
        self._last_pdf_export_error = ""
        self._last_duzon_dialog_error = ""
        dlg = self._wait_print_dialog(timeout=timeout)
        if not dlg:
            detail = (
                self._last_duzon_dialog_error
                or "더존 인쇄 미리보기 창이 실행되지 않았습니다"
            )
            click_detail = str(getattr(self, "_last_print_click_detail", "") or "").strip()
            if click_detail:
                detail = f"{detail} / {click_detail}"
            self._set_pdf_export_error(final_path, detail)
            return None

        saved = None
        try:
            if not self._click_pdf_button(dlg):
                self._set_pdf_export_error(final_path, "더존 미리보기의 PDF 버튼 클릭에 실패했습니다")
                return None
            if not self._click_print_execute_button(dlg):
                self._set_pdf_export_error(final_path, "더존 미리보기의 인쇄하기 버튼 클릭에 실패했습니다")
                return None

            saved = self._save_pdf_dialog(final_path, timeout=timeout)
            return saved
        finally:
            # The Duzon/WEHAGO preview is a separate Windows program. Close it
            # even when saving fails, otherwise the next crawl keeps reusing a
            # stale preview window.
            self._close_print_dialog(dlg)
            self._close_all_print_dialogs()
            self._terminate_stale_duzon_print_helpers()

    def _wait_print_dialog(self, timeout: int = 20):
        deadline = time.time() + timeout
        exception_count = 0
        preview_title_patterns = (
            r".*인쇄 기본 설정 / 미리보기.*",
            r".*인쇄.*미리보기.*",
            r".*Print.*Preview.*",
            r".*WehagoPrint.*미리보기.*",
            r".*TX2A\.drf.*",
        )

        while time.time() < deadline:
            handled_exception = False
            for backend in ("uia", "win32"):
                try:
                    win = Desktop(backend=backend).window(
                        title_re=r".*Duzon - PrintDialog.*"
                    )
                    if win.exists(timeout=0.3):
                        wrap = win.wrapper_object()
                        if self._is_duzon_exception_dialog(wrap):
                            exception_count += 1
                            if exception_count > 2:
                                self._last_duzon_dialog_error = (
                                    "Duzon PrintDialog 오류가 반복되었습니다: "
                                    "개체 참조가 개체의 인스턴스로 설정되지 않았습니다"
                                )
                                return None
                            if not self._continue_duzon_exception_dialog(wrap):
                                self._last_duzon_dialog_error = (
                                    "Duzon PrintDialog 오류창의 계속 버튼 처리에 실패했습니다"
                                )
                                return None
                            handled_exception = True
                        elif self._looks_like_print_preview(wrap):
                            try:
                                wrap.set_focus()
                            except Exception:
                                pass
                            return wrap
                except Exception:
                    pass
                if handled_exception:
                    break
            if handled_exception:
                time.sleep(1.0)
                continue

            for backend in ("uia", "win32"):
                for title_re in preview_title_patterns:
                    try:
                        win = Desktop(backend=backend).window(title_re=title_re)
                        if not win.exists(timeout=0.4):
                            continue
                        wrap = win.wrapper_object()
                        try:
                            wrap.set_focus()
                        except Exception:
                            pass
                        return wrap
                    except Exception:
                        continue
            time.sleep(0.4)
        relevant_titles = self._relevant_desktop_window_titles()
        if relevant_titles and not self._last_duzon_dialog_error:
            self._last_duzon_dialog_error = (
                "더존 인쇄 미리보기 창을 식별하지 못했습니다"
                f" (감지 창: {' | '.join(relevant_titles)})"
            )
        return None

    @staticmethod
    def _looks_like_print_preview(dlg) -> bool:
        texts = []
        try:
            texts.append(str(dlg.window_text() or ""))
        except Exception:
            pass
        try:
            nodes = dlg.descendants()
        except Exception:
            nodes = []
        for node in nodes:
            try:
                value = str(node.window_text() or "").strip()
                if value:
                    texts.append(value)
            except Exception:
                continue
        merged = " ".join(texts).lower()
        has_preview_heading = "인쇄 기본 설정 / 미리보기" in merged
        has_dr_viewer = "dr viewer" in merged
        has_drf_document = "tx2a.drf" in merged
        has_printer_selector = "프린터선택" in merged
        has_legacy_controls = "인쇄하기" in merged and (
            "pdf" in merged or has_printer_selector or "print" in merged
        )
        return (
            has_preview_heading
            or (has_dr_viewer and (has_printer_selector or has_drf_document))
            or has_legacy_controls
        )

    @staticmethod
    def _relevant_desktop_window_titles() -> list[str]:
        titles = []
        hints = ("duzon", "wehago", "인쇄", "미리보기", "print", "tx2a")
        for backend in ("uia", "win32"):
            try:
                windows = Desktop(backend=backend).windows()
            except Exception:
                continue
            for win in windows:
                try:
                    title = str(win.window_text() or "").strip()
                except Exception:
                    continue
                lowered = title.lower()
                if not title or not any(hint in lowered for hint in hints):
                    continue
                if title not in titles:
                    titles.append(title[:160])
                if len(titles) >= 8:
                    return titles
        return titles

    @staticmethod
    def _is_duzon_exception_dialog(dlg) -> bool:
        hints = (
            "처리되지 않은 예외",
            "개체 참조가 개체의 인스턴스로 설정되지 않았습니다",
            "unhandled exception",
            "object reference not set to an instance of an object",
        )
        texts = []
        try:
            texts.append(str(dlg.window_text() or ""))
        except Exception:
            pass
        try:
            nodes = dlg.descendants()
        except Exception:
            nodes = []
        for node in nodes:
            try:
                text = str(node.window_text() or "").strip()
                if text:
                    texts.append(text)
            except Exception:
                continue
        merged = " ".join(texts).lower()
        return any(hint.lower() in merged for hint in hints)

    @staticmethod
    def _continue_duzon_exception_dialog(dlg) -> bool:
        try:
            nodes = dlg.descendants(control_type="Button")
        except Exception:
            try:
                nodes = dlg.descendants()
            except Exception:
                nodes = []

        for node in nodes:
            try:
                caption = str(node.window_text() or "").strip()
                normalized = caption.replace("&", "").lower()
                if not (
                    normalized.startswith("계속")
                    or normalized.startswith("continue")
                ):
                    continue
                try:
                    node.click_input()
                except Exception:
                    node.invoke()
                return True
            except Exception:
                continue

        try:
            rect = dlg.rectangle()
            pyautogui.click(rect.right - 58, rect.bottom - 22)
            return True
        except Exception:
            return False

    def _click_pdf_button(self, dlg) -> bool:
        # This DevExpress preview can block indefinitely while pywinauto
        # enumerates descendants. Send the click to the control under the
        # known PDF-button point instead; this also leaves the user's cursor
        # and foreground window untouched.
        if self._post_dialog_click(dlg, 228, 202):
            time.sleep(1)
            return True

        deadline = time.time() + 8
        while time.time() < deadline:
            try:
                for node in dlg.descendants():
                    try:
                        txt = (node.window_text() or "").strip()
                        if txt != "PDF":
                            continue
                        try:
                            node.click_input()
                        except Exception:
                            node.invoke()
                        time.sleep(1)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
            time.sleep(0.4)

        # Duzon/WEHAGO 미리보기는 서버 환경에서 PDF 버튼이 UIA 텍스트로
        # 노출되지 않는 경우가 있어, 마지막 수단으로 창 기준 상대좌표를 쓴다.
        try:
            rect = dlg.rectangle()
            candidates = [
                (228, 202),
                (222, 202),
                (235, 202),
                (228, 194),
                (228, 210),
            ]
            for dx, dy in candidates:
                pyautogui.click(rect.left + dx, rect.top + dy)
                time.sleep(0.8)
                return True
        except Exception:
            pass
        return False

    def _click_print_execute_button(self, dlg) -> bool:
        if self._post_dialog_click(dlg, 88, 94):
            time.sleep(1)
            return True

        try:
            for node in dlg.descendants():
                try:
                    txt = (node.window_text() or "").strip()
                    if txt != "인쇄하기":
                        continue
                    try:
                        node.click_input()
                    except Exception:
                        try:
                            node.invoke()
                        except Exception:
                            pass
                    time.sleep(1)
                    return True
                except Exception:
                    continue
        except Exception:
            pass

        try:
            rect = dlg.rectangle()
            candidates = [
                (88, 94),
                (98, 96),
                (110, 105),
                (110, 114),
            ]
            for dx, dy in candidates:
                pyautogui.click(rect.left + dx, rect.top + dy)
                time.sleep(0.8)
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _post_dialog_click(dlg, dx: int, dy: int) -> bool:
        """Post a background click to a Duzon preview control."""
        try:
            import win32api
            import win32con
            import win32gui

            rect = dlg.rectangle()
            root_handle = int(dlg.handle)
            screen_point = (int(rect.left + dx), int(rect.top + dy))
            target_handle = int(win32gui.WindowFromPoint(screen_point) or root_handle)
            if target_handle != root_handle and not win32gui.IsChild(
                root_handle, target_handle
            ):
                target_handle = root_handle
            client_x, client_y = win32gui.ScreenToClient(target_handle, screen_point)
            packed = win32api.MAKELONG(client_x, client_y)
            win32gui.PostMessage(target_handle, win32con.WM_MOUSEMOVE, 0, packed)
            win32gui.PostMessage(
                target_handle,
                win32con.WM_LBUTTONDOWN,
                win32con.MK_LBUTTON,
                packed,
            )
            win32gui.PostMessage(target_handle, win32con.WM_LBUTTONUP, 0, packed)
            return True
        except Exception:
            return False

    def _save_pdf_dialog(self, final_path, timeout: int = 30):
        started_at = time.time()
        before_files = self.snapshot(".pdf")
        final_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + timeout
        last_exception = None

        while time.time() < deadline:
            direct = self.wait_new_file(".pdf", before_files, timeout=1)
            if direct:
                try:
                    if direct.resolve() != final_path.resolve():
                        direct.rename(final_path)
                    self._cleanup_saveas_new_folders(final_path, started_at)
                    return final_path
                except Exception:
                    self._cleanup_saveas_new_folders(final_path, started_at)
                    return direct

            try:
                wrap = self._find_save_as_dialog(timeout=0.5)
                if wrap:
                    try:
                        wrap.set_focus()
                    except Exception:
                        pass
                    
                    import pyautogui
                    for key in ('alt', 'ctrl', 'shift', 'win'):
                        pyautogui.keyUp(key)
                    time.sleep(0.3)

                    success = self._set_save_as_filename_text(wrap, str(final_path))
                    if not success:
                        self._cleanup_saveas_new_folders(final_path, started_at)
                        self._set_pdf_export_error(final_path, "PDF 저장창 파일명 입력에 실패했습니다")
                        return None

                    if not self._click_save_as_save_button(wrap):
                        # Do not press Enter here. If the file list has focus,
                        # Enter can open/create the selected "새 폴더" item.
                        self._cleanup_saveas_new_folders(final_path, started_at)
                        self._set_pdf_export_error(final_path, "PDF 저장창의 저장 버튼 클릭에 실패했습니다")
                        return None
                    time.sleep(0.5)

                    self._confirm_overwrite_dialog()

                    stable_deadline = time.time() + 15
                    while time.time() < stable_deadline:
                        if final_path.exists() and self._is_stable(final_path, interval=0.5):
                            self._cleanup_saveas_new_folders(final_path, started_at)
                            return final_path
                        recovered = self._recover_misplaced_pdf(final_path, started_at)
                        if recovered:
                            self._cleanup_saveas_new_folders(final_path, started_at)
                            return recovered
                        time.sleep(0.4)
            except Exception as exc:
                last_exception = exc
            time.sleep(0.3)

        fallback = self.wait_new_file(".pdf", before_files, timeout=2)
        if fallback:
            try:
                if fallback.resolve() != final_path.resolve():
                    fallback.rename(final_path)
                self._cleanup_saveas_new_folders(final_path, started_at)
                return final_path
            except Exception:
                self._cleanup_saveas_new_folders(final_path, started_at)
                return fallback
        recovered = self._recover_misplaced_pdf(final_path, started_at)
        if recovered:
            self._cleanup_saveas_new_folders(final_path, started_at)
            return recovered
        recovered = self._recover_pdf_from_saveas_new_folders(final_path, started_at)
        self._cleanup_saveas_new_folders(final_path, started_at)
        if recovered:
            return recovered
        detail = "PDF 저장창 또는 생성된 PDF 파일을 확인하지 못했습니다"
        if last_exception is not None:
            detail += f" ({last_exception!r})"
        self._set_pdf_export_error(final_path, detail)
        return None

    def _find_save_as_dialog(self, timeout: float = 0.5):
        title_patterns = (
            r".*다른 이름으로.*저장.*",
            r".*다음 이름으로.*저장.*",
            r".*프린터 출력.*저장.*",
            r".*인쇄 출력.*저장.*",
            r".*Save Print Output As.*",
            r".*Save As.*",
        )
        for backend in ("win32", "uia"):
            for title_re in title_patterns:
                try:
                    win = Desktop(backend=backend).window(title_re=title_re)
                    if win.exists(timeout=timeout):
                        return win.wrapper_object()
                except Exception:
                    continue
        return None

    def _set_pdf_export_error(self, final_path: Path, text: str) -> None:
        self._last_pdf_export_error = str(text or "").strip()
        self._write_saveas_debug(final_path, f"pdf_export_error={self._last_pdf_export_error}")

    def _recover_pdf_from_saveas_new_folders(self, final_path: Path, started_at: float):
        try:
            roots = [final_path.parent, Path.home() / "Downloads", Path.home() / "Documents", Path.home() / "Desktop"]
            candidates = []
            for root in roots:
                if not root.exists():
                    continue
                for folder in root.glob("새 폴더*"):
                    try:
                        if not folder.is_dir() or folder.stat().st_mtime < started_at - 10:
                            continue
                        for pdf in folder.glob("*.pdf"):
                            if pdf.stat().st_mtime >= started_at - 10 and self._is_stable(pdf, interval=0.5):
                                candidates.append(pdf)
                    except Exception:
                        continue
            for pdf in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    final_path.parent.mkdir(parents=True, exist_ok=True)
                    if final_path.exists():
                        final_path.unlink()
                    pdf.replace(final_path)
                    self._write_saveas_debug(final_path, f"recovered_from_new_folder={pdf}")
                    return final_path
                except Exception as exc:
                    self._write_saveas_debug(final_path, f"recover_failed={pdf} | {exc!r}")
        except Exception as exc:
            self._write_saveas_debug(final_path, f"recover_scan_failed={exc!r}")
        return None

    def _cleanup_saveas_new_folders(self, final_path: Path, started_at: float) -> None:
        roots = [final_path.parent, Path.home() / "Downloads", Path.home() / "Documents", Path.home() / "Desktop"]
        removed = []
        skipped = []
        for root in roots:
            try:
                if not root.exists():
                    continue
                for folder in root.glob("새 폴더*"):
                    try:
                        if not folder.is_dir() or folder.stat().st_mtime < started_at - 10:
                            continue
                        descendants = [p for p in folder.rglob("*")]
                        if any(p.is_file() and p.stat().st_mtime < started_at - 10 for p in descendants):
                            skipped.append(str(folder))
                            continue
                        shutil.rmtree(folder)
                        removed.append(str(folder))
                    except Exception as exc:
                        skipped.append(f"{folder} | {exc!r}")
            except Exception:
                continue
        if removed or skipped:
            self._write_saveas_debug(final_path, f"new_folder_cleanup removed={removed} skipped={skipped}")

    def _write_saveas_debug(self, final_path: Path, text: str) -> None:
        try:
            debug_path = final_path.parent / "_debug_wehago_saveas.txt"
            with open(debug_path, "a", encoding="utf-8") as f:
                f.write(time.strftime("[%Y-%m-%d %H:%M:%S] "))
                f.write(str(text))
                f.write("\n")
        except Exception:
            pass

    def _recover_misplaced_pdf(self, final_path: Path, started_at: float):
        """Microsoft Print to PDF sometimes ignores the target folder.
        If the correct filename was saved under Documents/Downloads/Desktop, move it back.
        """
        try:
            target_name = final_path.name
            roots = [
                final_path.parent,
                Path.home() / "Documents",
                Path.home() / "Downloads",
                Path.home() / "Desktop",
            ]
            seen = set()
            for root in roots:
                try:
                    root = root.resolve()
                except Exception:
                    continue
                if root in seen or not root.exists():
                    continue
                seen.add(root)
                candidates = []
                try:
                    candidates.extend(root.glob(target_name))
                    candidates.extend(root.glob(f"**/{target_name}"))
                except Exception:
                    continue
                for path in sorted(set(candidates), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True):
                    try:
                        if path.resolve() == final_path.resolve():
                            continue
                        if path.suffix.lower() != ".pdf" or path.name != target_name:
                            continue
                        if path.stat().st_mtime < started_at - 10:
                            continue
                        if not self._is_stable(path, interval=0.5):
                            continue
                        final_path.parent.mkdir(parents=True, exist_ok=True)
                        if final_path.exists():
                            final_path.unlink()
                        path.replace(final_path)
                        return final_path
                    except Exception:
                        continue
        except Exception:
            pass
        return None

    def _set_save_as_filename_text(self, dlg, text: str) -> bool:
        try:
            dlg_rect = dlg.rectangle()
            edits = []
            for node in dlg.descendants():
                try:
                    class_name = node.class_name() or ""
                    try:
                        control_type = str(node.element_info.control_type or "")
                    except Exception:
                        control_type = ""
                    if class_name != "Edit" and control_type != "Edit":
                        continue
                    rect = node.rectangle()
                    if rect.top < dlg_rect.top + int(dlg_rect.height() * 0.50):
                        continue
                    edits.append((rect.top, rect.left, node))
                except Exception:
                    continue
            for _, _, node in sorted(edits, reverse=True):
                try:
                    node.set_focus()
                    node.set_edit_text(str(text))
                    time.sleep(0.2)
                    return True
                except Exception:
                    try:
                        node.set_focus()
                        node.type_keys("^a{BACKSPACE}", set_foreground=False)
                        node.type_keys(str(text), with_spaces=True, set_foreground=False)
                        time.sleep(0.2)
                        return True
                    except Exception:
                        continue
        except Exception:
            pass

        # Some Windows "Save Print Output As" dialogs do not expose their
        # filename Edit through UIA. Focus the lower filename field directly.
        try:
            rect = dlg.rectangle()
            pyautogui.click(
                rect.left + int(rect.width() * 0.55),
                rect.bottom - 92,
            )
            time.sleep(0.2)
            pyautogui.hotkey("ctrl", "a")
            self._paste_save_as_text(str(text))
            time.sleep(0.2)
            return True
        except Exception:
            pass
        return False

    @staticmethod
    def _paste_save_as_text(text: str) -> None:
        try:
            import win32clipboard

            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(str(text), win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
            pyautogui.hotkey("ctrl", "v")
            return
        except Exception:
            pass

        pyautogui.write(str(text), interval=0.01)

    def _click_save_as_save_button(self, dlg) -> bool:
        save_markers = ("저장", "Save")
        blocked_markers = ("열기", "Open", "새 폴더", "New Folder")

        for _ in range(8):
            try:
                dlg_rect = dlg.rectangle()
                min_top = dlg_rect.bottom - 90
                min_left = dlg_rect.left + int(dlg_rect.width() * 0.55)
                for node in dlg.descendants():
                    try:
                        txt = (node.window_text() or "").strip()
                        class_name = node.class_name() or ""
                        try:
                            control_type = str(node.element_info.control_type or "")
                        except Exception:
                            control_type = ""
                        if "Button" not in class_name and control_type != "Button":
                            continue
                        rect = node.rectangle()
                        if rect.top < min_top or rect.left < min_left:
                            continue
                        if any(b in txt for b in blocked_markers):
                            continue
                        if not any(s in txt for s in save_markers):
                            continue
                        try:
                            node.set_focus()
                        except Exception:
                            pass
                        node.click_input()
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
            time.sleep(0.25)
        return False

    def _focus_save_as_filename_field(self, dlg) -> bool:
        try:
            dlg_rect = dlg.rectangle()
            edits = []
            for node in dlg.descendants():
                try:
                    if (node.class_name() or "") != "Edit":
                        continue
                    rect = node.rectangle()
                    edits.append((rect.top, rect.left, node))
                except Exception:
                    continue
            # Filename edit is the lower Edit control. Search/address edits are near the top.
            for _, _, node in sorted(edits, reverse=True):
                try:
                    rect = node.rectangle()
                    if rect.top < dlg_rect.top + int((dlg_rect.height()) * 0.55):
                        continue
                    node.click_input()
                    time.sleep(0.15)
                    return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def _confirm_overwrite_dialog(self) -> None:
        for _ in range(8):
            for backend in ("win32", "uia"):
                try:
                    dlg = Desktop(backend=backend).window(title_re=r".*(확인|Confirm|바꾸기).*")
                    if not dlg.exists(timeout=0.2):
                        continue
                    wrap = dlg.wrapper_object()
                    title = (wrap.window_text() or "").strip()
                    if "다른 이름으로 저장" in title:
                        continue
                    try:
                        wrap.set_focus()
                    except Exception:
                        pass
                    saw_overwrite_text = False
                    for node in wrap.descendants():
                        try:
                            txt = (node.window_text() or "").strip()
                            if any(marker in txt for marker in ("이미", "존재", "바꾸", "덮어", "overwrite", "replace")):
                                saw_overwrite_text = True
                            if txt in ("예", "Yes", "확인", "저장", "바꾸기"):
                                node.click_input()
                                time.sleep(0.3)
                                return
                        except Exception:
                            continue
                    if saw_overwrite_text:
                        pyautogui.press("enter")
                        time.sleep(0.3)
                        return
                except Exception:
                    continue
            time.sleep(0.2)

    def _close_print_dialog(self, dlg) -> None:
        try:
            dlg.set_focus()
        except Exception:
            pass

        try:
            dlg.close()
            time.sleep(0.8)
            return
        except Exception:
            pass

        try:
            rect = dlg.rectangle()
            pyautogui.click(rect.right - 18, rect.top + 16)
            time.sleep(0.8)
            return
        except Exception:
            pass

        try:
            pyautogui.hotkey("alt", "f4")
            time.sleep(0.8)
        except Exception:
            pass

    def _close_all_print_dialogs(self) -> None:
        title_patterns = (
            r".*인쇄 기본 설정 / 미리보기.*",
            r".*Duzon.*Print.*",
            r".*WehagoPrint.*",
            r".*TX2A\.drf.*",
            r".*다음 이름으로 프린터 출력 저장.*",
            r".*Save Print Output As.*",
        )
        for _ in range(2):
            closed_any = False
            for backend in ("uia", "win32"):
                try:
                    for win in Desktop(backend=backend).windows():
                        title = (win.window_text() or "").strip()
                        if not any(re.search(pat, title, re.I) for pat in title_patterns):
                            continue
                        try:
                            win.close()
                            closed_any = True
                            time.sleep(0.3)
                            continue
                        except Exception:
                            pass
                        try:
                            rect = win.rectangle()
                            pyautogui.click(rect.right - 18, rect.top + 16)
                            closed_any = True
                            time.sleep(0.3)
                        except Exception:
                            pass
                except Exception:
                    pass
            if not closed_any:
                break

    @staticmethod
    def _terminate_stale_duzon_print_helpers() -> None:
        """Terminate only the external Duzon WEHAGO print helper processes."""
        try:
            import psutil

            matched = []
            for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
                try:
                    name = str(proc.info.get("name") or "").lower()
                    exe = str(proc.info.get("exe") or "").lower()
                    command = " ".join(proc.info.get("cmdline") or []).lower()
                    process_text = f"{name} {exe} {command}".replace("/", "\\")
                    is_wehago_print = (
                        "\\douzone\\wehago\\wehagoprint" in process_text
                        or (
                            "douzone" in process_text
                            and (
                                "wehagoprint" in process_text
                                or "printdialog" in process_text
                            )
                        )
                    )
                    if is_wehago_print:
                        matched.append(proc)
                except Exception:
                    continue

            for proc in matched:
                try:
                    for child in proc.children(recursive=True):
                        child.kill()
                except Exception:
                    pass
                try:
                    proc.kill()
                except Exception:
                    pass
            if matched:
                psutil.wait_procs(matched, timeout=3)
        except Exception:
            pass

    @staticmethod
    def _paste_text(text: str) -> None:
        try:
            import win32clipboard
            import win32con
            import pyautogui
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, str(text))
            win32clipboard.CloseClipboard()
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                root.clipboard_clear()
                root.clipboard_append(str(text))
                root.update()
                root.destroy()
                import pyautogui
                pyautogui.hotkey("ctrl", "v")
            except Exception:
                pass

    @staticmethod
    def _parse_field(html: str, keywords: list[str]) -> str:
        for kw in keywords:
            m = re.search(rf'{kw}[^가-힣A-Za-z()]*([가-힣A-Za-z(주)㈜]+)', html)
            if m:
                return m.group(1).strip()
        return ""

    @staticmethod
    def _parse_amount(html: str) -> int:
        nums = [int(n.replace(",", "")) for n in re.findall(r"[\d,]{6,15}", html)
                if int(n.replace(",", "")) > 10000]
        return max(nums) if nums else 0

    @staticmethod
    def _to_int(value) -> int:
        return int(re.sub(r"[^\d]", "", str(value or "0")) or "0")


if __name__ == "__main__":
    print("[WEHAGO 단독 테스트]")
    print("메일에서 wehago.com 링크를 복사해서 붙여넣으세요.")
    url = input("URL: ").strip()
    mail_text = input("메일 키워드 (예: Acronis, Watching-On) [엔터=대승]: ").strip() or "대승"
    handler = WehagoHandler()
    res = handler.process(url=url, mail_text=mail_text, mail_date=time.strftime("%y%m%d"))
    print(f"\nok={res['ok']} | pdf={res.get('pdf_path')} | error={res.get('error')}")
    print(f"subject={res.get('subject')}")
