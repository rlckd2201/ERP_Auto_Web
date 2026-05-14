const ONE_CLICK_OUTPUT_STORAGE_KEY = "accountingWebOneClickOutputTarget";
const ONE_CLICK_OUTPUT_TARGETS = new Set(["pdf", "pyeongtaek", "gimje"]);

const state = {
  user: (() => {
    try {
      return JSON.parse(localStorage.getItem("accountingWebUser") || "null");
    } catch {
      return null;
    }
  })(),
  setupStatus: null,
  appLoaded: false,
  currentJobId: null,
  eventSource: null,
  serviceWorkerReady: null,
  selectedInvoiceIds: new Set(),
  invoices: [],
  statusFilter: "all",
  invoicePageSize: 20,
  selectedInvoiceDetail: null,
  detailLoading: false,
  statusPanelOpen: false,
  workLogOpen: false,
  setupMonitorTimer: null,
  mailCollectTimer: null,
  setupWasReady: false,
  agentAutoStartAttempted: false,
  approvalPollTimer: null,
  oneClickOutputTarget: localStorage.getItem(ONE_CLICK_OUTPUT_STORAGE_KEY) || "",
  detailMode: localStorage.getItem("accountingWebDetailMode") === "1",
  invoiceMode: localStorage.getItem("accountingWebInvoiceMode") === "regular" ? "regular" : "purchase",
};

const els = {
  loginView: document.querySelector("#loginView"),
  setupView: document.querySelector("#setupView"),
  appShell: document.querySelector("#appShell"),
  loginForm: document.querySelector("#loginForm"),
  loginUserId: document.querySelector("#loginUserId"),
  loginPassword: document.querySelector("#loginPassword"),
  loginMessage: document.querySelector("#loginMessage"),
  setupSummary: document.querySelector("#setupSummary"),
  setupChecks: document.querySelector("#setupChecks"),
  setupRefreshButton: document.querySelector("#setupRefreshButton"),
  setupInstallButton: document.querySelector("#setupInstallButton"),
  setupContinueButton: document.querySelector("#setupContinueButton"),
  setupSavePrintersButton: document.querySelector("#setupSavePrintersButton"),
  setupOpenButton: document.querySelector("#setupOpenButton"),
  setupNavButton: document.querySelector("#setupNavButton"),
  purchaseNavButton: document.querySelector("#purchaseNavButton"),
  regularNavButton: document.querySelector("#regularNavButton"),
  pageTitle: document.querySelector("#pageTitle"),
  pageSubtitle: document.querySelector("#pageSubtitle"),
  invoicePanelTitle: document.querySelector("#invoicePanelTitle"),
  detailPanelTitle: document.querySelector("#detailPanelTitle"),
  printerMappingForm: document.querySelector("#printerMappingForm"),
  serverState: document.querySelector("#serverState"),
  serverVersion: document.querySelector("#serverVersion"),
  notifyState: document.querySelector("#notifyState"),
  detailModeButton: document.querySelector("#detailModeButton"),
  notifyButton: document.querySelector("#notifyButton"),
  statusToggleButton: document.querySelector("#statusToggleButton"),
  statusGrid: document.querySelector("#statusGrid"),
  purchaseCollectButton: document.querySelector("#purchaseCollectButton"),
  oneClickOutputTarget: document.querySelector("#oneClickOutputTarget"),
  demoButton: document.querySelector("#demoButton"),
  refreshButton: document.querySelector("#refreshButton"),
  refreshInvoicesButton: document.querySelector("#refreshInvoicesButton"),
  erpQueueButton: document.querySelector("#erpQueueButton"),
  retryInvoiceButton: document.querySelector("#retryInvoiceButton"),
  deleteInvoiceButton: document.querySelector("#deleteInvoiceButton"),
  invoiceLogButton: document.querySelector("#invoiceLogButton"),
  invoiceSelectAll: document.querySelector("#invoiceSelectAll"),
  invoicePageSize: document.querySelector("#invoicePageSize"),
  purchaseDetailTitle: document.querySelector("#purchaseDetailTitle"),
  purchaseDetailBody: document.querySelector("#purchaseDetailBody"),
  manualUploadButton: document.querySelector("#manualUploadButton"),
  manualUploadModal: document.querySelector("#manualUploadModal"),
  manualNewTaxInvoiceInput: document.querySelector("#manualNewTaxInvoiceInput"),
  manualNewQuoteInput: document.querySelector("#manualNewQuoteInput"),
  manualCreatePurchaseButton: document.querySelector("#manualCreatePurchaseButton"),
  taxInvoiceFileInput: document.querySelector("#taxInvoiceFileInput"),
  quoteFileInput: document.querySelector("#quoteFileInput"),
  voucherFileInput: document.querySelector("#voucherFileInput"),
  approvalFileInput: document.querySelector("#approvalFileInput"),
  expenseReportFileInput: document.querySelector("#expenseReportFileInput"),
  analyzePurchaseButton: document.querySelector("#analyzePurchaseButton"),
  saveAnalysisButton: document.querySelector("#saveAnalysisButton"),
  selectedCount: document.querySelector("#selectedCount"),
  invoiceLogTitle: document.querySelector("#invoiceLogTitle"),
  invoiceLogList: document.querySelector("#invoiceLogList"),
  jobTitle: document.querySelector("#jobTitle"),
  jobBadge: document.querySelector("#jobBadge"),
  progressBar: document.querySelector("#progressBar"),
  progressText: document.querySelector("#progressText"),
  mailCollectSummary: document.querySelector("#mailCollectSummary"),
  workLogToggleButton: document.querySelector("#workLogToggleButton"),
  workLogBox: document.querySelector("#workLogBox"),
  logList: document.querySelector("#logList"),
  jobsTable: document.querySelector("#jobsTable"),
  invoicesTable: document.querySelector("#invoicesTable"),
  statusFilterButtons: [...document.querySelectorAll("[data-status-filter]")],
  stages: [...document.querySelectorAll("[data-stage]")],
};

function isLocalhost() {
  return ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
}

function notificationNeedsHttps() {
  return !window.isSecureContext && !isLocalhost();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatTime(value) {
  const date = value ? new Date(value) : new Date();
  return date.toLocaleTimeString("ko-KR", { hour12: false });
}

function formatMoney(value) {
  const number = Number(value) || 0;
  return number ? number.toLocaleString("ko-KR") : "-";
}

function displayProcessor(value) {
  const text = String(value || "").trim();
  if (!text) return "-";
  const parts = text.split("-").map((part) => part.trim()).filter(Boolean);
  if (parts.length === 2 && parts[0] === parts[1]) return parts[0];
  return text;
}

function approvalPaths(data) {
  return Array.isArray(data.approval_pdf_paths) ? data.approval_pdf_paths.filter(Boolean) : [];
}

function compactApprovalError(error) {
  const text = String(error || "").trim();
  if (!text) return "";
  if (text.includes("greenlet") || text.includes("Playwright") || text.includes("_greenlet")) {
    return "품의결재본 자동 확보 런타임 오류: 운영서버에서 Playwright/greenlet 재설치가 필요합니다.";
  }
  return text.length > 180 ? `${text.slice(0, 180)}...` : text;
}

function approvalStatusText(data) {
  const paths = approvalPaths(data);
  if (paths.length) return `확보 완료 (${paths.length}건)`;
  const status = String(data.approval_fetch_status || "").toLowerCase();
  const error = compactApprovalError(data.approval_fetch_error);
  if (status === "running" || status === "pending") return "자동 확보 중";
  if (status === "error" || error) return `자동 확보 실패${error ? `: ${error}` : ""}`;
  const hasAnalysis = data.purchase_analysis_ready || (Array.isArray(data.items) && data.items.length);
  if (data.quote_path && hasAnalysis) return "자동 확보 대기";
  return "분석 후 자동 확보";
}

function singleSelectedInvoiceId() {
  const ids = [...state.selectedInvoiceIds];
  return ids.length === 1 ? ids[0] : null;
}

function invoiceTypeOf(invoice) {
  return String(invoice?.invoice_type || invoice?.raw?.invoice_type || "").toLowerCase();
}

function selectedInvoiceType() {
  const selectedId = singleSelectedInvoiceId();
  if (!selectedId) return "";
  const detailType = state.selectedInvoiceDetail?.invoice_type || state.selectedInvoiceDetail?.raw?.invoice_type;
  if (detailType) return String(detailType).toLowerCase();
  const invoice = state.invoices.find((row) => Number(row.id) === Number(selectedId));
  return String(invoice?.invoice_type || "").toLowerCase();
}

function applyModeUi() {
  const regular = state.invoiceMode === "regular";
  if (els.pageTitle) els.pageTitle.textContent = regular ? "정기 처리" : "구매 처리";
  if (els.pageSubtitle) {
    els.pageSubtitle.textContent = regular
      ? "정기 세금계산서를 확인하고 ERP 전표와 문서 세트를 처리합니다."
      : "메일 수집, PDF 저장, ERP 입력 큐 등록까지 운영서버에서 진행합니다.";
  }
  if (els.invoicePanelTitle) els.invoicePanelTitle.textContent = regular ? "정기 수신 내역" : "구매 수신 내역";
  if (els.detailPanelTitle) els.detailPanelTitle.textContent = regular ? "정기 상세" : "구매 상세";
  if (els.erpQueueButton) els.erpQueueButton.textContent = regular ? "정기 원클릭 처리" : "원클릭 처리";
  els.purchaseCollectButton?.classList.toggle("hidden", regular);
}

function setManualUploadOpen(open) {
  if (!els.manualUploadModal) return;
  els.manualUploadModal.classList.toggle("hidden", !open);
  document.body.classList.toggle("modal-open", open);
  if (!open) return;
  const selectedId = singleSelectedInvoiceId();
  const isPurchase = selectedInvoiceType() !== "regular";
  els.manualUploadModal.querySelectorAll("[data-upload-kind]").forEach((button) => {
    const purchaseOnly = ["quote", "approval", "expense_report"].includes(button.dataset.uploadKind);
    button.disabled = !selectedId || (purchaseOnly && !isPurchase);
    button.title = !selectedId ? "기존 건 첨부는 구매 건을 1개 선택해야 합니다." : (button.disabled ? "구매 처리 건에서만 첨부할 수 있습니다." : "");
  });
}

function triggerManualUpload(kind) {
  const inputMap = {
    tax_invoice: els.taxInvoiceFileInput,
    quote: els.quoteFileInput,
    voucher: els.voucherFileInput,
    approval: els.approvalFileInput,
    expense_report: els.expenseReportFileInput,
  };
  const input = inputMap[kind];
  if (!input) return;
  setManualUploadOpen(false);
  input.value = "";
  input.click();
}

function clearApprovalPoll() {
  if (!state.approvalPollTimer) return;
  clearTimeout(state.approvalPollTimer);
  state.approvalPollTimer = null;
}

function scheduleApprovalRefresh(invoiceId, data) {
  clearApprovalPoll();
  const status = String(data.approval_fetch_status || "").toLowerCase();
  if (status !== "running" && status !== "pending") return;
  state.approvalPollTimer = setTimeout(async () => {
    const selected = [...state.selectedInvoiceIds];
    if (selected.length !== 1 || selected[0] !== invoiceId) return;
    await refreshInvoices({ skipDetail: true });
    await loadOutputSet(invoiceId);
  }, 3000);
}

function setCollapsibleOpen(button, panel, isOpen, openText, closedText) {
  if (!button || !panel) return;
  panel.classList.toggle("hidden", !isOpen);
  button.setAttribute("aria-expanded", String(isOpen));
  button.textContent = isOpen ? openText : closedText;
}

function setStatusPanelOpen(isOpen) {
  state.statusPanelOpen = isOpen;
  setCollapsibleOpen(els.statusToggleButton, els.statusGrid, isOpen, "서버 상태 숨기기", "서버 상태 보기");
}

function setWorkLogOpen(isOpen) {
  state.workLogOpen = isOpen;
  setCollapsibleOpen(els.workLogToggleButton, els.workLogBox, isOpen, "작업 로그 숨기기", "작업 로그 보기");
}

function applyDetailMode() {
  document.body.classList.toggle("detail-mode", state.detailMode);
  document.body.classList.toggle("simple-mode", !state.detailMode);
  if (els.detailModeButton) {
    els.detailModeButton.textContent = state.detailMode ? "담당자모드" : "상세모드";
  }
  if (!state.detailMode) {
    setStatusPanelOpen(false);
    setWorkLogOpen(false);
  }
}

function toggleDetailMode() {
  state.detailMode = !state.detailMode;
  localStorage.setItem("accountingWebDetailMode", state.detailMode ? "1" : "0");
  applyDetailMode();
}

function statusClass(status) {
  const text = String(status || "");
  if (text.includes("처리완료") || text === "done") return "status-done";
  if (text.includes("오류") || text.includes("실패") || text === "error") return "status-error";
  if (text.includes("ERP")) return "status-erp";
  if (text.includes("처리중")) return "status-processing";
  if (text.includes("대기")) return "status-waiting";
  return "status-unknown";
}

function matchesStatusFilter(invoice) {
  if (state.statusFilter === "all") return true;
  const status = String(invoice.status || "");
  if (state.statusFilter === "ERP대기") return status.includes("ERP");
  return status === state.statusFilter;
}

function filteredInvoices() {
  return state.invoices.filter(matchesStatusFilter);
}

function visibleInvoices() {
  return filteredInvoices().slice(0, state.invoicePageSize);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { message: text };
    }
  }
  if (!response.ok) {
    const message = data.detail || data.message || `HTTP ${response.status}`;
    throw new Error(String(message).startsWith("Internal Server Error") ? "서버 내부 오류가 발생했습니다. 관리자에게 화면을 전달하세요." : message);
  }
  return data;
}

