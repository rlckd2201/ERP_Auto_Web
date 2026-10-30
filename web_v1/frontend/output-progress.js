/* Observe existing invoice responses; preserve the portal's transport/authentication. */
(function () {
  "use strict";
  const records = new Map();
  const shortNames = {erp_voucher: "전표", tax_invoice: "세금계산서", approval_docs: "품의", expense_report: "현출"};
  let scheduled = false;
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  function button(text, action, cls = "button secondary") {
    const node = el("button", text, cls); node.type = "button";
    node.addEventListener("click", event => { event.stopPropagation(); action(); });
    return node;
  }
  function timeLabel(value) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "시각 확인 필요" : date.toLocaleString("ko-KR", {hour12: false});
  }
  function table(summary) {
    const wrap = el("div", "", "output-progress-scroll");
    const grid = el("table", "", "output-progress-table");
    const head = el("thead"), heading = el("tr");
    for (const text of ["문서", "PDF", "프린터 전송", "프린터 / 기록 시각"]) {
      const th = el("th", text); th.scope = "col"; heading.append(th);
    }
    head.append(heading); grid.append(head);
    const body = el("tbody");
    for (const doc of summary.documents || []) {
      const row = el("tr"), print = doc.print || {};
      row.append(el("td", doc.label));
      const pdf = el("td", doc.pdf_label);
      if (doc.pdf_error) pdf.append(el("small", doc.pdf_error));
      const transmission = el("td", print.label, `output-progress-${print.state}`);
      if (print.error) transmission.append(el("small", print.error));
      const destination = el("td", print.printer_name || "—");
      destination.append(el("small", timeLabel(print.at)));
      row.append(pdf, transmission, destination); body.append(row);
    }
    grid.append(body); wrap.append(grid); return wrap;
  }
  function modal(record, confirmRetry = false) {
    document.getElementById("outputProgressModal")?.remove();
    const summary = record.processing_status;
    const dialog = el("dialog", "", "output-progress-dialog"); dialog.id = "outputProgressModal";
    const title = el("h2", `#${record.id} ${confirmRetry ? "실패 문서 다시 출력" : "문서·출력 상태"}`);
    title.id = "outputProgressTitle"; dialog.setAttribute("aria-labelledby", title.id);
    dialog.append(title, el("p", summary.erp_label), table(summary));
    dialog.append(el("p", summary.notice, "output-progress-notice"));
    const actions = el("div", "", "output-progress-actions");
    if (confirmRetry) {
      const keys = summary.retry_doc_keys || [];
      const names = summary.documents.filter(doc => keys.includes(doc.key)).map(doc => doc.label).join(" · ");
      dialog.append(el("p", `재출력 대상: ${names}`, "output-progress-retry-list"));
      dialog.append(el("p", "이미 준비된 PDF를 전송합니다. ERP 입력은 실행하지 않습니다."));
      const mapping = typeof state !== "undefined" ? state.setupStatus?.capabilities?.printer_mapping || {} : {};
      const label = el("label", "출력 프린터 ", "output-progress-printer");
      const select = el("select"); select.id = "outputProgressPrinter";
      for (const [key, name] of [["pyeongtaek", "평택"], ["gimje", "김제"]]) {
        const printer = String(mapping[key] || "").trim();
        if (!printer || /microsoft print to pdf/i.test(printer)) continue;
        const option = el("option", `${name} · ${printer}`); option.value = key; select.append(option);
      }
      if ([...select.options].some(option => option.value === summary.printer_key)) select.value = summary.printer_key;
      label.append(select); dialog.append(label);
      const message = el("p", select.options.length ? "" : "프린터 매핑을 먼저 확인해 주세요.", "output-progress-error");
      message.setAttribute("role", "alert"); dialog.append(message);
      const confirm = button("선택한 프린터로 재출력", async () => {
        if (confirm.disabled) return;
        confirm.disabled = true;
        try {
          if (typeof startJob !== "function") throw new Error("업무 화면을 새로고침해 주세요.");
          await startJob("/api/jobs/output-set", {
            invoice_ids: [Number(record.id)], action: "print_individual", printer_key: select.value,
            expected_printer_name: String(mapping[select.value] || "").trim(),
            retry_token: summary.retry_token, existing_only: true,
          });
          dialog.close();
        } catch (error) { message.textContent = error.message; confirm.disabled = false; }
      }, "button primary output-progress-confirm");
      confirm.disabled = !select.options.length || !keys.length || summary.active || !summary.complete;
      actions.append(confirm);
    } else if (summary.retry_doc_keys?.length) {
      actions.append(button("실패 문서만 다시 출력", () => modal(record, true)));
    }
    actions.append(button("닫기", () => dialog.close(), "button ghost"));
    dialog.append(actions); document.body.append(dialog); dialog.showModal();
  }
  function compact(record) {
    const summary = record.processing_status;
    const wrap = el("div", "", "output-progress-compact");
    const chips = el("div", "", "output-progress-chips");
    for (const doc of summary.documents || []) {
      const print = doc.print || {}, name = shortNames[doc.key] || doc.label;
      let text = !doc.pdf_ready ? "미준비" : "PDF 준비";
      if (print.state === "sent") text = "전송 확인";
      else if (print.state === "submitted") text = "전송 요청";
      else if (print.state === "failed") text = "전송 실패";
      else if (print.state === "not_sent") text = "미전송";
      else if (print.state === "sending") text = "전송 중";
      else if (["unknown", "changed"].includes(print.state)) text = "확인 필요";
      const chip = el("span", `${name} · ${text}`, `output-progress-chip output-progress-${print.state}`);
      chip.title = `${doc.pdf_label} / ${print.label}`; chips.append(chip);
    }
    wrap.append(chips);
    const history = summary.documents.map(doc => doc.print).filter(print => print?.at).sort((a,b) => String(b.at).localeCompare(String(a.at)));
    if (history.length) wrap.append(el("small", `${history[0].printer_name || "프린터 미확인"} · ${timeLabel(history[0].at)}`));
    wrap.append(button("출력 상태 보기", () => modal(record), "output-progress-link"));
    return wrap;
  }
  function render() {
    scheduled = false;
    document.querySelectorAll("#invoicesTable tr[data-invoice-id]").forEach(row => {
      const record = records.get(Number(row.dataset.invoiceId));
      if (!record?.processing_status || row.cells.length < 3) return;
      const signature = JSON.stringify(record.processing_status), previous = row.querySelector(".output-progress-compact");
      if (previous?.dataset.signature === signature) return;
      previous?.remove(); const node = compact(record); node.dataset.signature = signature; row.cells[2].append(node);
    });
    const detail = document.getElementById("purchaseDetailBody");
    const id = Number(document.getElementById("purchaseDetailTitle")?.textContent.match(/#(\d+)/)?.[1]);
    const record = records.get(id);
    if (!detail || !record?.processing_status) return;
    const signature = JSON.stringify([id, record.processing_status]);
    const previous = detail.querySelector("#invoiceOutputProgress");
    if (previous?.dataset.signature === signature) return;
    previous?.remove();
    const panel = el("section", "", "output-progress-panel"); panel.id = "invoiceOutputProgress"; panel.dataset.signature = signature;
    const summary = record.processing_status;
    panel.append(el("h3", "문서·출력 상태"), el("p", summary.erp_label), table(summary), el("p", summary.notice, "output-progress-notice"));
    if (!summary.complete) panel.append(el("p", "일부 전송 기록을 확인하지 못했습니다. 잠시 후 다시 확인해 주세요.", "output-progress-error"));
    if (summary.active) panel.append(el("p", "처리가 진행 중입니다. 완료 후 출력 상태가 갱신됩니다."));
    if (summary.retry_doc_keys?.length) panel.append(button("실패 문서만 다시 출력", () => modal(record, true)));
    detail.prepend(panel);
  }
  function schedule() { if (!scheduled) { scheduled = true; requestAnimationFrame(render); } }
  const fetchBefore = window.fetch;
  window.fetch = async function (...args) {
    const response = await fetchBefore.apply(this, args);
    try {
      const url = new URL(typeof args[0] === "string" ? args[0] : args[0].url || String(args[0]), location.href);
      if (response.ok && url.origin === location.origin && /\/api\/invoices(?:\/\d+)?\/?$/.test(url.pathname)) {
        response.clone().json().then(value => {
          for (const record of Array.isArray(value) ? value : [value]) {
            if (record?.id && record.processing_status) records.set(Number(record.id), record);
          }
          schedule();
        }).catch(() => {});
      }
    } catch (_) { /* A failed observer must not change application requests. */ }
    return response;
  };
  new MutationObserver(schedule).observe(document.body, {childList: true, subtree: true});
  schedule();
})();
