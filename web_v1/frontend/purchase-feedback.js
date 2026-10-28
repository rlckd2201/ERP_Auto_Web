/* Independent of app.js: the portal adapts that file's transport source. */
(function () {
  "use strict";
  const invoices = new Map();
  const announced = new Set();
  const pending = [];
  let modal, modalBody, modalTitle, focusAfterClose, renderScheduled = false;

  function ensureModal() {
    if (modal) return;
    modal = document.createElement("dialog");
    modal.id = "purchaseFeedbackModal";
    modal.setAttribute("aria-labelledby", "purchaseFeedbackTitle");
    modal.setAttribute("aria-describedby", "purchaseFeedbackMessage");
    modalTitle = document.createElement("h2");
    modalTitle.id = "purchaseFeedbackTitle";
    modalBody = document.createElement("p");
    modalBody.id = "purchaseFeedbackMessage";
    const close = document.createElement("button");
    close.type = "button";
    close.className = "button primary";
    close.textContent = "확인";
    close.autofocus = true;
    close.addEventListener("click", () => modal.close());
    modal.append(modalTitle, modalBody, close);
    modal.addEventListener("close", () => {
      const target = focusAfterClose;
      focusAfterClose = null;
      if (target?.isConnected) target.focus();
      if (pending.length) setTimeout(() => present(...pending.shift()), 0);
    });
    document.body.append(modal);
  }

  function present(title, message, target) {
    ensureModal();
    if (modal.open) {
      if (!pending.some(item => item[1] === message) && modalBody.textContent !== message) pending.push([title, message, target]);
      return;
    }
    modalTitle.textContent = title;
    modalBody.textContent = message;
    focusAfterClose = target;
    modal.showModal();
  }

  function approvalMessage(error, orderNumber) {
    const text = String(error || "");
    if (text.startsWith("품의 자동 확보 실패:")) return text;
    if (text.includes("결재완료 품의 문서가 없습니다")) {
      const order = String(orderNumber || text.match(/\((\d{8})\)\s*로 검색된/)?.[1] || "주문번호");
      return `첨부파일명 '(${order})'로 검색했지만 결재완료 품의를 찾지 못했습니다.\n전자결재 품의의 첨부파일명에 '(${order})'가 괄호까지 포함되어 있는지, 주문번호가 맞는지, 결재가 완료됐는지 확인해 주세요.\n검색 결과만으로 파일명 누락 여부를 단정할 수는 없습니다. 수정 후 품의 확보를 다시 실행해 주세요.`;
    }
    if (text.includes("견적서에서 주문번호")) return "견적서에서 주문번호를 읽지 못했습니다. 견적서 내용 또는 파일명에 올바른 주문번호가 있는지 확인해 주세요.";
    if (/greenlet|Playwright|playwright|DLL load failed/.test(text)) return "서버의 품의 조회 프로그램 실행에 실패했습니다. 관리자에게 품의 조회 프로그램 복구를 요청해 주세요.";
    if (/TimeoutError|Timeout /.test(text)) return "전자결재 화면 또는 첨부파일 응답을 기다리다 시간이 초과됐습니다. 전자결재 접속 상태를 확인한 뒤 다시 시도해 주세요.";
    if (/Traceback|마지막 로그|<!doctype|<html/i.test(text)) return "품의 조회 프로그램에서 오류가 발생했습니다. 관리자에게 품의 조회 로그 확인을 요청해 주세요.";
    return text.slice(0, 500) || "품의 파일을 확보하지 못했습니다. 견적서 주문번호와 전자결재 첨부파일을 확인해 주세요.";
  }

  const outputNotice = "\n\n품의가 없어도 전표·세금계산서·현금출금결의서는 준비된 문서대로 출력할 수 있습니다. 품의는 확보 후 별도로 출력해 주세요.";
  function selectedIds() {
    return [...document.querySelectorAll("tr[data-invoice-id]")]
      .filter(row => row.querySelector("input.invoice-check:checked"))
      .map(row => Number(row.dataset.invoiceId));
  }
  function detailId() {
    return Number(document.getElementById("purchaseDetailTitle")?.textContent.match(/^#(\d+)/)?.[1] || 0);
  }
  function scheduleRender() {
    if (renderScheduled) return;
    renderScheduled = true;
    requestAnimationFrame(() => { renderScheduled = false; renderFeedback(); });
  }
  function renderFeedback() {
    const selected = selectedIds();
    const detail = document.getElementById("purchaseDetailBody");
    const currentId = detailId();
    let activeMessage = "";
    for (const id of selected) {
      const data = invoices.get(id);
      if (!data || data.invoice_type === "regular" || data.approval_pdf_paths?.length) continue;
      if (data.approval_fetch_status !== "error" && !data.approval_fetch_error) continue;
      const message = approvalMessage(data.approval_fetch_error, data.approval_order_number || data.order_no);
      if (id === currentId && selected.length === 1) activeMessage = message;
      const key = `${id}:${data.approval_fetch_finished_at || ""}:${data.approval_fetch_error || "error"}`;
      if (!announced.has(key)) {
        announced.add(key);
        present(`#${id} 품의 자동 확보 실패`, message + outputNotice);
      }
    }
    let banner = document.getElementById("purchaseApprovalFeedback");
    if (!activeMessage || !detail) { banner?.remove(); return; }
    if (!banner) {
      banner = document.createElement("section");
      banner.id = "purchaseApprovalFeedback";
      banner.setAttribute("aria-label", "품의 실패 안내");
      const heading = document.createElement("strong");
      heading.textContent = "품의 자동 확보 실패";
      const body = document.createElement("p");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "button secondary";
      button.textContent = "실패 이유 다시 보기";
      button.addEventListener("click", () => present("품의 자동 확보 실패", body.textContent + outputNotice, button));
      banner.append(heading, body, button);
      detail.prepend(banner);
    }
    if (banner.querySelector("p").textContent !== activeMessage) banner.querySelector("p").textContent = activeMessage;
  }

  // Observe API responses without changing URLs, headers, authentication or retries.
  const upstreamFetch = window.fetch.bind(window);
  window.fetch = async function (...args) {
    const response = await upstreamFetch(...args);
    try {
      const input = args[0];
      const url = new URL(typeof input === "string" ? input : input.url || String(input), location.href);
      if (response.ok && url.origin === location.origin && /(?:^|\/)api\/invoices(?:\/\d+(?:\/purchase-analysis|\/quote)?)?\/?$/.test(url.pathname)) {
        response.clone().json().then(payload => {
          const records = Array.isArray(payload) ? payload : [payload];
          for (const record of records) {
            if (!record?.id) continue;
            invoices.set(Number(record.id), { ...record.raw, ...record.raw?.data, ...record.data, ...record });
          }
          scheduleRender();
        }).catch(() => {});
      }
    } catch { /* A feedback failure must not interrupt the original request. */ }
    return response;
  };

  // Covers batch validation returned by the server through the existing error handler.
  const originalAlert = window.alert.bind(window);
  window.alert = function (message) {
    if (String(message).startsWith("부서 입력 필요")) {
      present("부서를 입력해 주세요", String(message));
      return;
    }
    return originalAlert(message);
  };

  document.addEventListener("click", event => {
    if (!event.target.closest?.("#erpQueueButton")) return;
    if (!document.getElementById("pageTitle")?.textContent.includes("구매")) return;
    const selected = selectedIds();
    if (selected.length !== 1 || selected[0] !== detailId()) return; // Batch: server checks every invoice.
    const savedOutput = document.querySelector('#outputSetPanel [data-output-action="saved_output"]');
    if (savedOutput && !savedOutput.disabled) return; // Printing existing documents never re-enters ERP.
    const missing = [...document.querySelectorAll("#purchaseDetailBody tr[data-analysis-index]")].filter(row => {
      const account = row.querySelector('[data-item-field="account"]')?.value;
      const dept = row.querySelector('[data-item-field="dept"]')?.value.trim();
      return ["집기비품", "컴퓨터소프트웨어"].includes(account) && (!dept || dept === "소모품");
    });
    if (!missing.length) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const lines = missing.slice(0, 4).map(row => `${Number(row.dataset.analysisIndex) + 1}행 ${row.querySelector('[data-item-field="name"]')?.value || "품목"}`);
    if (missing.length > 4) lines.push(`외 ${missing.length - 4}개 품목`);
    present("부서를 입력해 주세요", `#${selected[0]}\n${lines.join("\n")}\n\n집기비품·컴퓨터소프트웨어는 부서가 필요합니다. 품목별 부서를 입력한 뒤 다시 실행해 주세요. 작업은 등록되지 않았습니다.`, missing[0].querySelector('[data-item-field="dept"]'));
  }, true);

  function initialize() {
    const observer = new MutationObserver(scheduleRender);
    for (const id of ["purchaseDetailBody", "purchaseDetailTitle", "invoicesTable"]) {
      const element = document.getElementById(id);
      if (element) observer.observe(element, { childList: true, subtree: true });
    }
    document.addEventListener("change", scheduleRender);
    scheduleRender();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize, { once: true });
  else initialize();
})();
