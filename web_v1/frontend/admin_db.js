const state = {
  tables: [],
  selectedTable: "",
};

const els = {
  dbPath: document.querySelector("#dbPath"),
  tableList: document.querySelector("#tableList"),
  tableTitle: document.querySelector("#tableTitle"),
  tableSummary: document.querySelector("#tableSummary"),
  searchInput: document.querySelector("#searchInput"),
  limitSelect: document.querySelector("#limitSelect"),
  searchButton: document.querySelector("#searchButton"),
  refreshButton: document.querySelector("#refreshButton"),
  errorBox: document.querySelector("#errorBox"),
  dataTable: document.querySelector("#dataTable"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function requestJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!response.ok) {
    const message = data?.detail || text || `HTTP ${response.status}`;
    throw new Error(message);
  }
  return data;
}

function showError(message) {
  if (!els.errorBox) return;
  els.errorBox.textContent = message || "";
  els.errorBox.classList.toggle("hidden", !message);
}

function shortCell(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  const text = String(value);
  return text.length > 500 ? `${text.slice(0, 500)}...` : text;
}

function renderTables() {
  if (!els.tableList) return;
  if (!state.tables.length) {
    els.tableList.innerHTML = '<div class="admin-db-empty">테이블 없음</div>';
    return;
  }
  els.tableList.innerHTML = state.tables.map((table) => `
    <button class="${table.name === state.selectedTable ? "active" : ""}" type="button" data-table="${escapeHtml(table.name)}">
      <strong>${escapeHtml(table.name)}</strong>
      <span>${Number(table.count || 0).toLocaleString("ko-KR")}건</span>
    </button>
  `).join("");
}

function renderRows(data) {
  const thead = els.dataTable?.querySelector("thead");
  const tbody = els.dataTable?.querySelector("tbody");
  if (!thead || !tbody) return;
  const columns = data.columns || [];
  if (!columns.length) {
    thead.innerHTML = "";
    tbody.innerHTML = '<tr><td class="empty-cell">컬럼 없음</td></tr>';
    return;
  }
  thead.innerHTML = `<tr>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>`;
  if (!data.rows?.length) {
    tbody.innerHTML = `<tr><td class="empty-cell" colspan="${columns.length}">조회 결과 없음</td></tr>`;
    return;
  }
  tbody.innerHTML = data.rows.map((row) => `
    <tr>
      ${columns.map((column) => {
        const value = shortCell(row[column]);
        const className = String(value).length > 80 ? "long-cell" : "";
        return `<td class="${className}" title="${escapeHtml(value)}">${escapeHtml(value)}</td>`;
      }).join("")}
    </tr>
  `).join("");
}

async function loadOverview() {
  showError("");
  const overview = await requestJson("/api/admin/db/overview");
  state.tables = overview.tables || [];
  if (els.dbPath) els.dbPath.textContent = overview.db_path || "";
  if (!state.selectedTable && state.tables.length) {
    const preferred = state.tables.find((table) => table.name === "invoices") || state.tables[0];
    state.selectedTable = preferred.name;
  }
  renderTables();
  if (state.selectedTable) await loadTable();
}

async function loadTable() {
  if (!state.selectedTable) return;
  showError("");
  const params = new URLSearchParams({
    table: state.selectedTable,
    q: els.searchInput?.value || "",
    limit: els.limitSelect?.value || "100",
  });
  const data = await requestJson(`/api/admin/db/table?${params.toString()}`);
  if (els.tableTitle) els.tableTitle.textContent = data.table;
  if (els.tableSummary) {
    els.tableSummary.textContent = `총 ${Number(data.total || 0).toLocaleString("ko-KR")}건 중 ${Number(data.rows?.length || 0).toLocaleString("ko-KR")}건 표시`;
  }
  renderRows(data);
}

els.tableList?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-table]");
  if (!button) return;
  state.selectedTable = button.dataset.table || "";
  renderTables();
  try {
    await loadTable();
  } catch (error) {
    showError(error.message);
  }
});

els.searchButton?.addEventListener("click", async () => {
  try {
    await loadTable();
  } catch (error) {
    showError(error.message);
  }
});

els.searchInput?.addEventListener("keydown", async (event) => {
  if (event.key !== "Enter") return;
  try {
    await loadTable();
  } catch (error) {
    showError(error.message);
  }
});

els.limitSelect?.addEventListener("change", async () => {
  try {
    await loadTable();
  } catch (error) {
    showError(error.message);
  }
});

els.refreshButton?.addEventListener("click", async () => {
  try {
    await loadOverview();
  } catch (error) {
    showError(error.message);
  }
});

loadOverview().catch((error) => showError(error.message));
