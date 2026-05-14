from __future__ import annotations

import re
import base64
import time
from pathlib import Path
from typing import Any, Callable

from .config import settings
from .invoice_db import add_invoice_log, get_invoice, update_invoice_json
from .purchase_analysis import _extract_order_no_from_quote, _extract_pdf_text, purchase_quote_dir, safe_filename


Progress = Callable[[str], None]

DEFAULT_COMPUZONE_ACCOUNTS = (
    {"user_id": "ds1500", "password": "eotmd12!@"},
    {"user_id": "reum0009", "password": "eotmd12!@"},
)

PRINT_SELECTORS = (
    "button:has-text('출력하기')",
    "a:has-text('출력하기')",
    "input[type='button'][value*='출력']",
    "button:has-text('출력')",
    "a:has-text('출력')",
)

DENY_TEXT_TOKENS = ("권한", "접근", "존재하지", "조회된", "잘못", "로그인")


class CompuzoneQuoteError(RuntimeError):
    pass


def _emit(progress: Progress | None, message: str) -> None:
    if progress:
        progress(message)


def _clean_order_no(value: Any) -> str:
    match = re.search(r"\d{8}", str(value or ""))
    return match.group(0) if match else ""


def _compuzone_accounts() -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    if settings.compuzone_id and settings.compuzone_pw:
        candidates.append({"user_id": settings.compuzone_id, "password": settings.compuzone_pw})
    candidates.extend(DEFAULT_COMPUZONE_ACCOUNTS)

    accounts: list[dict[str, str]] = []
    seen: set[str] = set()
    for account in candidates:
        user_id = str(account.get("user_id") or "").strip()
        password = str(account.get("password") or "")
        if not user_id or not password or user_id.lower() in seen:
            continue
        seen.add(user_id.lower())
        accounts.append({"user_id": user_id, "password": password})
    return accounts


def _invoice_data(invoice: dict[str, Any]) -> dict[str, Any]:
    raw = invoice.get("raw") if isinstance(invoice.get("raw"), dict) else {}
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    merged: dict[str, Any] = {}
    merged.update(raw)
    merged.update(data)
    if isinstance(invoice.get("data"), dict):
        merged.update(invoice["data"])
    return merged


def _invoice_order_no(invoice: dict[str, Any]) -> str:
    data = _invoice_data(invoice)
    for key in ("order_no", "purchase_order_no", "tax_order_no", "quote_order_no"):
        order_no = _clean_order_no(data.get(key) or invoice.get(key))
        if order_no:
            return order_no
    return ""


def _is_compuzone_purchase(invoice: dict[str, Any]) -> bool:
    data = _invoice_data(invoice)
    text = "\n".join(
        str(value or "")
        for value in (
            invoice.get("subject"),
            invoice.get("vendor_name"),
            data.get("vendor_name"),
            data.get("supplier_name"),
            data.get("raw_vendor_name"),
        )
    ).lower()
    return "컴퓨존" in text or "compuzone" in text


def _quote_output_path(invoice_id: int, order_no: str) -> Path:
    filename = safe_filename(f"컴퓨존_견적서_{order_no}.pdf", fallback=f"compuzone_quote_{order_no}.pdf")
    return purchase_quote_dir(invoice_id) / filename


def _first_visible(locator):
    try:
        count = locator.count()
    except Exception:
        return None
    for index in range(min(count, 20)):
        item = locator.nth(index)
        try:
            if item.is_visible(timeout=500):
                return item
        except Exception:
            continue
    return None


def _login_if_needed(page, account: dict[str, str], progress: Progress | None) -> None:
    password = _first_visible(page.locator("input[type='password']"))
    if not password:
        return

    user_id = str(account.get("user_id") or "").strip()
    account_password = str(account.get("password") or "")
    if not user_id or not account_password:
        raise CompuzoneQuoteError("컴퓨존 로그인 계정 정보가 비어 있습니다.")

    _emit(progress, f"컴퓨존 로그인 입력: {user_id}")
    id_candidates = [
        "input[name='login_id']",
        "input[name='id']",
        "input[name='member_id']",
        "input[id*='id' i]",
        "input[type='text']",
        "input[type='email']",
    ]
    user_input = None
    for selector in id_candidates:
        user_input = _first_visible(page.locator(selector))
        if user_input:
            break
    if not user_input:
        raise CompuzoneQuoteError("컴퓨존 로그인 아이디 입력칸을 찾지 못했습니다.")

    user_input.fill(user_id)
    password.fill(account_password)

    clicked = False
    for selector in (
        "button:has-text('로그인')",
        "a:has-text('로그인')",
        "input[type='submit']",
        "input[type='button'][value*='로그인']",
    ):
        button = _first_visible(page.locator(selector))
        if button:
            button.click()
            clicked = True
            break
    if not clicked:
        password.press("Enter")

    page.wait_for_load_state("networkidle", timeout=settings.compuzone_timeout_ms)