async function requestForm(url, formData) {
  const response = await fetch(url, { method: "POST", body: formData });
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { message: text };
    }
  }
  if (!response.ok) {
    const message = data.detail || data.message || `HTTP ${response.status}`;
    throw new Error(String(message).startsWith("Internal Server Error") ? "서버 내부 오류가 발생했습니다. 관리자에게 화면을 전달하세요." : message);
  }
  return data;
}

function setupReady() {
  return state.setupStatus?.ready === true;
}

function setupCapabilities() {
  return state.setupStatus?.capabilities || {};
}

function mappedDefaultOutputTarget() {
  const capabilities = setupCapabilities();
  const mapping = capabilities.printer_mapping || {};
  const defaultPrinter = String(capabilities.default_printer || "").trim();
  if (!defaultPrinter) return "pdf";
  if (String(mapping.pyeongtaek || "").trim() === defaultPrinter) return "pyeongtaek";
  if (String(mapping.gimje || "").trim() === defaultPrinter) return "gimje";
  if (String(mapping.pdf || "").trim() === defaultPrinter) return "pdf";
  return "pdf";
}

function currentOutputTarget() {
  if (ONE_CLICK_OUTPUT_TARGETS.has(state.oneClickOutputTarget)) return state.oneClickOutputTarget;
  return mappedDefaultOutputTarget();
}

function syncOneClickOutputTarget() {
  if (!els.oneClickOutputTarget) return;
  els.oneClickOutputTarget.value = currentOutputTarget();
}

function showView(name) {
  els.loginView?.classList.toggle("hidden", name !== "login");
  els.setupView?.classList.toggle("hidden", name !== "setup");
  els.appShell?.classList.toggle("hidden", name !== "app");
  els.purchaseNavButton?.classList.toggle("active", name === "app" && state.invoiceMode === "purchase");
  els.regularNavButton?.classList.toggle("active", name === "app" && state.invoiceMode === "regular");
  els.setupNavButton?.classList.toggle("active", name === "setup");
}

function checkClass(check) {
  return check.ok ? "ok" : "warn";
}

function missingCompaniesFromSetup() {
  return (state.setupStatus?.checks || [])
    .filter((check) => String(check.key || "").startsWith("company_") && !check.ok)
    .map((check) => String(check.label || "").split(":").pop().trim())
    .filter(Boolean);
}

function certificateMissingFromSetup() {
  return (state.setupStatus?.checks || []).some((check) => check.key === "https_certificate" && !check.ok);
}

function agentConnectedFromSetup() {
  return (state.setupStatus?.checks || []).some((check) => check.key === "agent" && check.ok);
}

function agentUpdateRequiredFromSetup() {
  return (state.setupStatus?.checks || []).some((check) => check.key === "agent_update" && !check.ok);
}

function clearLoginAndShowLogin(message = "") {
  localStorage.removeItem("accountingWebUser");
  state.user = null;
  state.setupStatus = null;
  state.appLoaded = false;
  state.setupWasReady = false;
  state.selectedInvoiceIds.clear();
  if (state.eventSource) {
    state.eventSource.close();
    state.eventSource = null;
  }
  stopSetupMonitor();
  stopMailCollectMonitor();
  showView("login");
  if (els.loginMessage) els.loginMessage.textContent = message;
}

function stopSetupMonitor() {
  if (state.setupMonitorTimer) {
    clearInterval(state.setupMonitorTimer);
    state.setupMonitorTimer = null;
  }
}

function startSetupMonitor() {
  if (state.setupMonitorTimer) return;
  state.setupMonitorTimer = setInterval(async () => {
    if (!state.user?.id || !state.setupWasReady) return;
    try {
      const status = await requestJson(`/api/setup/status?user_id=${encodeURIComponent(state.user.id)}`);
      renderSetupStatus(status);
      if (!status.ready && !agentConnectedFromSetup()) {
        clearLoginAndShowLogin("담당자 PC 필수 프로그램 연결이 끊겨 로그아웃되었습니다. 필수 프로그램을 다시 실행한 뒤 로그인하세요.");
      } else if (!status.ready) {
        showView("setup");
      }
    } catch (error) {
      clearLoginAndShowLogin(`필수환경 점검 중 오류가 발생해 로그아웃했습니다: ${error.message}`);
    }
  }, 5000);
}

function stopMailCollectMonitor() {
  if (state.mailCollectTimer) {
    clearInterval(state.mailCollectTimer);
    state.mailCollectTimer = null;
  }
}

function downloadUserPcInstaller() {
  const serverUrl = window.location.origin;
  const command = [
    "$ServerUrl = \"" + serverUrl + "\"",
    "$Bootstrap = \"$env:TEMP\\accounting_web_user_pc_bootstrap.ps1\"",
    "curl.exe -k -L --fail --output $Bootstrap \"$ServerUrl/api/setup/user-pc-bootstrap.ps1\"",
    "powershell -ExecutionPolicy Bypass -File $Bootstrap",
  ].join("\n");
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(command).catch(() => {});
  }
  if (els.setupSummary) {
    els.setupSummary.textContent = "담당자 PC 필수 프로그램 설치 명령을 클립보드에 복사했습니다. PowerShell에 붙여넣어 실행한 뒤 다시 점검을 누르세요.";
  }
  alert(`PowerShell에 아래 명령을 붙여넣어 실행하세요.\n\n${command}`);
}

function requestAgentStartByProtocol() {
  const url = `accountingweb://start?server=${encodeURIComponent(window.location.origin)}`;
  const link = document.createElement("a");
  link.href = url;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  setTimeout(() => link.remove(), 1000);
}

