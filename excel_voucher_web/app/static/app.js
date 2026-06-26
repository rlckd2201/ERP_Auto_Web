const state = {
  selectedJobId: "",
  jobs: [],
  uploading: false,
  auth: {
    auth_required: false,
    authenticated: false,
    user: null,
  },
};

const statusText = {
  queued: "접수 완료",
  claimed: "처리 준비",
  running: "처리 중",
  done: "출력 완료",
  error: "확인 필요",
  cancelled: "취소",
};

const statusMessage = {
  queued: "파일 접수가 끝났습니다. 창을 닫아도 처리는 계속 진행됩니다.",
  claimed: "담당 PC가 작업을 가져갔습니다.",
  running: "전표 자료를 만들고 출력 요청을 준비하고 있습니다.",
  done: "출력 요청까지 완료되었습니다.",
  error: "처리 중 확인이 필요한 내용이 있습니다.",
  cancelled: "작업이 취소되었습니다.",
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
  detailStatus.textContent = statusText[status] || status || "대기";
}

function jobTitle(job) {
  const payload = job.payload || {};
  return `${payload.company_name || "수시결제"} ${job.accounting_date || ""}`.trim();
}

function resultNotice(job) {
  if (job.status === "error") {
    return job.error || "처리 중 오류가 발생했습니다. 전산팀에 확인을 요청해 주세요.";
  }
  const notification = (job.result || {}).notification || {};
  if (job.status === "done" && notification.sent) {
    return "출력 요청과 완료 메일 발송이 끝났습니다.";
  }
  if (job.status === "done" && notification.queued) {
    return "출력 요청은 끝났고, 메일은 서버 보관함에 임시 저장되었습니다.";
  }
  return statusMessage[job.status] || "처리 상태를 확인하고 있습니다.";
}

function renderStep(label, done, active) {
  const className = `stepItem ${done ? "done" : ""} ${active ? "active" : ""}`.trim();
  return `<li class="${className}"><span></span>${escapeHtml(label)}</li>`;
}

function renderSteps(job) {
  const progress = Number(job.progress || 0);
  const status = job.status;
  const done = status === "done";
  const error = status === "error";
  return `
    <ol class="stepList">
      ${renderStep("접수", progress >= 5, status === "queued")}
      ${renderStep("자료 확인", progress >= 15, status === "claimed")}
      ${renderStep("전표 처리", progress >= 35, status === "running")}
      ${renderStep("출력", done, done)}
      ${error ? renderStep("확인 필요", true, true) : ""}
    </ol>
  `;
}

function renderTransientProgress(message, progress) {
  setDetailStatus("running");
  document.querySelector("#jobDetail").className = "currentJob";
  document.querySelector("#jobDetail").innerHTML = `
    <div class="currentHeader">
      <div>
        <strong>파일 업로드 중</strong>
        <span>${escapeHtml(message)}</span>
      </div>
      <b>${Math.max(0, Math.min(progress, 100))}%</b>
    </div>
    <div class="largeProgressTrack">
      <div class="largeProgressBar" style="width:${Math.max(0, Math.min(progress, 100))}%"></div>
    </div>
    <p class="plainMessage">업로드가 끝나면 서버에 작업이 접수됩니다.</p>
  `;
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
    rows.innerHTML = `<tr><td colspan="4" class="tableEmpty">최근 처리 내역이 없습니다.</td></tr>`;
    return;
  }
  jobs.forEach((job) => {
    const row = document.createElement("tr");
    row.className = "jobRow";
    row.dataset.jobId = job.id;
    const title = escapeHtml(jobTitle(job));
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
  } else if (!state.uploading && jobs.length) {
    await selectJob(jobs[0].id);
  } else if (!state.uploading) {
    setDetailStatus("");
    document.querySelector("#jobDetail").className = "currentJob emptyState";
    document.querySelector("#jobDetail").textContent = "엑셀 파일을 업로드하면 처리 현황이 표시됩니다.";
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
  const warnings = payload.warnings || [];
  const progress = Math.max(0, Math.min(Number(job.progress || 0), 100));
  const notification = (job.result || {}).notification || {};
  document.querySelector("#jobDetail").className = "currentJob";
  document.querySelector("#jobDetail").innerHTML = `
    <div class="currentHeader">
      <div>
        <strong>${escapeHtml(jobTitle(job))}</strong>
        <span>${escapeHtml(resultNotice(job))}</span>
      </div>
      <b>${progress}%</b>
    </div>
    <div class="largeProgressTrack" title="${progress}%">
      <div class="largeProgressBar" style="width:${progress}%"></div>
    </div>
    ${renderSteps(job)}
    <div class="detailGrid">
      <div class="metric"><strong>${money(payload.debit_total)}</strong><span>처리 금액</span></div>
      <div class="metric"><strong>${Number(payload.source_row_count || 0)}</strong><span>엑셀 행</span></div>
      <div class="metric"><strong>${Number(payload.line_count || 0)}</strong><span>전표 줄</span></div>
      <div class="metric"><strong>${escapeHtml(job.accounting_date || "-")}</strong><span>회계일</span></div>
      <div class="metric"><strong>${notification.sent ? "발송 완료" : notification.queued ? "보관됨" : "-"}</strong><span>완료 메일</span></div>
      <div class="metric"><strong>${job.finished_at ? escapeHtml(job.finished_at.replace("T", " ")) : "-"}</strong><span>완료 시간</span></div>
    </div>
    ${warnings.length ? `<ul class="warningList">${warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul>` : ""}
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
  state.uploading = true;
  renderTransientProgress("파일을 서버로 보내고 있습니다.", 8);
  try {
    const data = new FormData(form);
    const job = await fetchJson("/api/uploads/voucher", {
      method: "POST",
      body: data,
    });
    state.selectedJobId = job.id;
    notice.textContent = "업로드가 완료되었습니다. 창을 닫아도 처리는 계속 진행됩니다.";
    form.querySelector("#fileInput").value = "";
    updateFileName();
    await refreshJobs();
    await selectJob(job.id);
  } catch (error) {
    notice.className = "notice error";
    notice.textContent = error.message;
  } finally {
    state.uploading = false;
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