def _find_print_button(page) -> Any:
    for selector in PRINT_SELECTORS:
        button = _first_visible(page.locator(selector))
        if button:
            return button
    return None


def _click_print_button(page, progress: Progress | None) -> Any:
    button = _find_print_button(page)
    if button:
        _emit(progress, "컴퓨존 견적서 출력 버튼 클릭")
        try:
            with page.context.expect_page(timeout=5000) as popup_info:
                button.click()
            popup = popup_info.value
            popup.wait_for_load_state("networkidle", timeout=settings.compuzone_timeout_ms)
            return popup
        except Exception:
            try:
                button.click()
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            return page
    _emit(progress, "컴퓨존 출력 버튼을 찾지 못해 현재 화면을 PDF로 저장")
    return page


def _quote_page_accessible(page, order_no: str) -> tuple[bool, str]:
    current_url = (page.url or "").lower()
    if "login" in current_url and "compuzone" in current_url:
        return False, "로그인 페이지로 되돌아감"
    if _find_print_button(page):
        return True, "출력 버튼 감지"

    try:
        body_text = page.locator("body").inner_text(timeout=3000)
    except Exception:
        body_text = ""
    compact = re.sub(r"\D+", "", body_text)
    if order_no and order_no in compact:
        return True, "주문번호 감지"
    if any(token in body_text for token in DENY_TEXT_TOKENS):
        return False, "접근 불가 또는 조회 실패 문구 감지"
    return False, "출력 버튼/주문번호 미검출"


def _close_context(context: Any) -> None:
    try:
        context.close()
    except Exception:
        pass