function autoStartAgentAfterLogin({ downloadFallback = false } = {}) {
  if (agentConnectedFromSetup()) return;
  if (!state.agentAutoStartAttempted) {
    state.agentAutoStartAttempted = true;
    if (els.setupSummary) {
      els.setupSummary.textContent = "담당자 PC 필수 프로그램 자동 실행을 요청했습니다. 브라우저 확인창이 나오면 열기를 누르세요.";
    }
    requestAgentStartByProtocol();
  }
  if (!downloadFallback) return;
  setTimeout(async () => {
    if (!state.user?.id || agentConnectedFromSetup()) return;
    try {
      const status = await loadSetupStatus({ showReadyApp: false });
      if (status && !agentConnectedFromSetup()) {
        downloadUserPcInstaller();
      }
    } catch {
      downloadUserPcInstaller();
    }
  }, 7000);
}

function renderPrinterMapping(status) {
  if (!els.printerMappingForm) return;
  const printers = status.capabilities?.printers || [];
  const mapping = status.capabilities?.printer_mapping || {};
  const keys = status.printer_keys || [];
  if (!keys.length) {
    els.printerMappingForm.innerHTML = '<div class="empty-cell">담당자 PC 필수 프로그램 연결 후 프린터 목록을 확인할 수 있습니다.</div>';
    return;
  }
  els.printerMappingForm.innerHTML = keys.map(({ key, label }) => {
    const selected = mapping[key] || "";
    const options = ['<option value="">선택 필요</option>']
      .concat(printers.map((name) => `<option value="${escapeHtml(name)}" ${name === selected ? "selected" : ""}>${escapeHtml(name)}</option>`))
      .join("");
    return `<label>${escapeHtml(label)}<select data-printer-key="${escapeHtml(key)}">${options}</select></label>`;
  }).join("");
}

function renderSetupStatus(status) {
  state.setupStatus = status;
  if (status.ready) {
    state.setupWasReady = true;
    startSetupMonitor();
  }
  if (!els.setupSummary || !els.setupChecks) return;
  const agentText = status.agent_id ? `담당자 PC 연결됨: ${status.agent_id}` : "담당자 PC 필수 프로그램 미연결";
  els.setupSummary.textContent = status.ready
    ? `필수환경 점검 완료. ${agentText}`
    : `필수환경 점검이 필요합니다. ${agentText}`;
  els.setupChecks.innerHTML = (status.checks || []).map((check) => `
    <article class="check-card ${checkClass(check)}">
      <span class="check-status">${escapeHtml(check.status || "")}</span>
      <strong>${escapeHtml(check.label || "")}</strong>
      <p>${escapeHtml(check.message || "")}</p>
    </article>
  `).join("");
  renderPrinterMapping(status);
  const agentConnected = agentConnectedFromSetup();
  const missingCompanies = missingCompaniesFromSetup();
  const certificateMissing = certificateMissingFromSetup();
  const installerMap = status.capabilities?.installers?.companies || {};
  const missingInstallers = missingCompanies.filter((company) => !installerMap[company]);
  if (els.setupInstallButton) {
    const agentUpdateRequired = agentUpdateRequiredFromSetup();
    els.setupInstallButton.textContent = !agentConnected || agentUpdateRequired ? "필수 프로그램 최신버전 설치파일 다운로드" : (status.ready ? "설치 완료" : "필수 프로그램 설치");
    els.setupInstallButton.disabled = Boolean(status.ready);
    els.setupInstallButton.title = !agentConnected
      ? "담당자 PC 필수 프로그램 설치 파일을 다운로드합니다."
      : (agentUpdateRequired
          ? "서버와 담당자 PC 필수 프로그램 버전이 달라 최신 설치 파일을 다시 실행해야 합니다."
          : (missingInstallers.length
              ? `서버 설치 파일 없음: ${missingInstallers.join(", ")}`
              : [
                  missingCompanies.length ? `${missingCompanies.join(", ")} 설치 요청` : "",
                  certificateMissing ? "WEB HTTPS 인증서 등록 요청" : "",
                ].filter(Boolean).join(" / ") || "ERP 법인 설치 항목과 인증서는 정상입니다."))
  }
  if (els.setupContinueButton) {
    els.setupContinueButton.disabled = !status.ready;
  }
  syncOneClickOutputTarget();
  updateSelectionUi();
}

async function loadSetupStatus({ showReadyApp = true } = {}) {
  if (!state.user?.id) {
    showView("login");
    return null;
  }
  const status = await requestJson(`/api/setup/status?user_id=${encodeURIComponent(state.user.id)}`);
  renderSetupStatus(status);
  if (status.ready && showReadyApp) {
    showApp();
  } else if (!status.ready) {
    showView("setup");
    if (!agentConnectedFromSetup() && state.setupWasReady) {
      autoStartAgentAfterLogin();
    }
  }
  return status;
}

async function openSetupSettings() {
  try {
    await loadSetupStatus({ showReadyApp: false });
    showView("setup");
  } catch (error) {
    alert(`설정 화면을 열지 못했습니다: ${error.message}`);
  }
}

async function showApp(mode = state.invoiceMode) {
  const nextMode = mode === "regular" ? "regular" : "purchase";
  const modeChanged = state.invoiceMode !== nextMode;
  state.invoiceMode = nextMode;
  localStorage.setItem("accountingWebInvoiceMode", state.invoiceMode);
  applyModeUi();
  showView("app");
  state.setupWasReady = true;
  startSetupMonitor();
  startMailCollectMonitor();
  if (state.appLoaded) {
    if (modeChanged) {
      state.selectedInvoiceIds.clear();
      state.selectedInvoiceDetail = null;
      await refreshInvoices({ forceDetailReload: true, force: true });
    } else {
      updateSelectionUi();
    }
    return;
  }
  state.appLoaded = true;
  await loadHealth();
  await refreshJobs();
  await refreshInvoices();
}

async function handleLogin(event) {
  event.preventDefault();
  if (els.loginMessage) els.loginMessage.textContent = "";
  state.setupStatus = null;
  state.agentAutoStartAttempted = false;
  autoStartAgentAfterLogin();
  try {
    const data = await requestJson("/api/login", {
      method: "POST",
      body: JSON.stringify({
        user_id: els.loginUserId.value.trim(),
        password: els.loginPassword.value,
      }),
    });
    state.user = data.user;
    localStorage.setItem("accountingWebUser", JSON.stringify(data.user));
    renderSetupStatus(data.setup);
    if (data.setup?.ready) await showApp();
    else {
      showView("setup");
      if (!agentConnectedFromSetup()) {
        autoStartAgentAfterLogin({ downloadFallback: true });
      }
    }
  } catch (error) {
    if (els.loginMessage) els.loginMessage.textContent = error.message;
  }
}

async function savePrinterMapping() {
  const mapping = {};
  els.printerMappingForm?.querySelectorAll("[data-printer-key]").forEach((select) => {
    if (select.value) mapping[select.dataset.printerKey] = select.value;
  });
  try {
    const data = await requestJson("/api/setup/printers", {
      method: "POST",
      body: JSON.stringify({ agent_id: state.setupStatus?.agent_id || "", mapping }),
    });
    renderSetupStatus(data.setup);
    alert("프린터 매핑을 저장했습니다. 담당자 PC 필수 프로그램이 다음 점검 때 로컬 설정에도 반영합니다.");
    await loadSetupStatus({ showReadyApp: false });
  } catch (error) {
    alert(error.message);
  }
}

async function requestSetupInstall() {
  if (!agentConnectedFromSetup() || agentUpdateRequiredFromSetup()) {
    downloadUserPcInstaller();
    return;
  }
  const companies = missingCompaniesFromSetup();
  const installCertificate = certificateMissingFromSetup();
  const installerMap = state.setupStatus?.capabilities?.installers?.companies || {};
  const missingInstallers = companies.filter((company) => !installerMap[company]);
  if (missingInstallers.length) {
    alert(`서버 설치 파일이 없습니다: ${missingInstallers.join(", ")}\n\n서버 C:\\ERP_DB\\installers에 법인별 ZIP을 넣은 뒤 다시 점검하세요.`);
    return;
  }
  if (!companies.length && !installCertificate) return;
  try {
    await requestJson("/api/setup/install", {
      method: "POST",
      body: JSON.stringify({ agent_id: state.setupStatus?.agent_id || "", companies, install_certificate: installCertificate }),
    });
    const targets = [...companies, ...(installCertificate ? ["WEB HTTPS 인증서"] : [])];
    els.setupSummary.textContent = `설치 작업을 담당자 PC 필수 프로그램에 등록했습니다: ${targets.join(", ")}`;
  } catch (error) {
    alert(error.message);
  }
}

function syncNotificationState() {
  if (!("Notification" in window)) {
    els.notifyState.textContent = "미지원";
    els.notifyButton.disabled = true;
    return;
  }
  if (notificationNeedsHttps()) {
    els.notifyState.textContent = "HTTPS 필요";
    els.notifyButton.disabled = false;
    return;
  }
  if (Notification.permission === "granted") els.notifyState.textContent = "허용됨";
  else if (Notification.permission === "denied") els.notifyState.textContent = "차단됨";
  else els.notifyState.textContent = "대기";
}

function setBusy(isBusy) {
  const gateBlocked = !setupReady();
  if (els.purchaseCollectButton) els.purchaseCollectButton.disabled = isBusy || gateBlocked;
  if (els.oneClickOutputTarget) els.oneClickOutputTarget.disabled = isBusy || gateBlocked;
  if (els.demoButton) els.demoButton.disabled = isBusy || gateBlocked;
  if (els.manualUploadButton) els.manualUploadButton.disabled = isBusy || gateBlocked;
  const detail = detailData(state.selectedInvoiceDetail);
  const regular = selectedInvoiceType() === "regular" || state.invoiceMode === "regular";
  els.analyzePurchaseButton.disabled = regular || isBusy || !detail.quote_path;
  els.saveAnalysisButton.disabled = isBusy || !(Array.isArray(detail.items) && detail.items.length);
  els.retryInvoiceButton.disabled = isBusy || state.selectedInvoiceIds.size === 0;
  els.deleteInvoiceButton.disabled = isBusy || state.selectedInvoiceIds.size === 0;
  if (isBusy) els.erpQueueButton.disabled = true;
  else updateSelectionUi();
}

