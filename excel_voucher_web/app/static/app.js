const state = {
  selectedJobId: "",
  jobs: [],
  auth: {
    auth_required: false,
    authenticated: false,
    user: null,
  },
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

async function postJson(url, payload = {}) {
  return fetchJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function canUseApp() {
  if (!state.auth.auth_required) {
    return true;
  }
  return Boolean(state.auth.user && !state.auth.user.must_change_password);
}

function applyAuthUi() {
  const authShell = document.querySelector("#authShell");
  const appShell = document.querySelector("#appShell");
  const loginPanel = document.querySelector("#loginPanel");
  const changePasswordPanel = document.querySelector("#changePasswordPanel");
  const userBar = document.querySelector("#userBar");
  const userName = document.querySelector("#userName");
  const requester = document.querySelector("#requester");
  const companyKey = document.querySelector("#companyKey");
  const user = state.auth.user;

  appShell.hidden = !canUseApp();
  authShell.hidden = canUseApp();
  loginPanel.hidden = Boolean(user && user.must_change_password);
  changePasswordPanel.hidden = !(user && user.must_change_password);
  userBar.hidden = !user;
  if (user) {
    userName.textContent = `${user.name || user.user_id}`;
    requester.value = user.name || user.user_id;
    requester.readOnly = true;
    if (!user.is_admin && companyKey.querySelector(`option[value="${user.company_key}"]`)) {
      companyKey.value = user.company_key;
      companyKey.disabled = true;
    } else {
      companyKey.disabled = false;
    }
  } else {
    userName.textContent = "";
    requester.readOnly = false;
    companyKey.disabled = false;
  }
}

async function loadSettings() {
  const settings = await fetchJson("/api/settings");
  state.auth = settings.auth || state.auth;
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
  applyAuthUi();
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
    updateFileName();
    await refreshJobs();
    await selectJob(job.id);
  } catch (error) {
    notice.className = "notice error";
    notice.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function login(event) {
  event.preventDefault();
  const notice = document.querySelector("#loginNotice");
  notice.className = "notice";
  notice.textContent = "";
  try {
    const data = await postJson("/api/auth/login", {
      user_id: document.querySelector("#loginId").value,
      password: document.querySelector("#loginPassword").value,
    });
    state.auth.authenticated = true;
    state.auth.user = data.user;
    await loadSettings();
    if (canUseApp()) {
      await refreshJobs();
    }
  } catch (error) {
    notice.className = "notice error";
    notice.textContent = error.message;
  }
}

async function changePassword(event) {
  event.preventDefault();
  const notice = document.querySelector("#changePasswordNotice");
  notice.className = "notice";
  notice.textContent = "";
  try {
    const data = await postJson("/api/auth/change-password", {
      old_password: document.querySelector("#oldPassword").value,
      new_password: document.querySelector("#newPassword").value,
    });
    state.auth.user = data.user;
    notice.textContent = "변경 완료";
    await loadSettings();
    await refreshJobs();
  } catch (error) {
    notice.className = "notice error";
    notice.textContent = error.message;
  }
}

async function forgotPassword() {
  const notice = document.querySelector("#loginNotice");
  const userId = document.querySelector("#loginId").value.trim();
  notice.className = "notice";
  notice.textContent = "";
  if (!userId) {
    notice.className = "notice error";
    notice.textContent = "ID를 입력해 주세요.";
    return;
  }
  try {
    await postJson("/api/auth/forgot-password", { user_id: userId });
    notice.textContent = "임시 비밀번호 발송 요청 완료";
  } catch (error) {
    notice.className = "notice error";
    notice.textContent = error.message;
  }
}

async function logout() {
  await postJson("/api/auth/logout");
  state.auth.authenticated = false;
  state.auth.user = null;
  await loadSettings();
}

function updateFileName() {
  const input = document.querySelector("#fileInput");
  const name = input.files && input.files.length ? input.files[0].name : "선택된 파일 없음";
  document.querySelector("#fileName").textContent = name;
}

function initDropZone() {
  const dropZone = document.querySelector("#dropZone");
  const fileInput = document.querySelector("#fileInput");
  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", updateFileName);
  ["dragenter", "dragover"].forEach((name) => {
    dropZone.addEventListener(name, (event) => {
      event.preventDefault();
      dropZone.classList.add("dragOver");
    });
  });
  ["dragleave", "drop"].forEach((name) => {
    dropZone.addEventListener(name, () => dropZone.classList.remove("dragOver"));
  });
  dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    const files = event.dataTransfer.files;
    if (!files || !files.length) {
      return;
    }
    fileInput.files = files;
    updateFileName();
  });
}

document.querySelector("#uploadForm").addEventListener("submit", uploadVoucher);
document.querySelector("#refreshButton").addEventListener("click", refreshJobs);
document.querySelector("#loginForm").addEventListener("submit", login);
document.querySelector("#changePasswordForm").addEventListener("submit", changePassword);
document.querySelector("#forgotPasswordButton").addEventListener("click", forgotPassword);
document.querySelector("#logoutButton").addEventListener("click", logout);
initDropZone();

loadSettings()
  .then(() => {
    if (canUseApp()) {
      return refreshJobs();
    }
    return null;
  })
  .catch((error) => {
    document.querySelector("#uploadNotice").className = "notice error";
    document.querySelector("#uploadNotice").textContent = error.message;
  });

setInterval(() => {
  if (canUseApp()) {
    refreshJobs();
  }
}, 5000);