def _launch_logged_in_context(playwright: Any, account: dict[str, str], progress: Progress | None) -> tuple[Any, Any]:
    user_id = str(account.get("user_id") or "").strip()
    safe_user_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", user_id) or "account"
    profile_dir = settings.compuzone_profile_dir / safe_user_id
    profile_dir.mkdir(parents=True, exist_ok=True)

    _emit(progress, f"컴퓨존 계정 세션 준비: {user_id}")
    context = playwright.chromium.launch_persistent_context(
        str(profile_dir),
        headless=settings.compuzone_headless,
        accept_downloads=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    try:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(settings.compuzone_login_url, wait_until="networkidle", timeout=settings.compuzone_timeout_ms)
        _login_if_needed(page, account, progress)
        return context, page
    except Exception:
        _close_context(context)
        raise


def _get_chromedriver_service() -> Any:
    from selenium.webdriver.chrome.service import Service

    try:
        wdm_base = Path.home() / ".wdm" / "drivers" / "chromedriver" / "win64"
        if wdm_base.exists():
            candidates = sorted(
                wdm_base.rglob("chromedriver.exe"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                return Service(str(candidates[0]))
    except Exception:
        pass

    from webdriver_manager.chrome import ChromeDriverManager

    return Service(ChromeDriverManager().install())


def _selenium_wait_ready(driver: Any, timeout: float | None = None) -> None:
    from selenium.webdriver.support.ui import WebDriverWait

    seconds = timeout or max(5.0, settings.compuzone_timeout_ms / 1000)
    try:
        WebDriverWait(driver, seconds).until(
            lambda d: d.execute_script("return document.readyState") in {"interactive", "complete"}
        )
    except Exception:
        pass


def _selenium_find_visible(driver: Any, locators: tuple[tuple[str, str], ...]) -> Any | None:
    for by, value in locators:
        try:
            elements = driver.find_elements(by, value)
        except Exception:
            continue
        for element in elements[:20]:
            try:
                if element.is_displayed() and element.is_enabled():
                    return element
            except Exception:
                continue
    return None


def _selenium_login_if_needed(driver: Any, account: dict[str, str], progress: Progress | None) -> None:
    from selenium.webdriver.common.by import By

    password = _selenium_find_visible(driver, ((By.CSS_SELECTOR, "input[type='password']"),))
    if not password:
        return

    user_id = str(account.get("user_id") or "").strip()
    account_password = str(account.get("password") or "")
    if not user_id or not account_password:
        raise CompuzoneQuoteError("컴퓨존 로그인 계정 정보가 비어 있습니다.")

    _emit(progress, f"컴퓨존 Selenium 로그인 입력: {user_id}")
    user_input = _selenium_find_visible(
        driver,
        (
            (By.CSS_SELECTOR, "input[name='login_id']"),
            (By.CSS_SELECTOR, "input[name='id']"),
            (By.CSS_SELECTOR, "input[name='member_id']"),
            (By.CSS_SELECTOR, "input[id*='id' i]"),
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.CSS_SELECTOR, "input[type='email']"),
        ),
    )
    if not user_input:
        raise CompuzoneQuoteError("컴퓨존 로그인 아이디 입력칸을 찾지 못했습니다.")

    user_input.clear()
    user_input.send_keys(user_id)
    password.clear()
    password.send_keys(account_password)

    button = _selenium_find_visible(
        driver,
        (
            (By.XPATH, "//button[contains(normalize-space(.), '로그인')]"),
            (By.XPATH, "//a[contains(normalize-space(.), '로그인')]"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.CSS_SELECTOR, "input[type='button'][value*='로그인']"),
        ),
    )
    if button:
        button.click()
    else:
        password.submit()
    time.sleep(1.5)
    _selenium_wait_ready(driver)


def _selenium_print_button(driver: Any) -> Any | None:
    from selenium.webdriver.common.by import By

    return _selenium_find_visible(
        driver,
        (
            (By.XPATH, "//button[contains(normalize-space(.), '출력하기')]"),
            (By.XPATH, "//a[contains(normalize-space(.), '출력하기')]"),
            (By.CSS_SELECTOR, "input[type='button'][value*='출력']"),
            (By.XPATH, "//button[contains(normalize-space(.), '출력')]"),
            (By.XPATH, "//a[contains(normalize-space(.), '출력')]"),
        ),
    )


def _selenium_quote_page_accessible(driver: Any, order_no: str) -> tuple[bool, str]:
    current_url = (driver.current_url or "").lower()
    if "login" in current_url and "compuzone" in current_url:
        return False, "로그인 페이지로 되돌아감"
    if _selenium_print_button(driver):
        return True, "출력 버튼 감지"

    try:
        body_text = driver.find_element("tag name", "body").text
    except Exception:
        body_text = ""
    compact = re.sub(r"\D+", "", body_text)
    if order_no and order_no in compact:
        return True, "주문번호 감지"
    if any(token in body_text for token in DENY_TEXT_TOKENS):
        return False, "접근 불가 또는 조회 실패 문구 감지"
    return False, "출력 버튼/주문번호 미검출"


def _selenium_launch_logged_in_driver(account: dict[str, str], progress: Progress | None) -> Any:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    user_id = str(account.get("user_id") or "").strip()
    safe_user_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", user_id) or "account"
    profile_dir = settings.compuzone_profile_dir / f"selenium_{safe_user_id}"
    profile_dir.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--window-size=1280,1600")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    if settings.compuzone_headless:
        options.add_argument("--headless=new")

    _emit(progress, f"컴퓨존 Selenium 계정 세션 준비: {user_id}")
    driver = webdriver.Chrome(service=_get_chromedriver_service(), options=options)
    driver.set_page_load_timeout(max(15, int(settings.compuzone_timeout_ms / 1000)))
    try:
        driver.get(settings.compuzone_login_url)
        _selenium_wait_ready(driver)
        _selenium_login_if_needed(driver, account, progress)
        return driver
    except Exception:
        _selenium_quit(driver)
        raise


def _selenium_quit(driver: Any) -> None:
    try:
        driver.quit()
    except Exception:
        pass


def _selenium_click_print_page(driver: Any, progress: Progress | None) -> None:
    button = _selenium_print_button(driver)
    if not button:
        _emit(progress, "컴퓨존 출력 버튼을 찾지 못해 현재 화면을 PDF로 저장")
        return

    before_handles = set(driver.window_handles)
    _emit(progress, "컴퓨존 견적서 출력 버튼 클릭")
    button.click()
    time.sleep(1.5)
    after_handles = set(driver.window_handles)
    new_handles = list(after_handles - before_handles)
    if new_handles:
        driver.switch_to.window(new_handles[-1])
        _selenium_wait_ready(driver)
    else:
        _selenium_wait_ready(driver)


def _selenium_save_pdf(driver: Any, save_path: Path) -> None:
    try:
        driver.execute_cdp_cmd("Emulation.setEmulatedMedia", {"media": "print"})
    except Exception:
        pass
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
    save_path.write_bytes(base64.b64decode(payload["data"]))


def fetch_compuzone_quote_pdf(order_no: str, invoice_id: int, progress: Progress | None = None) -> dict[str, Any]:
    order_no = _clean_order_no(order_no)
    if not order_no:
        raise CompuzoneQuoteError("컴퓨존 견적서 조회용 주문번호가 없습니다.")
    if not settings.compuzone_auto_quote_enabled:
        raise CompuzoneQuoteError("COMPUZONE_AUTO_QUOTE_ENABLED=0 상태입니다.")
    accounts = _compuzone_accounts()
    if not accounts:
        raise CompuzoneQuoteError("컴퓨존 로그인 계정이 없습니다.")

    save_path = _quote_output_path(invoice_id, order_no)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    quote_url = settings.compuzone_quote_url_template.format(order_no=order_no)

    used_account = ""
    errors: list[str] = []
    drivers: list[tuple[dict[str, str], Any]] = []
    _emit(progress, f"컴퓨존 견적서 조회 시작(Selenium): {order_no}")
    try:
        for account in accounts:
            account_id = account["user_id"]
            try:
                drivers.append((account, _selenium_launch_logged_in_driver(account, progress)))
            except Exception as exc:
                errors.append(f"{account_id}: 로그인 실패 - {exc}")
                _emit(progress, f"컴퓨존 계정 로그인 실패: {account_id}")

        for account, driver in list(drivers):
            account_id = account["user_id"]
            try:
                _emit(progress, f"컴퓨존 견적서 URL 확인: {account_id}")
                driver.get(quote_url)
                _selenium_wait_ready(driver)
                _selenium_login_if_needed(driver, account, progress)
                if settings.compuzone_login_url.split("/login/")[0] in (driver.current_url or "") and "login" in (
                    driver.current_url or ""
                ).lower():
                    driver.get(quote_url)
                    _selenium_wait_ready(driver)

                ok, reason = _selenium_quote_page_accessible(driver, order_no)
                if not ok:
                    errors.append(f"{account_id}: {reason}")
                    _emit(progress, f"컴퓨존 계정 미사용: {account_id} ({reason})")
                    _selenium_quit(driver)
                    continue

                _emit(progress, f"컴퓨존 견적서 출력 계정 확정: {account_id}")
                for other_account, other_driver in drivers:
                    if other_account["user_id"] != account_id:
                        _selenium_quit(other_driver)

                _selenium_click_print_page(driver, progress)
                time.sleep(1.0)
                _emit(progress, f"컴퓨존 견적서 PDF 저장: {save_path}")
                _selenium_save_pdf(driver, save_path)
                used_account = account_id
                _selenium_quit(driver)
                break
            except Exception as exc:
                errors.append(f"{account_id}: {exc}")
                _emit(progress, f"컴퓨존 계정 처리 실패: {account_id}")
                _selenium_quit(driver)
    finally:
        for _, driver in drivers:
            _selenium_quit(driver)

    if not used_account:
        detail = " / ".join(errors[-4:]) if errors else "접속 가능한 계정 없음"
        raise CompuzoneQuoteError(f"두 계정 모두 견적서 URL 접근 실패: {detail}")

    if not save_path.exists() or save_path.stat().st_size < 1024:
        raise CompuzoneQuoteError(f"컴퓨존 견적서 PDF 저장 실패: {save_path}")

    quote_order_no = ""
    try:
        quote_order_no = _extract_order_no_from_quote(_extract_pdf_text(save_path))
    except Exception:
        quote_order_no = ""

    return {
        "quote_path": str(save_path),
        "quote_pdf_path": str(save_path),
        "order_no": order_no,
        "purchase_order_no": order_no,
        "quote_order_no": quote_order_no or order_no,
        "source_url": quote_url,
        "compuzone_account": used_account,
    }


def auto_attach_compuzone_quote(invoice_id: int, progress: Progress | None = None, *, force: bool = False) -> dict[str, Any]:
    invoice = get_invoice(invoice_id)
    if not invoice:
        return {"ok": False, "skipped": True, "reason": "invoice not found"}
    if str(invoice.get("invoice_type") or "").strip().lower() != "purchase":
        return {"ok": False, "skipped": True, "reason": "not purchase"}
    if not _is_compuzone_purchase(invoice):
        return {"ok": False, "skipped": True, "reason": "not compuzone"}

    data = _invoice_data(invoice)
    quote_path = str(data.get("quote_path") or invoice.get("quote_path") or "")
    if quote_path and Path(quote_path).exists() and not force:
        return {"ok": True, "skipped": True, "reason": "quote already exists", "quote_path": quote_path}

    order_no = _invoice_order_no(invoice)
    if not order_no:
        return {"ok": False, "skipped": True, "reason": "order_no missing"}

    try:
        payload = fetch_compuzone_quote_pdf(order_no, invoice_id, progress=progress)
        update_invoice_json(
            invoice_id,
            {
                **payload,
                "purchase_analysis_ready": False,
                "erp_ready": False,
            },
            message=f"컴퓨존 견적서 자동첨부 완료: 주문번호 {order_no}",
        )
        return {"ok": True, **payload}
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        add_invoice_log(invoice_id, f"컴퓨존 견적서 자동첨부 실패: {message}", level="error")
        return {"ok": False, "skipped": False, "reason": message, "order_no": order_no}