function setBadge(status) {
  els.jobBadge.textContent = status;
  els.jobBadge.className = "status-badge";
  if (status === "done") els.jobBadge.classList.add("done");
  else if (status === "error") els.jobBadge.classList.add("error");
  else if (status && status !== "idle") els.jobBadge.classList.add("active");
  else els.jobBadge.classList.add("idle");
}

function setProgress(progress) {
  const value = Math.max(0, Math.min(100, Number(progress) || 0));
  els.progressBar.style.width = `${value}%`;
  els.progressText.textContent = `${value}%`;
}

function setStage(status) {
  els.stages.forEach((stage) => {
    stage.classList.toggle("active", stage.dataset.stage === status);
  });
}

function addLog(event) {
  const empty = els.logList.querySelector(".empty-log");
  if (empty) empty.remove();
  const line = document.createElement("div");
  line.className = "log-line";
  line.textContent = `[${formatTime(event.created_at)}] ${event.status} ${event.progress}% - ${event.message}`;
  els.logList.appendChild(line);
  line.scrollIntoView({ block: "nearest" });
}

function showNotification(title, body) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  const options = {
    body,
    tag: `accounting-web-v1-${Date.now()}`,
    renotify: true,
    requireInteraction: true,
    silent: false,
  };
  if (state.serviceWorkerReady) {
    state.serviceWorkerReady
      .then((registration) => registration.showNotification(title, options))
      .catch(() => new Notification(title, options));
    return;
  }
  new Notification(title, options);
}

async function requestNotification() {
  if (!("Notification" in window)) {
    els.notifyState.textContent = "미지원";
    return;
  }
  if (notificationNeedsHttps()) {
    els.notifyState.textContent = "HTTPS 필요";
    alert("운영서버 IP 접속은 HTTPS가 필요합니다. HTTPS 주소로 접속한 뒤 알림을 허용하세요.");
    return;
  }
  const permission = await Notification.requestPermission();
  syncNotificationState();
  if (permission === "granted") {
    showNotification("알림 허용 완료", "작업 완료 알림을 받을 수 있습니다.");
  }
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  if (!window.isSecureContext) return;
  state.serviceWorkerReady = navigator.serviceWorker
    .register("/assets/sw.js")
    .then(() => navigator.serviceWorker.ready)
    .catch(() => null);
}

async function loadHealth() {
  try {
    const data = await requestJson("/health");
    els.serverState.textContent = data.ok ? "정상" : "오류";
    els.serverVersion.textContent = data.version || "-";
  } catch (error) {
    els.serverState.textContent = "연결 실패";
    els.serverVersion.textContent = "-";
  }
  syncNotificationState();
}

async function loadMailCollectStatus() {
  if (!els.mailCollectSummary) return;
  try {
    const data = await requestJson("/api/mail-collect/status");
    const finishedAt = data.last_finished_at || data.last_started_at || "";
    const timeText = finishedAt ? formatTime(finishedAt) : "-";
    const savedCount = Number(data.saved_count) || 0;
    const analyzedCount = Number(data.auto_analyzed_count) || 0;
    const failedCount = Number(data.failed_count) || 0;
    if (data.running) {
      els.mailCollectSummary.textContent = "메일 자동 수집 중입니다.";
    } else if (data.status === "error") {
      const errorText = Array.isArray(data.errors) && data.errors.length ? ` · 오류 ${data.errors[0]}` : "";
      els.mailCollectSummary.textContent = `메일 자동 수집 오류 · 마지막 ${timeText}${errorText}`;
    } else {
      els.mailCollectSummary.textContent = `메일 자동 수집 · 마지막 ${timeText} · 신규 ${savedCount}건 · 자동분석 ${analyzedCount}건 · 실패 ${failedCount}건`;
    }
  } catch (error) {
    els.mailCollectSummary.textContent = `메일 자동 수집 상태 확인 실패: ${error.message}`;
  }
}

function startMailCollectMonitor() {
  if (state.mailCollectTimer) return;
  loadMailCollectStatus();
  state.mailCollectTimer = setInterval(loadMailCollectStatus, 60000);
}

async function refreshJobs() {
  const jobs = await requestJson("/api/jobs");
  if (!jobs.length) {
    els.jobsTable.innerHTML = '<tr><td colspan="5" class="empty-cell">작업 내역 없음</td></tr>';
    return;
  }
  els.jobsTable.innerHTML = jobs.map((job) => `
    <tr>
      <td>${escapeHtml(job.status)}</td>
      <td>${escapeHtml(job.title)}</td>
      <td>${escapeHtml(job.progress)}%</td>
      <td>${escapeHtml(job.message)}</td>
      <td><button class="table-button" data-job-log="${escapeHtml(job.id)}" type="button">보기</button></td>
    </tr>
  `).join("");
}

function updateSelectionUi() {
  if (!els.selectedCount || !els.erpQueueButton) return;
  const count = state.selectedInvoiceIds.size;
  const filtered = filteredInvoices();
  const visible = visibleInvoices();
  const selectedVisible = state.invoices.filter((item) => state.selectedInvoiceIds.has(item.id));
  const gateBlocked = !setupReady();
  const erpExecutable = !gateBlocked && count > 0 && selectedVisible.length === count && selectedVisible.every((item) => canRunErp(item));
  const blocked = selectedVisible.find((item) => !canRunErp(item));
  const actionName = state.invoiceMode === "regular" ? "정기 원클릭 처리" : "원클릭 처리";
  const blockedReason = gateBlocked ? `필수 프로그램 점검 완료 후 ${actionName}를 실행할 수 있습니다.` : (blocked ? `${actionName} 불가: #${blocked.id} ${invoiceReadinessText(blocked)}` : "");
  els.selectedCount.textContent = `선택 ${count}건 · 표시 ${visible.length}/${filtered.length}건`;
  els.erpQueueButton.disabled = !erpExecutable;
  els.erpQueueButton.title = erpExecutable ? `선택 건 ${actionName}` : blockedReason;
  syncOneClickOutputTarget();
  els.retryInvoiceButton.disabled = count === 0;
  els.deleteInvoiceButton.disabled = count === 0;
  els.invoiceLogButton.disabled = count !== 1;
  els.invoiceSelectAll.checked =
    visible.length > 0 && visible.every((item) => state.selectedInvoiceIds.has(item.id));
}

function renderInvoices() {
  const filtered = filteredInvoices();
  const invoices = visibleInvoices();
  if (!filtered.length) {
    const label = state.invoiceMode === "regular" ? "정기 수신 내역 없음" : "수신 내역 없음";
    els.invoicesTable.innerHTML = `<tr><td colspan="7" class="empty-cell">${label}</td></tr>`;
    updateSelectionUi();
    return;
  }
  els.invoicesTable.innerHTML = invoices.map((invoice) => `
    <tr class="${state.selectedInvoiceIds.has(invoice.id) ? "selected" : ""} ${statusClass(invoice.status)}" data-invoice-id="${invoice.id}">
      <td class="check-col">
        <input class="invoice-check" type="checkbox" ${state.selectedInvoiceIds.has(invoice.id) ? "checked" : ""} aria-label="선택">
      </td>
      <td><span class="invoice-status ${statusClass(invoice.status)}">${escapeHtml(invoice.status || "-")}</span></td>
      <td>${escapeHtml(invoice.vendor_name || invoice.subject || "-")}</td>
      <td>${escapeHtml(invoice.site_name || "-")}</td>
      <td>${formatMoney(invoice.total_sum)}</td>
      <td>${escapeHtml(invoice.received_at || "-")}</td>
      <td>${escapeHtml(displayProcessor(invoice.processor))}</td>
    </tr>
  `).join("");
  updateSelectionUi();
}

async function refreshInvoices(options = {}) {
  const invoices = await requestJson(`/api/invoices?mode=${encodeURIComponent(state.invoiceMode)}&limit=200`);
  state.invoices = invoices;
  state.selectedInvoiceIds = new Set([...state.selectedInvoiceIds].filter((id) => invoices.some((item) => item.id === id)));
  if (options.forceDetailReload) {
    state.selectedInvoiceDetail = null;
  }
  renderInvoices();
  if (options.skipDetail) return;
  await loadSelectedPurchaseDetail(options);
}

function detailData(invoice) {
  if (!invoice) return {};
  const raw = invoice.raw || {};
  return {
    ...raw,
    ...(raw.data || {}),
    ...(invoice.data || {}),
    ...invoice,
  };
}

function readinessText(data) {
  if (invoiceTypeOf(data) === "regular") return regularReadinessText(data);
  if (data.readiness_reason) return data.readiness_reason;
  if (!data.quote_path) return "견적서 필요";
  if (!data.purchase_analysis_ready && !(Array.isArray(data.items) && data.items.length)) return "분석 필요";
  const approvalStatus = String(data.approval_fetch_status || "").toLowerCase();
  if (approvalStatus === "running" || approvalStatus === "pending") return "품의 확보 중";
  if (approvalStatus === "error" || data.approval_fetch_error) return "품의 확보 실패";
  return "ERP 입력 가능";
}

function regularReadinessText(data) {
  if (data.readiness_reason && !String(data.readiness_reason).includes("견적서")) return data.readiness_reason;
  if (!(data.pdf_path || data.tax_invoice_pdf_path)) return "세금계산서 필요";
  const total = Number(data.total_sum || data.total_amount || data.amount || 0);
  if (!total) return "금액 확인 필요";
  return "ERP 입력 가능";
}

function canRunErp(invoice) {
  const data = detailData(invoice);
  if (invoiceTypeOf(invoice) === "regular" || invoiceTypeOf(data) === "regular") {
    return regularReadinessText(data) === "ERP 입력 가능";
  }
  return Boolean(
    data.quote_path &&
    (data.purchase_analysis_ready || (Array.isArray(data.items) && data.items.length))
  );
}

function invoiceReadinessText(invoice) {
  return readinessText(detailData(invoice));
}

