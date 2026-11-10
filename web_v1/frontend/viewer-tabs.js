(() => {
  "use strict";

  function escape(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  }

  function createViewer(prefix, api) {
    const el = {};
    ["TableList", "TableTitle", "TableSummary", "SearchForm", "SearchInput", "LimitSelect", "SearchButton",
      "RefreshButton", "ErrorBox", "DataTable", "PreviousButton", "NextButton"].forEach(name => {
      el[name] = document.getElementById(prefix + name);
    });
    let tables = [], selectedTable = "", offset = 0, total = 0, request = null, revision = 0, busy = false;

    function error(message) {
      el.ErrorBox.textContent = message || "";
      el.ErrorBox.classList.toggle("hidden", !message);
    }

    function controls() {
      el.SearchButton.disabled = busy;
      el.RefreshButton.disabled = busy;
      el.PreviousButton.disabled = busy || offset === 0;
      el.NextButton.disabled = busy || offset + Number(el.LimitSelect.value) >= total;
      el.DataTable.setAttribute("aria-busy", String(busy));
    }

    function renderTables() {
      el.TableList.innerHTML = tables.length ? tables.map(table => `
        <button class="${table.name === selectedTable ? "active" : ""}" type="button"
          data-table="${escape(table.name)}" aria-pressed="${table.name === selectedTable}">
          <strong>${escape(table.label || table.name)}</strong><span>${Number(table.count || 0).toLocaleString("ko-KR")}건</span>
        </button>`).join("") : '<p class="admin-db-empty">조회 항목 없음</p>';
    }

    function placeholder(text) {
      el.DataTable.querySelector("thead").innerHTML = "";
      el.DataTable.querySelector("tbody").innerHTML = `<tr><td class="empty-cell">${escape(text)}</td></tr>`;
    }

    function renderRows(data) {
      const columns = data.columns || [], labels = data.column_labels || {}, rows = data.rows || [];
      total = Number(data.total || 0);
      el.TableTitle.textContent = tables.find(table => table.name === selectedTable)?.label || data.table;
      el.TableSummary.textContent = `총 ${total.toLocaleString("ko-KR")}건 · ${rows.length ? offset + 1 : 0}–${offset + rows.length}건 표시`;
      el.DataTable.querySelector("thead").innerHTML = `<tr>${columns.map(column => `<th>${escape(labels[column] || column)}</th>`).join("")}</tr>`;
      el.DataTable.querySelector("tbody").innerHTML = rows.length ? rows.map(row => `<tr>${columns.map(column => {
        let text = row[column] == null ? "" : (typeof row[column] === "object" ? JSON.stringify(row[column]) : String(row[column]));
        if (prefix === "log" && column === "invoice_type") text = {purchase: "구매", regular: "정기"}[text] || text;
        if (prefix === "log" && column === "invoice_id" && text) text = "#" + text;
        return `<td class="${text.length > 80 ? "long-cell" : ""}" title="${escape(text)}">${escape(text.length > 500 ? text.slice(0, 500) + "…" : text)}</td>`;
      }).join("")}</tr>`).join("") : `<tr><td class="empty-cell" colspan="${Math.max(columns.length, 1)}">조회 결과 없음</td></tr>`;
    }

    async function load(withOverview = false) {
      if (!request) return;
      const mine = ++revision, client = request;
      busy = true;
      error("");
      placeholder("불러오는 중입니다.");
      el.TableSummary.textContent = "불러오는 중입니다.";
      controls();
      try {
        if (withOverview) {
          const overview = await client(api + "/overview");
          if (mine !== revision) return;
          tables = overview.tables || [];
          if (!tables.some(table => table.name === selectedTable)) {
            selectedTable = (tables.find(table => table.name === "invoices") || tables[0])?.name || "";
            offset = 0;
          }
          renderTables();
        }
        if (!selectedTable) {
          total = 0;
          el.TableSummary.textContent = "조회할 항목이 없습니다.";
          placeholder("조회할 항목이 없습니다.");
          return;
        }
        const params = new URLSearchParams({table: selectedTable, q: el.SearchInput.value,
          limit: el.LimitSelect.value, offset: String(offset)});
        const data = await client(api + "/table?" + params);
        if (mine !== revision) return;
        renderRows(data);
      } catch (err) {
        if (mine !== revision) return;
        total = 0;
        error(err.message || "조회 중 오류가 발생했습니다.");
        el.TableSummary.textContent = "조회하지 못했습니다.";
        placeholder("조건을 확인한 뒤 다시 조회해 주세요.");
      } finally {
        if (mine === revision) { busy = false; controls(); }
      }
    }

    el.TableList.addEventListener("click", event => {
      const button = event.target.closest("[data-table]");
      if (!button) return;
      selectedTable = button.dataset.table;
      offset = 0;
      renderTables();
      load();
    });
    el.SearchForm.addEventListener("submit", event => { event.preventDefault(); offset = 0; load(); });
    el.LimitSelect.addEventListener("change", () => { offset = 0; load(); });
    el.RefreshButton.addEventListener("click", () => load(true));
    el.PreviousButton.addEventListener("click", () => { offset = Math.max(0, offset - Number(el.LimitSelect.value)); load(); });
    el.NextButton.addEventListener("click", () => { offset += Number(el.LimitSelect.value); load(); });

    return {
      open(client) { request = client; return load(true); },
      select(table, query) { selectedTable = table; el.SearchInput.value = query; offset = 0; },
      reset() {
        revision++;
        request = null;
        tables = [];
        selectedTable = "";
        offset = total = 0;
        busy = false;
        el.SearchInput.value = "";
        el.LimitSelect.value = "100";
        el.TableTitle.textContent = "조회 항목 선택";
        el.TableSummary.textContent = "조회 항목을 선택하세요.";
        error("");
        renderTables();
        placeholder("조회 항목을 선택하세요.");
        controls();
      },
    };
  }

  window.AccountingLogViewer = createViewer("log", "/api/logs");
  window.AccountingDbViewer = createViewer("db", "/api/admin/db");
})();
