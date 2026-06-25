const state = {
  selectedJobId: "",
  jobs: [],
};

const statusText = {
  queued: "대기",
  claimed: "수락",
  running: "진행",
  done: "완료",
  error: "오류",
  cancelled: "취소",
};

function money(value) {
  return Number(value || 0).toLocaleString("ko-KR");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function badge(status) {
  const text = statusText[status] || status || "-";
  return `<span class="badge ${status}">${escapeHtml(text)}</span>`;
}

function setDetailStatus(status) {
  const detailStatus = document.querySelector("#detailStatus");
  detailStatus.className = `badge ${status}`;
  detailStatus.textContent = statusText[status] || status || "-";
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || response.statusText);
  }
  return data;
}

async function loadSettings() {
  const settings = await fetchJson("/api/settings");
  document.querySelector("#accountingDate").value = settings.default_accounting_date;
  document.querySelector("#agentTarget").textContent = `Agent ${settings.target_agent_ip} / ${settings.target_agent_id}`;
  const select = document.querySelector("#companyKey");
  select.innerHTML = "";
  settings.managers.forEach((manager) => {
    const option = document.createElement("option");
    option.value = manager.key;
    option.textContent = manager.label;
    select.appendChild(option);
  });
}

function renderJobs(jobs) {
  state.jobs = jobs;
  document.querySelector("#queueCount").textContent = `${jobs.length}건`;
  const rows = document.querySelector("#jobRows");
  rows.innerHTML = "";
  if (!jobs.length) {
    rows.innerHTML = `<tr><td colspan="4" class="emptyState">대기 중인 작업이 없습니다.</td></tr>`;
    return;
  }
  jobs.forEach((job) => {
    const row = document.createElement("tr");
    row.className = "jobRow";
    row.dataset.jobId = job.id;
    const title = escapeHtml(job.title);
    row.innerHTML = `
      <td>${badge(job.status)}</td>
      <td class="titleCell" title="${title}">${title}</td>
      <td>${escapeHtml(job.accounting_date)}</td>
      <td>
        <div class="progressTrack" title="${job.progress}%">
          <div class="progressBar" style="width:${job.progress}%"></div>
        </div>
      </td>
    `;
    row.addEventListener("click", () => selectJob(job.id));
    rows.appendChild(row);
  });
}

async function refreshJobs() {
  const jobs = await fetchJson("/api/jobs");
  renderJobs(jobs);
  if (state.selectedJobId) {
    await selectJob(state.selectedJobId, false);
  }
}

async function selectJob(jobId, keepSelection = true) {
  if (keepSelection) {
    state.selectedJobId = jobId;
  }
  let job;
  try {
    job = await fetchJson(`/api/jobs/${jobId}`);
  } catch (error) {
    if (state.selectedJobId === jobId) {
      state.selectedJobId = "";
    }
    return;
  }
  setDetailStatus(job.status);
  const payload = job.payload || {};
  const events = job.events || [];
  const warnings = payload.warnings || [];
  const forward = (job.result || {}).data_server_forward;
  document.querySelector("#jobDetail").className = "";
  document.querySelector("#jobDetail").innerHTML = `
    <div class="detailGrid">
      <div class="metric"><strong>${money(payload.debit_total)}</strong><span>차변 합계</span></div>
      <div class="metric"><strong>${money(payload.credit_total)}</strong><span>대변 합계</span></div>
      <div class="metric"><strong>${Number(payload.line_count || 0)}</strong><span>전표 행</span></div>
      <div class="metric"><strong>${Number(payload.source_row_count || 0)}</strong><span>원본 행</span></div>
      <div class="metric"><strong>${escapeHtml(payload.source_format || "-")}</strong><span>원본 형식</span></div>
      <div class="metric"><strong>${escapeHtml(job.target_client_ip)}</strong><span>Agent PC</span></div>
      <div class="metric"><strong>${forward ? escapeHtml(forward.ok ? "OK" : "FAIL") : "-"}</strong><span>데이터 서버</span></div>
      <div class="metric"><strong>${Number((payload.bank_transfers || []).length)}</strong><span>이체 행</span></div>
    </div>
    ${warnings.length ? `<ul class="warningList">${warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul>` : ""}
    <ul class="eventList">
      ${events.map((event) => `<li><span>${escapeHtml(event.message)}</span><time>${escapeHtml(event.created_at.replace("T", " "))}</time></li>`).join("")}
    </ul>
  `;
}

async function uploadVoucher(event) {
  event.preventDefault();
  const form = document.querySelector("#uploadForm");
  const button = document.querySelector("#uploadButton");
  const notice = document.querySelector("#uploadNotice");
  notice.className = "notice";
  notice.textContent = "";
  button.disabled = true;
  try {
    const data = new FormData(form);
    const job = await fetchJson("/api/uploads/voucher", {
      method: "POST",
      body: data,
    });
    state.selectedJobId = job.id;
    notice.textContent = "업로드 완료";
    form.querySelector("#fileInput").value = "";
    await refreshJobs();
    await selectJob(job.id);
  } catch (error) {
    notice.className = "notice error";
    notice.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

document.querySelector("#uploadForm").addEventListener("submit", uploadVoucher);
document.querySelector("#refreshButton").addEventListener("click", refreshJobs);

loadSettings()
  .then(refreshJobs)
  .catch((error) => {
    document.querySelector("#uploadNotice").className = "notice error";
    document.querySelector("#uploadNotice").textContent = error.message;
  });

setInterval(refreshJobs, 5000);