function accountOptions(value) {
  const accounts = ["소모품비", "집기비품", "컴퓨터소프트웨어"];
  return accounts.map((account) => `<option value="${account}" ${account === value ? "selected" : ""}>${account}</option>`).join("");
}

function regularAccountOptions(value) {
  const accounts = ["지급수수료", "통신비", "소모품비", "컴퓨터소프트웨어", "집기비품"];
  return accounts.map((account) => `<option value="${account}" ${account === value ? "selected" : ""}>${account}</option>`).join("");
}

function outputStatusClass(status) {
  if (status === "exists") return "ok";
  if (status === "generate_needed") return "need";
  if (status === "failed") return "fail";
  return "missing";
}

function outputStatusText(status) {
  return {
    exists: "있음",
    missing: "누락",
    generate_needed: "생성필요",
    failed: "실패",
  }[status] || status || "-";
}

function outputTargetOptions(selectedValue) {
  return [
    ["pdf", "통합본 PDF 저장"],
    ["pyeongtaek", "평택 프린터"],
    ["gimje", "김제 프린터"],
  ].map(([value, label]) => `<option value="${value}" ${value === selectedValue ? "selected" : ""}>${label}</option>`).join("");
}

function renderOutputSetPanel(outputSet, invoiceId) {
  const docs = Array.isArray(outputSet?.docs) ? outputSet.docs : [];
  const ready = Boolean(outputSet?.ready);
  const canOutput = Boolean(outputSet?.can_output);
  const blockers = Array.isArray(outputSet?.blockers) ? outputSet.blockers : [];
  const outputMode = outputSet?.mode || (state.invoiceMode === "regular" ? "regular" : "purchase");
  const isPurchaseSet = outputMode === "purchase";
  const requiredDocText = isPurchaseSet ? "전표, 세금계산서, 품의, 현금결의서" : "전표, 세금계산서";
  const blockerText = ready
    ? "저장된 문서로 바로 출력할 수 있습니다."
    : (blockers.length ? `누락 문서: ${blockers.map((doc) => doc.label).join(", ")}` : "필수 문서가 준비되면 출력할 수 있습니다.");
  const printerOptions = [
    ["pdf", "PDF"],
    ["pyeongtaek", "평택"],
    ["gimje", "김제"],
  ].map(([value, label]) => `<option value="${value}">${label}</option>`).join("");
  return `
    <section id="outputSetPanel" class="output-set-panel" data-invoice-id="${escapeHtml(invoiceId || "")}">
      <div class="output-set-header">
        <div>
          <strong>문서 세트</strong>
          <p>${escapeHtml(outputSet ? blockerText : "문서 세트 상태를 확인하는 중입니다.")}</p>
        </div>
        <div class="output-set-actions admin-only">
          <select id="savedOutputTarget" class="saved-output-target" title="기존 문서 출력 대상">${outputTargetOptions(currentOutputTarget())}</select>
          <button class="button primary" type="button" data-output-action="saved_output" ${ready ? "" : "disabled"} title="${ready ? "저장된 문서 세트로 바로 출력" : `${requiredDocText}가 모두 있어야 합니다.`}">기존 문서 출력</button>
          <select id="outputPrinterKey" title="개별 출력 대상">${printerOptions}</select>
          <button class="button secondary" type="button" data-output-action="refresh">세트 상태 갱신</button>
          ${isPurchaseSet ? '<button class="button secondary" type="button" data-output-action="generate_expense_report">현금결의서 생성</button>' : ""}
          <button class="button primary" type="button" data-output-action="merged_pdf" ${canOutput ? "" : "disabled"}>통합본 PDF 저장</button>
          <button class="button secondary admin-only" type="button" data-output-action="individual_pdf" ${canOutput ? "" : "disabled"}>개별 PDF 저장</button>
          <button class="button secondary admin-only" type="button" data-output-action="print_individual" ${canOutput ? "" : "disabled"}>개별 출력</button>
        </div>
      </div>
      <div class="output-doc-grid">
        ${docs.length ? docs.map((doc) => `
          <article class="output-doc-card ${outputStatusClass(doc.status)}">
            <span>${escapeHtml(outputStatusText(doc.status))}</span>
            <strong>${escapeHtml(doc.label || doc.key || "")}</strong>
            <p title="${escapeHtml((doc.paths || []).join(", ") || doc.path || doc.message || "")}">${escapeHtml(doc.message || doc.path || "-")}</p>
          </article>
        `).join("") : '<div class="empty-cell">문서 세트 상태를 불러오지 못했습니다.</div>'}
      </div>
    </section>
  `;
}

async function loadOutputSet(invoiceId) {
  if (!invoiceId) return;
  try {
    const outputSet = await requestJson(`/api/invoices/${invoiceId}/output-set`);
    if (state.selectedInvoiceDetail?.id === invoiceId) {
      state.selectedInvoiceDetail.output_docs = outputSet;
      if (state.selectedInvoiceDetail.data) state.selectedInvoiceDetail.data.output_docs = outputSet;
    }
    const panel = document.querySelector(`#outputSetPanel[data-invoice-id="${CSS.escape(String(invoiceId))}"]`);
    if (panel) panel.outerHTML = renderOutputSetPanel(outputSet, invoiceId);
  } catch (error) {
    const panel = document.querySelector("#outputSetPanel");
    if (panel) {
      panel.querySelector(".output-set-header p").textContent = `문서 세트 상태 확인 실패: ${error.message}`;
    }
  }
}

function normalizedDept(item) {
  return (item.account || "소모품비") === "소모품비" ? "소모품" : (item.dept || "");
}

function guessRegularAccount(itemName, vendorName = "") {
  const text = `${itemName || ""} ${vendorName || ""}`.toLowerCase();
  const compact = `${itemName || ""}${vendorName || ""}`.replace(/\s+/g, "");
  if (compact.includes("동양정보통신") || compact.includes("대신아이씨티")) return "지급수수료";
  if (["kt", "케이티", "통신", "vpn", "sdwan", "오토에버", "autoever", "704100", "w001"].some((key) => text.includes(key))) return "통신비";
  return "지급수수료";
}

function regularItemsForDisplay(data, invoice) {
  const source = Array.isArray(data.items) && data.items.length ? data.items : [{
    name: data.item_name || data.item || invoice?.subject || "정기 서비스",
    qty: 1,
    inc_vat: Number(data.total_sum || invoice?.total_sum || 0),
  }];
  const totalSupply = Number(data.target_supply || data.total_supply || 0);
  const totalIncVat = source.reduce((sum, item) => sum + (Number(item.inc_vat || item.amount || item.total || 0) || 0), 0);
  let supplyRemainder = totalSupply;
  let maxIndex = 0;
  let maxAmount = -1;
  const rows = source.map((item, index) => {
    const incVat = Number(item.inc_vat || item.amount || item.total || 0) || 0;
    let supply = Number(item.supply || item.supply_amount || 0) || 0;
    if (!supply && totalSupply && totalIncVat) supply = Math.floor(totalSupply * (incVat / totalIncVat));
    if (!supply && incVat) supply = Math.round(incVat / 1.1);
    if (!supply && source.length === 1) supply = totalSupply;
    if (incVat > maxAmount) {
      maxAmount = incVat;
      maxIndex = index;
    }
    supplyRemainder -= supply;
    return {
      account: item.account || guessRegularAccount(item.name || item.item_name, data.vendor_name || invoice?.vendor_name),
      name: item.name || item.item_name || "정기 서비스",
      qty: Math.max(1, Number(item.qty || item.quantity || 1) || 1),
      supply,
      inc_vat: incVat,
    };
  });
  if (rows.length && supplyRemainder) rows[maxIndex].supply = (Number(rows[maxIndex].supply) || 0) + supplyRemainder;
  return rows;
}

function renderRegularDetail(invoice) {
  const ids = [...state.selectedInvoiceIds];
  clearApprovalPoll();
  if (els.detailPanelTitle) els.detailPanelTitle.textContent = "정기 상세";
  if (els.manualUploadButton) els.manualUploadButton.disabled = !setupReady();
  els.analyzePurchaseButton.classList.add("hidden");
  els.analyzePurchaseButton.disabled = true;
  els.saveAnalysisButton.textContent = "정기 저장";
  els.saveAnalysisButton.disabled = true;
  if (ids.length !== 1) {
    state.selectedInvoiceDetail = null;
    els.purchaseDetailTitle.textContent = ids.length ? "정기 건은 1개만 선택해야 상세를 편집할 수 있습니다." : "정기 건을 1개 선택하면 전표 데이터를 확인할 수 있습니다.";
    els.purchaseDetailBody.innerHTML = '<div class="empty-cell">선택된 정기 건이 없습니다.</div>';
    return;
  }
  if (!invoice) {
    els.purchaseDetailTitle.textContent = `#${ids[0]} 상세를 불러오는 중입니다.`;
    els.purchaseDetailBody.innerHTML = '<div class="empty-cell">상세 로딩 중</div>';
    return;
  }
  const data = detailData(invoice);
  const items = regularItemsForDisplay(data, invoice);
  els.purchaseDetailTitle.textContent = `#${invoice.id} ${invoice.vendor_name || data.vendor_name || invoice.subject || ""} · ${regularReadinessText(data)}`;
  els.saveAnalysisButton.disabled = !items.length;
  els.purchaseDetailBody.innerHTML = `
    <div class="detail-summary-grid">
      <label>세금계산서 <input value="${escapeHtml(invoice.pdf_path || data.pdf_path || "")}" readonly></label>
      <label>사업장 <input data-regular-field="site_name" value="${escapeHtml(data.site_name || invoice.site_name || "")}"></label>
      <label>거래처 <input data-regular-field="vendor_name" value="${escapeHtml(data.vendor_name || invoice.vendor_name || "")}"></label>
      <label>회계일 <input data-regular-field="invoice_date" value="${escapeHtml(data.invoice_date || data.issue_date || "")}"></label>
      <label>공급가액 <input data-regular-field="target_supply" value="${escapeHtml(data.target_supply || data.total_supply || 0)}"></label>
      <label>부가세 <input data-regular-field="total_tax" value="${escapeHtml(data.total_tax || data.tax || 0)}"></label>
      <label>합계 <input data-regular-field="total_sum" value="${escapeHtml(data.total_sum || invoice.total_sum || 0)}"></label>
    </div>
    ${renderOutputSetPanel(data.output_docs || invoice.output_docs || null, invoice.id)}
    <div class="analysis-table-wrap">
      <table class="analysis-table">
        <thead>
          <tr>
            <th>계정</th>
            <th>품목명</th>
            <th>수량</th>
            <th>공급가</th>
            <th>합계</th>
          </tr>
        </thead>
        <tbody>
          ${items.length ? items.map((item, index) => `
            <tr data-regular-index="${index}">
              <td><select data-item-field="account">${regularAccountOptions(item.account || "지급수수료")}</select></td>
              <td><input data-item-field="name" value="${escapeHtml(item.name || "")}"></td>
              <td><input data-item-field="qty" value="${escapeHtml(item.qty || 1)}"></td>
              <td><input data-item-field="supply" value="${escapeHtml(item.supply || 0)}"></td>
              <td><input data-item-field="inc_vat" value="${escapeHtml(item.inc_vat || 0)}"></td>
            </tr>
          `).join("") : '<tr><td colspan="5" class="empty-cell">정기 품목이 없습니다.</td></tr>'}
        </tbody>
      </table>
    </div>
  `;
  loadOutputSet(invoice.id);
}

