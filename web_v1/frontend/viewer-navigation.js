/* Keep app.js byte-compatible with the portal's source adaptation contract.
   Add navigation through shared runtime hooks after the original script loads. */
(() => {
  "use strict";
  if (typeof state === "undefined" || typeof els === "undefined") return;

  const canViewDb = () => state.user?.id === "rlckd9646";
  state.activeTab = ["#logs", "#db"].includes(location.hash) ? location.hash.slice(1) : state.invoiceMode;
  Object.assign(els, {
    processingView: document.querySelector("#processingView"),
    logsView: document.querySelector("#logsView"),
    logsNavButton: document.querySelector("#logsNavButton"),
    dbView: document.querySelector("#dbView"),
    dbNavButton: document.querySelector("#dbNavButton"),
  });

  function renderNavigation(name) {
    els.processingView?.classList.toggle("hidden", ["logs", "db"].includes(state.activeTab));
    els.logsView?.classList.toggle("hidden", state.activeTab !== "logs");
    els.dbView?.classList.toggle("hidden", state.activeTab !== "db" || !canViewDb());
    els.dbNavButton?.classList.toggle("hidden", !canViewDb());
    [[els.purchaseNavButton, "purchase"], [els.regularNavButton, "regular"],
      [els.logsNavButton, "logs"], [els.dbNavButton, "db"]].forEach(([button, tab]) => {
      button?.classList.toggle("active", name === "app" && state.activeTab === tab);
    });
    [els.purchaseNavButton, els.regularNavButton, els.logsNavButton, els.dbNavButton, els.setupNavButton].forEach(button => {
      if (!button) return;
      if (button.classList.contains("active")) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
  }

  // Retain the original function in app.js for the portal adapter; replace only
  // its browser-time effect so no separate DB window is created.
  ensureAdminDbButton = function () { document.querySelector("#adminDbButton")?.remove(); };
  ensureAdminDbButton();

  const previousShowView = showView;
  showView = function (name) {
    previousShowView(name);
    renderNavigation(name);
  };

  const previousShowApp = showApp;
  showApp = async function (mode = state.activeTab) {
    let nextTab = ["purchase", "regular", "logs", "db"].includes(mode) ? mode : state.invoiceMode;
    if (nextTab === "db" && !canViewDb()) nextTab = "logs";
    const viewerTab = ["logs", "db"].includes(nextTab);
    state.activeTab = nextTab;
    const url = new URL(location.href);
    if (viewerTab) url.hash = nextTab;
    else if (["#logs", "#db"].includes(url.hash)) url.hash = "";
    if (url.href !== location.href) history.replaceState(history.state, "", url.href);
    if (!viewerTab) return previousShowApp(nextTab);
    applyModeUi();
    showView("app");
    state.setupWasReady = true;
    startSetupMonitor();
    startMailCollectMonitor();
    startJobNotificationMonitor();
    return (nextTab === "db" ? window.AccountingDbViewer : window.AccountingLogViewer).open(requestJson);
  };

  const previousClearLogin = clearLoginAndShowLogin;
  clearLoginAndShowLogin = function (...args) {
    window.AccountingLogViewer.reset();
    window.AccountingDbViewer.reset();
    return previousClearLogin(...args);
  };

  const previousSelectedLog = loadSelectedInvoiceLogs;
  loadSelectedInvoiceLogs = async function () {
    const ids = [...state.selectedInvoiceIds];
    if (ids.length !== 1) return;
    window.AccountingLogViewer.select("all", "#" + ids[0]);
    return showApp("logs");
  };
  els.invoiceLogButton.removeEventListener("click", previousSelectedLog);
  els.invoiceLogButton.addEventListener("click", loadSelectedInvoiceLogs);

  loadJobLog = async function (jobId) {
    window.AccountingLogViewer.select("jobs", jobId || "");
    return showApp("logs");
  };
  els.workLogToggleButton.addEventListener("click", event => {
    event.stopImmediatePropagation();
    loadJobLog(state.currentJobId);
  }, true);
  els.logsNavButton?.addEventListener("click", () => {
    if (setupReady()) showApp("logs");
  });
  els.dbNavButton?.addEventListener("click", () => {
    if (setupReady() && canViewDb()) showApp("db");
  });

  if (!els.appShell.classList.contains("hidden")) {
    showApp(state.activeTab).catch(error => console.error("Viewer navigation failed", error.message));
  } else {
    renderNavigation(els.setupView.classList.contains("hidden") ? "login" : "setup");
  }
})();