function renderPurchaseDetail(invoice) {
  const ids = [...state.selectedInvoiceIds];
  clearApprovalPoll();
  if (els.detailPanelTitle) els.detailPanelTitle.textContent = "구매 상세";
  els.analyzePurchaseButton.classList.remove("hidden");
  els.analyzePurchaseButton.textContent = "분석";
  els.saveAnalysisButton.textContent = "분석 저장";
  if (els.manualUploadButton) els.manualUploadButton.disabled = !setupReady();
  els.analyzePurchaseButton.disabled = true;
  els.saveAnalysisButton.disabled = true;
  if (ids.length !== 1) {
    state.selectedInvoiceDetail = null;
    els.purchaseDetailTitle.textContent = ids.length ? "구매 건은 1개만 선택해야 상세를 편집할 수 있습니다." : "구매 건을 1개 선택하면 견적서 첨부와 분석을 진행할 수 있습니다.";
    els.purchaseDetailBody.innerHTML = '<div class="empty-cell">선택된 구매 건이 없습니다.</div>';
    return;
  }
  if (!invoice) {
    els.purchaseDetailTitle.textContent = `#${ids[0]} 상세를 불러오는 중입니다.`;
    els.purchaseDetailBody.innerHTML = '<div class="empty-cell">상세 로딩 중</div>';
    return;
  }
  const data = detailData(invoice);
  const items = Array.isArray(data.items) ? data.items : [];
  const approvalText = approvalStatusText(data);
  const approvalFiles = approvalPaths(data).join(", ");
  const approvalErrorRaw = String(data.approval_fetch_error || "").trim();
  const approvalError = compactApprovalError(approvalErrorRaw);
  els.purchaseDetailTitle.textContent = `#${invoice.id} ${invoice.vendor_name || data.vendor_name || invoice.subject || ""} · ${readinessText(data)}`;
  els.analyzePurchaseButton.disabled = !data.quote_path;
  els.saveAnalysisButton.disabled = !items.length;
  els.purchaseDetailBody.innerHTML = `
    <div class="detail-summary-grid">
      <label>세금계산서 <input value="${escapeHtml(invoice.pdf_path || "")}" readonly></label>
      <label>견적서 <input value="${escapeHtml(data.quote_path || "")}" readonly></label>
      <label>사업장 <input data-analysis-field="site_name" value="${escapeHtml(data.site_name || invoice.site_name || "")}"></label>
      <label>거래처 <input data-analysis-field="vendor_name" value="${escapeHtml(data.vendor_name || invoice.vendor_name || "")}"></label>
      <label>회계일 <input data-analysis-field="invoice_date" value="${escapeHtml(data.invoice_date || data.issue_date || "")}"></label>
      <label>주문번호 <input data-analysis-field="order_no" value="${escapeHtml(data.order_no || data.purchase_order_no || data.tax_order_no || data.quote_order_no || "")}"></label>
      <label>공급가액 <input data-analysis-field="target_supply" value="${escapeHtml(data.target_supply || data.total_supply || 0)}"></label>
      <label>부가세 <input data-analysis-field="total_tax" value="${escapeHtml(data.total_tax || data.tax || 0)}"></label>
      <label>합계 <input data-analysis-field="total_sum" value="${escapeHtml(data.total_sum || invoice.total_sum || 0)}"></label>
      <label>품의 확보상태 <input value="${escapeHtml(approvalText)}" title="${escapeHtml(approvalText)}" readonly></label>
      <label>품의결재본 <input value="${escapeHtml(approvalFiles)}" title="${escapeHtml(approvalFiles)}" readonly></label>
      ${approvalError ? `<label class="wide admin-only">품의 오류 <input value="${escapeHtml(approvalError)}" title="${escapeHtml(approvalErrorRaw || approvalError)}" readonly></label>` : ""}
    </div>
    ${renderOutputSetPanel(data.output_docs || invoice.output_docs || null, invoice.id)}
    <div class="analysis-table-wrap">
      <table class="analysis-table">
        <thead>
          <tr>
            <th>계정</th>
            <th>품목명</th>
            <th>수량</th>
            <th>공급가</th>
            <th>부서</th>
            <th>원문</th>
          </tr>
        </thead>
        <tbody>
          ${items.length ? items.map((item, index) => `
            <tr data-analysis-index="${index}" data-system-adjustment="${item.system_adjustment ? "1" : "0"}">
              <td><select data-item-field="account">${accountOptions(item.account || "소모품비")}</select></td>
              <td><input data-item-field="name" value="${escapeHtml(item.name || "")}"></td>
              <td><input data-item-field="qty" value="${escapeHtml(item.qty || 1)}"></td>
              <td><input data-item-field="supply" value="${escapeHtml(item.supply || 0)}"></td>
              <td><input data-item-field="dept" value="${escapeHtml(normalizedDept(item))}" ${(item.account || "소모품비") === "소모품비" ? "disabled" : ""}></td>
              <td><input data-item-field="raw_desc" value="${escapeHtml(item.raw_desc || "")}"></td>
            </tr>
          `).join("") : '<tr><td colspan="6" class="empty-cell">분석된 품목이 없습니다.</td></tr>'}
        </tbody>
      </table>
    </div>
  `;
  scheduleApprovalRefresh(invoice.id, data);
  loadOutputSet(invoice.id);
}

async function loadSelectedPurchaseDetail(options = {}) {
  const ids = [...state.selectedInvoiceIds];
  if (ids.length !== 1) {
    if (state.invoiceMode === "regular") renderRegularDetail(null);
    else renderPurchaseDetail(null);
    return;
  }
  const selectedId = ids[0];
  if (!options.force && state.selectedInvoiceDetail?.id === selectedId) {
    if (invoiceTypeOf(state.selectedInvoiceDetail) === "regular") renderRegularDetail(state.selectedInvoiceDetail);
    else renderPurchaseDetail(state.selectedInvoiceDetail);
    return;
  }
  if (state.invoiceMode === "regular") renderRegularDetail(null);
  else renderPurchaseDetail(null);
  try {
    state.detailLoading = true;
    state.selectedInvoiceDetail = await requestJson(`/api/invoices/${selectedId}`);
    if (invoiceTypeOf(state.selectedInvoiceDetail) === "regular") renderRegularDetail(state.selectedInvoiceDetail);
    else renderPurchaseDetail(state.selectedInvoiceDetail);
  } catch (error) {
    els.purchaseDetailTitle.textContent = `#${selectedId} 상세 로딩 실패`;
    els.purchaseDetailBody.innerHTML = `<div class="empty-cell">${escapeHtml(error.message)}</div>`;
  } finally {
    state.detailLoading = false;
  }
}

function collectAnalysisForm() {
  const body = els.purchaseDetailBody;
  const payload = {};
  body.querySelectorAll("[data-analysis-field]").forEach((input) => {
    const key = input.dataset.analysisField;
    payload[key] = ["target_supply", "total_tax", "total_sum"].includes(key) ? Number(String(input.value).replace(/[^0-9-]/g, "")) || 0 : input.value.trim();
  });
  payload.items = [...body.querySelectorAll("[data-analysis-index]")].map((row) => {
    const item = {};
    row.querySelectorAll("[data-item-field]").forEach((input) => {
      const key = input.dataset.itemField;
      item[key] = ["qty", "supply"].includes(key) ? Number(String(input.value).replace(/[^0-9-]/g, "")) || 0 : input.value.trim();
    });
    item.system_adjustment = row.dataset.systemAdjustment === "1";
    item.inc_vat = item.supply ? Math.round(item.supply * 1.1) : 0;
    item.is_a = item.account !== "소모품비";
    if (!item.is_a) item.dept = "소모품";
    return item;
  });
  payload.approval_pdf_paths = detailData(state.selectedInvoiceDetail).approval_pdf_paths || [];
  return payload;
}

function collectRegularForm() {
  const body = els.purchaseDetailBody;
  const payload = {};
  body.querySelectorAll("[data-regular-field]").forEach((input) => {
    const key = input.dataset.regularField;
    payload[key] = ["target_supply", "total_tax", "total_sum"].includes(key) ? Number(String(input.value).replace(/[^0-9-]/g, "")) || 0 : input.value.trim();
  });
  payload.items = [...body.querySelectorAll("[data-regular-index]")].map((row) => {
    const item = {};
    row.querySelectorAll("[data-item-field]").forEach((input) => {
      const key = input.dataset.itemField;
      item[key] = ["qty", "supply", "inc_vat"].includes(key) ? Number(String(input.value).replace(/[^0-9-]/g, "")) || 0 : input.value.trim();
    });
    if (!item.inc_vat && item.supply) item.inc_vat = Math.round(item.supply * 1.1);
    return item;
  });
  return payload;
}

async function saveCurrentAnalysisIfEditable() {
  const invoiceIds = [...state.selectedInvoiceIds];
  if (invoiceIds.length !== 1) return;
  if (selectedInvoiceType() === "regular") return;
  const invoiceId = invoiceIds[0];
  if (!els.purchaseDetailBody?.querySelector("[data-analysis-field]")) return;
  const payload = collectAnalysisForm();
  if (!Array.isArray(payload.items) || !payload.items.length) return;
  state.selectedInvoiceDetail = await requestJson(`/api/invoices/${invoiceId}/purchase-analysis`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

async function saveCurrentRegularIfEditable() {
  const invoiceIds = [...state.selectedInvoiceIds];
  if (invoiceIds.length !== 1) return;
  const invoiceId = invoiceIds[0];
  if (!els.purchaseDetailBody?.querySelector("[data-regular-field]")) return;
  const payload = collectRegularForm();
  if (!Array.isArray(payload.items) || !payload.items.length) return;
  state.selectedInvoiceDetail = await requestJson(`/api/invoices/${invoiceId}/regular-data`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

function schedulePostJobRefresh() {
  [0, 1500, 4000, 9000, 15000, 30000, 60000].forEach((delay) => {
    setTimeout(async () => {
      try {
        await refreshJobs();
        await loadMailCollectStatus();
        await refreshInvoices({ skipDetail: true });
      } catch {
        // 다음 주기에서 다시 갱신합니다.
      }
    }, delay);
  });
}

function finishJob(source, event) {
  setBusy(false);
  const title = event.status === "done" ? "작업 완료" : "작업 실패";
  showNotification(title, event.message);
  source.close();
  schedulePostJobRefresh();
}

function connectEvents(jobId) {
  if (state.eventSource) {
    state.eventSource.close();
    state.eventSource = null;
  }
  const source = new EventSource(`/api/jobs/${jobId}/events`);
  state.eventSource = source;
  source.addEventListener("job-progress", (message) => {
    const event = JSON.parse(message.data);
    setBadge(event.status);
    setProgress(event.progress);
    setStage(event.status);
    addLog(event);
    if (event.status === "done" || event.status === "error") {
      finishJob(source, event);
    }
  });
  source.onerror = () => {
    source.close();
    setBusy(false);
    schedulePostJobRefresh();
  };
}

async function startJob(url, body = null) {
  if (!setupReady()) {
    showView("setup");
    await loadSetupStatus({ showReadyApp: false });
    alert("필수 프로그램 점검이 완료되어야 업무 기능을 사용할 수 있습니다.");
    return;
  }
  setBusy(true);
  els.logList.innerHTML = "";
  setBadge("queued");
  setProgress(0);
  setStage("queued");
  setWorkLogOpen(state.detailMode);
  try {
    const job = await requestJson(url, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
    state.currentJobId = job.id;
    els.jobTitle.textContent = job.title;
    if (job.events?.[0]) addLog(job.events[0]);
    connectEvents(job.id);
    refreshJobs();
  } catch (error) {
    setBusy(false);
    alert(error.message);
  }
}

async function startErpQueue() {
  if (!setupReady()) {
    showView("setup");
    alert("필수 프로그램 점검 완료 후 원클릭 처리를 실행할 수 있습니다.");
    return;
  }
  const invoiceIds = [...state.selectedInvoiceIds];
  if (!invoiceIds.length) return;
  try {
    if (state.invoiceMode === "regular") await saveCurrentRegularIfEditable();
    else await saveCurrentAnalysisIfEditable();
    await refreshInvoices({ skipDetail: true });
  } catch (error) {
    alert(`ERP 입력 전 화면 저장 실패: ${error.message}`);
    return;
  }
  const url = state.invoiceMode === "regular" ? "/api/jobs/regular-one-click" : "/api/jobs/purchase-one-click";
  await startJob(url, {
    invoice_ids: invoiceIds,
    output_target: currentOutputTarget(),
    processor: "WEB v1.0",
  });
}

async function startOutputSet(action, options = {}) {
  if (!setupReady()) {
    showView("setup");
    alert("필수 프로그램 점검 완료 후 문서 세트 출력을 실행할 수 있습니다.");
    return;
  }
  const invoiceIds = [...state.selectedInvoiceIds];
  if (!invoiceIds.length) return;
  const printerKey = options.printerKey || document.querySelector("#outputPrinterKey")?.value || "pdf";
  await startJob("/api/jobs/output-set", {
    invoice_ids: invoiceIds,
    action,
    printer_key: printerKey,
    processor: "WEB v1.0",
    existing_only: Boolean(options.existingOnly),
  });
}

async function startSavedOutputSet() {
  const invoiceIds = [...state.selectedInvoiceIds];
  if (invoiceIds.length !== 1) return;
  const outputSet = detailData(state.selectedInvoiceDetail).output_docs || state.selectedInvoiceDetail?.output_docs;
  if (!outputSet?.ready) {
    const message = outputSet?.mode === "regular"
      ? "전표와 세금계산서가 모두 저장된 정기 건만 기존 문서 출력이 가능합니다."
      : "전표, 세금계산서, 품의, 현금결의서가 모두 저장된 건만 기존 문서 출력이 가능합니다.";
    alert(message);
    return;
  }
  const target = document.querySelector("#savedOutputTarget")?.value || currentOutputTarget();
  const action = target === "pdf" ? "merged_pdf" : "print_individual";
  await startOutputSet(action, { printerKey: target, existingOnly: true });
}

async function generateExpenseReport(invoiceId) {
  if (!invoiceId) return;
  try {
    state.selectedInvoiceDetail = await requestJson(`/api/invoices/${invoiceId}/expense-report`, { method: "POST" });
    await refreshInvoices({ force: true });
    await loadOutputSet(invoiceId);
    await loadInvoiceLogs(invoiceId);
  } catch (error) {
    alert(error.message);
  }
}

async function uploadInvoiceFile(invoiceId, input, url, options = {}) {
  const files = [...(input?.files || [])];
  if (!invoiceId || !files.length) return;
  const formData = new FormData();
  if (options.multiple) {
    files.forEach((file) => formData.append("files", file));
    if (options.replace) formData.append("replace", "true");
  } else {
    formData.append("file", files[0]);
  }
  try {
    state.selectedInvoiceDetail = await requestForm(url, formData);
    input.value = "";
    await refreshInvoices({ forceDetailReload: true, force: true });
    await loadOutputSet(invoiceId);
    await loadInvoiceLogs(invoiceId);
  } catch (error) {
    alert(error.message);
  }
}

async function createManualPurchaseInvoice() {
  const taxFile = els.manualNewTaxInvoiceInput?.files?.[0];
  const quoteFile = els.manualNewQuoteInput?.files?.[0];
  if (!taxFile) {
    alert("신규 등록에는 세금계산서 PDF가 필요합니다.");
    return;
  }
  const formData = new FormData();
  formData.append("tax_invoice", taxFile);
  if (quoteFile) formData.append("quote", quoteFile);
  try {
    const created = await requestForm("/api/invoices/manual-purchase", formData);
    const invoiceId = Number(created.id || created.invoice_id);
    if (els.manualNewTaxInvoiceInput) els.manualNewTaxInvoiceInput.value = "";
    if (els.manualNewQuoteInput) els.manualNewQuoteInput.value = "";
    setManualUploadOpen(false);
    if (invoiceId) {
      state.selectedInvoiceIds = new Set([invoiceId]);
      state.selectedInvoiceDetail = null;
    }
    await refreshInvoices({ forceDetailReload: true, force: true });
    if (invoiceId) {
      await loadOutputSet(invoiceId);
      await loadInvoiceLogs(invoiceId);
    }
  } catch (error) {
    alert(error.message);
  }
}

async function retrySelectedInvoices() {
  const invoiceIds = [...state.selectedInvoiceIds];
  if (!invoiceIds.length) return;
  await Promise.all(invoiceIds.map((id) => requestJson(`/api/invoices/${id}/retry`, { method: "POST" })));
  await refreshInvoices();
  if (invoiceIds.length === 1) await loadInvoiceLogs(invoiceIds[0]);
}

async function deleteSelectedInvoices() {
  const invoiceIds = [...state.selectedInvoiceIds];
  if (!invoiceIds.length) return;
  if (!confirm(`선택한 ${invoiceIds.length}건을 삭제할까요?`)) return;
  await Promise.all(invoiceIds.map((id) => requestJson(`/api/invoices/${id}`, { method: "DELETE" })));
  state.selectedInvoiceIds.clear();
  await refreshInvoices();
  els.invoiceLogTitle.textContent = "-";
  els.invoiceLogList.textContent = `로그를 볼 ${state.invoiceMode === "regular" ? "정기" : "구매"} 건을 선택하세요.`;
}

async function loadInvoiceLogs(invoiceId) {
  const logs = await requestJson(`/api/invoices/${invoiceId}/logs`);
  els.invoiceLogTitle.textContent = `#${invoiceId}`;
  if (!logs.length) {
    els.invoiceLogList.textContent = "기록된 로그가 없습니다.";
    return;
  }
  els.invoiceLogList.innerHTML = logs.map((log) => `
    <div class="detail-line ${escapeHtml(log.level)}">
      <span>${escapeHtml(log.created_at || "")}</span>
      <strong>${escapeHtml(log.level || "info")}</strong>
      <p>${escapeHtml(log.message || "")}</p>
    </div>
  `).join("");
}

async function loadSelectedInvoiceLogs() {
  const invoiceIds = [...state.selectedInvoiceIds];
  if (invoiceIds.length !== 1) return;
  await loadInvoiceLogs(invoiceIds[0]);
}

async function loadJobLog(jobId) {
  try {
    const job = await requestJson(`/api/jobs/${jobId}`);
    els.jobTitle.textContent = job.title;
    els.logList.innerHTML = "";
    if (!job.events?.length) {
      els.logList.innerHTML = '<p class="empty-log">기록된 작업 로그가 없습니다.</p>';
    } else {
      job.events.forEach(addLog);
    }
    setBadge(job.status);
    setProgress(job.progress);
    setStage(job.status);
    setWorkLogOpen(true);
    document.querySelector(".work-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    alert(`작업 로그를 불러오지 못했습니다: ${error.message}`);
  }
}

function toggleInvoice(invoiceId, checked) {
  if (checked) state.selectedInvoiceIds.add(invoiceId);
  else state.selectedInvoiceIds.delete(invoiceId);
  state.selectedInvoiceDetail = null;
  renderInvoices();
  loadSelectedPurchaseDetail();
}

function selectSingleInvoice(invoiceId) {
  state.selectedInvoiceIds = new Set([invoiceId]);
  state.selectedInvoiceDetail = null;
  renderInvoices();
  loadSelectedPurchaseDetail();
  loadInvoiceLogs(invoiceId);
}

els.loginForm?.addEventListener("submit", handleLogin);
els.setupRefreshButton?.addEventListener("click", () => loadSetupStatus({ showReadyApp: false }));
els.setupSavePrintersButton?.addEventListener("click", savePrinterMapping);
els.setupInstallButton?.addEventListener("click", requestSetupInstall);
els.setupContinueButton?.addEventListener("click", () => {
  if (setupReady()) showApp();
});
els.setupOpenButton?.addEventListener("click", openSetupSettings);
els.setupNavButton?.addEventListener("click", openSetupSettings);
els.purchaseNavButton?.addEventListener("click", () => {
  if (setupReady()) showApp("purchase");
});
els.regularNavButton?.addEventListener("click", () => {
  if (setupReady()) showApp("regular");
});
els.detailModeButton?.addEventListener("click", toggleDetailMode);
els.notifyButton.addEventListener("click", requestNotification);
els.statusToggleButton.addEventListener("click", () => setStatusPanelOpen(!state.statusPanelOpen));
els.workLogToggleButton.addEventListener("click", () => setWorkLogOpen(!state.workLogOpen));
els.purchaseCollectButton?.addEventListener("click", () => startJob("/api/jobs/purchase-mail-collect"));
els.oneClickOutputTarget?.addEventListener("change", (event) => {
  const value = event.target.value;
  state.oneClickOutputTarget = ONE_CLICK_OUTPUT_TARGETS.has(value) ? value : "pdf";
  localStorage.setItem(ONE_CLICK_OUTPUT_STORAGE_KEY, state.oneClickOutputTarget);
  syncOneClickOutputTarget();
});
els.demoButton.addEventListener("click", () => startJob("/api/jobs/demo"));
els.refreshButton.addEventListener("click", refreshJobs);
els.refreshInvoicesButton.addEventListener("click", refreshInvoices);
els.erpQueueButton.addEventListener("click", startErpQueue);
els.retryInvoiceButton.addEventListener("click", retrySelectedInvoices);
els.deleteInvoiceButton.addEventListener("click", deleteSelectedInvoices);
els.invoiceLogButton.addEventListener("click", loadSelectedInvoiceLogs);
els.invoiceSelectAll.addEventListener("change", (event) => {
  const visibleIds = visibleInvoices().map((item) => item.id);
  if (event.target.checked) {
    visibleIds.forEach((id) => state.selectedInvoiceIds.add(id));
  } else {
    visibleIds.forEach((id) => state.selectedInvoiceIds.delete(id));
  }
  state.selectedInvoiceDetail = null;
  renderInvoices();
  loadSelectedPurchaseDetail();
});
els.invoicesTable.addEventListener("change", (event) => {
  if (!event.target.classList.contains("invoice-check")) return;
  const row = event.target.closest("tr[data-invoice-id]");
  if (!row) return;
  toggleInvoice(Number(row.dataset.invoiceId), event.target.checked);
});
els.invoicesTable.addEventListener("click", (event) => {
  if (event.target.closest(".invoice-check, input, button, a, select, label")) return;
  const row = event.target.closest("tr[data-invoice-id]");
  if (!row) return;
  selectSingleInvoice(Number(row.dataset.invoiceId));
});
els.invoicesTable.addEventListener("dblclick", (event) => {
  const row = event.target.closest("tr[data-invoice-id]");
  if (!row) return;
  selectSingleInvoice(Number(row.dataset.invoiceId));
});
if (els.manualUploadButton) els.manualUploadButton.addEventListener("click", () => {
  setManualUploadOpen(true);
});
if (els.manualUploadModal) {
  els.manualUploadModal.addEventListener("click", (event) => {
    if (event.target === els.manualUploadModal || event.target.closest("[data-upload-modal-close]")) {
      setManualUploadOpen(false);
      return;
    }
    const button = event.target.closest("[data-upload-kind]");
    if (!button || button.disabled) return;
    triggerManualUpload(button.dataset.uploadKind);
  });
}
els.manualCreatePurchaseButton?.addEventListener("click", createManualPurchaseInvoice);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") setManualUploadOpen(false);
});
if (els.taxInvoiceFileInput) els.taxInvoiceFileInput.addEventListener("change", async (event) => {
  const invoiceId = singleSelectedInvoiceId();
  await uploadInvoiceFile(invoiceId, event.target, `/api/invoices/${invoiceId}/tax-invoice`);
});
if (els.quoteFileInput) els.quoteFileInput.addEventListener("change", async (event) => {
  const invoiceId = singleSelectedInvoiceId();
  await uploadInvoiceFile(invoiceId, event.target, `/api/invoices/${invoiceId}/quote`);
});
if (els.voucherFileInput) els.voucherFileInput.addEventListener("change", async (event) => {
  const invoiceId = singleSelectedInvoiceId();
  await uploadInvoiceFile(invoiceId, event.target, `/api/invoices/${invoiceId}/voucher`);
});
if (els.approvalFileInput) els.approvalFileInput.addEventListener("change", async (event) => {
  const invoiceId = singleSelectedInvoiceId();
  await uploadInvoiceFile(invoiceId, event.target, `/api/invoices/${invoiceId}/approval`, { multiple: true, replace: true });
});
if (els.expenseReportFileInput) els.expenseReportFileInput.addEventListener("change", async (event) => {
  const invoiceId = singleSelectedInvoiceId();
  await uploadInvoiceFile(invoiceId, event.target, `/api/invoices/${invoiceId}/expense-report-file`);
});
els.purchaseDetailBody.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-output-action]");
  if (!button) return;
  const action = button.dataset.outputAction;
  const invoiceIds = [...state.selectedInvoiceIds];
  if (invoiceIds.length !== 1) return;
  if (action === "refresh") {
    await loadOutputSet(invoiceIds[0]);
    return;
  }
  if (action === "generate_expense_report") {
    await generateExpenseReport(invoiceIds[0]);
    return;
  }
  if (action === "saved_output") {
    await startSavedOutputSet();
    return;
  }
  await startOutputSet(action);
});
els.purchaseDetailBody.addEventListener("change", async (event) => {
  if (event.target.matches?.("[data-output-voucher-input]")) {
    const invoiceIds = [...state.selectedInvoiceIds];
    const file = event.target.files?.[0];
    if (invoiceIds.length !== 1 || !file) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
      state.selectedInvoiceDetail = await requestForm(`/api/invoices/${invoiceIds[0]}/voucher`, formData);
      event.target.value = "";
      await refreshInvoices({ forceDetailReload: true, force: true });
      await loadInvoiceLogs(invoiceIds[0]);
      await loadOutputSet(invoiceIds[0]);
    } catch (error) {
      alert(error.message);
    }
    return;
  }
  if (event.target.dataset.itemField !== "account") return;
  const row = event.target.closest("[data-analysis-index]");
  const dept = row?.querySelector('[data-item-field="dept"]');
  if (!dept) return;
  if (event.target.value === "소모품비") {
    dept.value = "소모품";
    dept.disabled = true;
  } else {
    if (dept.value === "소모품") dept.value = "";
    dept.disabled = false;
  }
});
els.analyzePurchaseButton.addEventListener("click", async () => {
  const invoiceIds = [...state.selectedInvoiceIds];
  if (invoiceIds.length !== 1) return;
  await startJob("/api/jobs/purchase-analyze", {
    invoice_ids: invoiceIds,
    processor: "WEB v1.0",
  });
});
els.saveAnalysisButton.addEventListener("click", async () => {
  const invoiceIds = [...state.selectedInvoiceIds];
  if (invoiceIds.length !== 1) return;
  try {
    if (state.invoiceMode === "regular") await saveCurrentRegularIfEditable();
    else await saveCurrentAnalysisIfEditable();
    await refreshInvoices({ skipDetail: true });
  } catch (error) {
    alert(error.message);
  }
});
els.jobsTable.addEventListener("click", (event) => {
  const button = event.target.closest("[data-job-log]");
  if (!button) return;
  loadJobLog(button.dataset.jobLog);
});
els.invoicePageSize.addEventListener("change", (event) => {
  state.invoicePageSize = Number(event.target.value) || 20;
  renderInvoices();
});
els.statusFilterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.statusFilter = button.dataset.statusFilter || "all";
    els.statusFilterButtons.forEach((item) => item.classList.toggle("active", item === button));
    renderInvoices();
  });
});

async function bootstrap() {
  applyDetailMode();
  registerServiceWorker();
  if (!state.user?.id) {
    showView("login");
    return;
  }
  try {
    await loadSetupStatus();
  } catch (error) {
    clearLoginAndShowLogin(error.message);
  }
}

bootstrap();
