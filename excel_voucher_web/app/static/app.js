const state = {
  selectedJobId: "",
  jobs: [],
  adminCommands: [],
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
  queued: "파일 접수가 끝났습니다. 자동 전표처리 PC에서 이어서 처리합니다.",
  claimed: "자동 전표처리 PC에서 처리 준비 중입니다.",
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
  if ((job.result || {}).dry_run) {
    return "ERP 자동입력 전 테스트 출력입니다. 실제 전표 저장은 아직 수행되지 않았습니다.";
  }
  const notification = (job.result || {}).notification || {};
  if (job.status === "done" && notification.sent) {
    return "출력 요청과 완료 메일 발송이 끝났습니다.";
  }
  if (job.status === "done" && notification.queued) {
    return "출력 요청은 끝났고, 메일은 서버 보관함에 임시 저장되었습니다.";
  }
  if (job.status === "done" && (job.result || {}).erp_saved && !(job.result || {}).voucher_no) {
    return "ERP 저장과 출력은 끝났고, 전표번호 확인 전이라 완료 메일은 보내지 않았습니다.";
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

function formatAge(seconds) {
  if (seconds === null || seconds === undefined) {
    return "-";
  }
  const safeSeconds = Math.max(0, Number(seconds || 0));
  if (safeSeconds < 60) {
    return `${safeSeconds}초 전`;
  }
  const minutes = Math.floor(safeSeconds / 60);
  if (minutes < 60) {
    return `${minutes}분 전`;
  }
  return `${Math.floor(minutes / 60)}시간 전`;
}

function renderAdminDiagnostics(job) {
  const user = state.auth.user || {};
  const diagnostics = job.diagnostics || null;
  if (!user.is_admin || !diagnostics) {
    return "";
  }
  const profile = diagnostics.agent_profile || {};
  const forward = diagnostics.data_server_forward || {};
  const hasForward = Object.keys(forward).length > 0;
  const forwardText = hasForward ? (forward.ok ? "성공" : "실패") : "-";
  const events = job.events || [];
  return `
    <details class="adminDiagnostics" open>
      <summary>전산 상세</summary>
      <div class="adminGrid">
        <div><span>현재 위치</span><strong>${escapeHtml(diagnostics.current_location || "-")}</strong></div>
        <div><span>확인할 일</span><strong>${escapeHtml(diagnostics.recommended_action || "-")}</strong></div>
        <div><span>자동 전표처리 PC</span><strong>${escapeHtml(diagnostics.target_client_ip || profile.client_ip || "-")}</strong></div>
        <div><span>Agent ID</span><strong>${escapeHtml(diagnostics.target_agent_id || profile.agent_id || "-")}</strong></div>
        <div><span>Agent 프로그램 접속</span><strong>${diagnostics.agent_online ? "정상" : "미확인"} / ${formatAge(diagnostics.agent_last_seen_age_seconds)}</strong></div>
        <div><span>18080 전달</span><strong>${escapeHtml(forwardText)}</strong></div>
      </div>
      ${
        events.length
          ? `<ul class="eventList">${events
              .map(
                (event) =>
                  `<li><span>${escapeHtml(event.message)}</span><time>${escapeHtml(String(event.created_at || "").replace("T", " "))}</time></li>`,
              )
              .join("")}</ul>`
          : ""
      }
    </details>
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

function isAdmin() {
  return Boolean((state.auth.user || {}).is_admin);
}

async function erpCredentialStatus(companyKey) {
  return fetchJson(`/api/erp-credentials/${encodeURIComponent(companyKey)}`);
}

function canUseApp() {
  if (!state.auth.auth_required) {
    return true;
  }
  return Boolean(state.auth.user && !state.auth.user.must_change_password);
}

function updateUploadAvailability() {
  const companyKey = document.querySelector("#companyKey");
  const uploadButton = document.querySelector("#uploadButton");
  const uploadNotice = document.querySelector("#uploadNotice");
  const selected = companyKey.selectedOptions[0];
  const disabled = Boolean(selected && selected.disabled);
  uploadButton.disabled = disabled || state.uploading;
  if (disabled && uploadNotice && !uploadNotice.textContent) {
    uploadNotice.className = "notice error";
    uploadNotice.textContent = selected.title || "선택한 담당자 기능은 개발 예정입니다.";
  }
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
  const adminPanel = document.querySelector("#adminToolsPanel");
  const user = state.auth.user;

  appShell.hidden = !canUseApp();
  authShell.hidden = canUseApp();
  adminPanel.hidden = !isAdmin();
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
  updateUploadAvailability();
}

function askErpCredentials(status) {
  return new Promise((resolve) => {
    const dialog = document.querySelector("#erpCredentialDialog");
    const form = document.querySelector("#erpCredentialForm");
    const message = document.querySelector("#erpCredentialMessage");
    const userId = document.querySelector("#erpUserId");
    const password = document.querySelector("#erpPassword");
    const remember = document.querySelector("#rememberErpCredential");
    const useSaved = document.querySelector("#useSavedErpCredential");
    const cancel = document.querySelector("#cancelErpCredential");
    const saved = Boolean(status.saved);

    message.textContent = saved
      ? `저장된 ERP 계정 ${status.erp_user_id}으로 로그인할까요? 비밀번호가 바뀌었으면 아래에 새 비밀번호를 입력해서 갱신하세요.`
      : "처음 업로드하는 ERP 계정입니다. 입력한 계정은 다음 업로드 때 다시 확인할 수 있도록 저장됩니다.";
    userId.value = status.erp_user_id || "12240413";
    password.value = "";
    password.required = !saved;
    remember.checked = true;
    useSaved.hidden = !saved;
    dialog.hidden = false;
    password.focus();

    function close(value) {
      dialog.hidden = true;
      form.onsubmit = null;
      useSaved.onclick = null;
      cancel.onclick = null;
      resolve(value);
    }

    useSaved.onclick = () => close({ useSaved: true });
    cancel.onclick = () => close(null);
    form.onsubmit = (event) => {
      event.preventDefault();
      const erpUserId = userId.value.trim();
      const erpPassword = password.value;
      if (!erpUserId || !erpPassword) {
        password.focus();
        return;
      }
      close({
        useSaved: false,
        erpUserId,
        erpPassword,
        remember: remember.checked,
      });
    };
  });
}

function commandTitle(command) {
  const labels = {
    "tail-log": "Agent 로그 가져오기",
    "update-agent": "243 최신 적용",
    "restart-agent": "Agent 재시작",
  };
  return labels[command] || command || "-";
}

function commandStatus(command) {
  const labels = {
    queued: "대기",
    running: "실행 중",
    done: "완료",
    error: "실패",
  };
  return labels[command.status] || command.status || "-";
}

function renderAdminCommands(commands) {
  state.adminCommands = commands || [];
  const count = document.querySelector("#adminCommandCount");
  const rows = document.querySelector("#adminCommandRows");
  count.textContent = `${state.adminCommands.length}건`;
  if (!state.adminCommands.length) {
    rows.innerHTML = `<div class="adminCommandEmpty">실행 내역이 없습니다.</div>`;
    return;
  }
  rows.innerHTML = state.adminCommands
    .map((command) => {
      const result = command.result || {};
      const tail = result.tail ? `<pre class="adminLogTail">${escapeHtml(result.tail)}</pre>` : "";
      const detail = command.error || result.message || result.path || "";
      const statusClass = command.status === "error" ? "error" : command.status === "done" ? "done" : "running";
      return `
        <details class="adminCommandItem" ${command.status === "error" || result.tail ? "open" : ""}>
          <summary>
            <strong>${escapeHtml(commandTitle(command.command))}</strong>
            <span class="badge ${statusClass}">${escapeHtml(commandStatus(command))}</span>
            <time>${escapeHtml(String(command.created_at || "").replace("T", " "))}</time>
          </summary>
          ${detail ? `<p>${escapeHtml(detail)}</p>` : ""}
          ${tail}
        </details>
      `;
    })
    .join("");
}

async function refreshAdminCommands() {
  if (!isAdmin() || !canUseApp()) {
    return;
  }
  const data = await fetchJson("/api/admin/agent-commands");
  renderAdminCommands(data.commands || []);
}

async function runAdminAgentCommand(command) {
  const notice = document.querySelector("#adminToolNotice");
  notice.className = "notice";
  notice.textContent = "";
  try {
    await postJson("/api/admin/agent-commands", { command });
    notice.textContent = `${commandTitle(command)} 요청 완료`;
    await refreshAdminCommands();
  } catch (error) {
    notice.className = "notice error";
    notice.textContent = error.message;
  }
}

async function resetJobsFromAdmin() {
  const notice = document.querySelector("#adminToolNotice");
  notice.className = "notice";
  notice.textContent = "";
  if (!window.confirm("작업 큐와 업로드 파일을 비울까요? 계정 정보는 유지됩니다.")) {
    return;
  }
  try {
    const result = await postJson("/api/admin/jobs/reset", { clear_uploads: true });
    const cleared = result.cleared || {};
    notice.textContent = `작업 ${cleared.jobs || 0}건, 업로드 ${cleared.uploads || 0}건 정리 완료`;
    state.selectedJobId = "";
    await refreshJobs();
  } catch (error) {
    notice.className = "notice error";
    notice.textContent = error.message;
  }
}

async function appendErpCredentials(formData) {
  const companyKey = String(formData.get("company_key") || "daeseung");
  const status = await erpCredentialStatus(companyKey);
  const choice = await askErpCredentials(status);
  if (!choice) {
    return false;
  }
  if (choice.useSaved) {
    formData.set("use_saved_erp_credentials", "1");
    formData.set("remember_erp_credentials", "1");
    return true;
  }
  formData.set("use_saved_erp_credentials", "0");
  formData.set("remember_erp_credentials", choice.remember ? "1" : "0");
  formData.set("erp_user_id", choice.erpUserId);
  formData.set("erp_password", choice.erpPassword);
  return true;
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
    option.textContent = manager.enabled ? manager.label : `${manager.label} - 개발 예정`;
    option.disabled = !manager.enabled;
    if (manager.disabled_reason) {
      option.title = manager.disabled_reason;
    }
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
    ${renderAdminDiagnostics(job)}
  `;
}

async function uploadVoucher(event) {
  event.preventDefault();
  const form = document.querySelector("#uploadForm");
  const button = document.querySelector("#uploadButton");
  const notice = document.querySelector("#uploadNotice");
  notice.className = "notice";
  notice.textContent = "";
  const selected = document.querySelector("#companyKey").selectedOptions[0];
  if (selected && selected.disabled) {
    notice.className = "notice error";
    notice.textContent = selected.title || "선택한 담당자 기능은 개발 예정입니다.";
    return;
  }
  button.disabled = true;
  state.uploading = true;
  renderTransientProgress("파일을 서버로 보내고 있습니다.", 8);
  try {
    const data = new FormData(form);
    const credentialReady = await appendErpCredentials(data);
    if (!credentialReady) {
      return;
    }
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
      await refreshAdminCommands();
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
    await refreshAdminCommands();
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
  state.adminCommands = [];
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
document.querySelector("#companyKey").addEventListener("change", () => {
  const notice = document.querySelector("#uploadNotice");
  notice.className = "notice";
  notice.textContent = "";
  updateUploadAvailability();
});
document.querySelector("#refreshButton").addEventListener("click", () => {
  refreshJobs();
  refreshAdminCommands();
});
document.querySelector("#adminResetJobsButton").addEventListener("click", resetJobsFromAdmin);
document.querySelector("#adminTailLogButton").addEventListener("click", () => runAdminAgentCommand("tail-log"));
document.querySelector("#adminUpdateAgentButton").addEventListener("click", () => runAdminAgentCommand("update-agent"));
document.querySelector("#adminRestartAgentButton").addEventListener("click", () => runAdminAgentCommand("restart-agent"));
document.querySelector("#loginForm").addEventListener("submit", login);
document.querySelector("#changePasswordForm").addEventListener("submit", changePassword);
document.querySelector("#forgotPasswordButton").addEventListener("click", forgotPassword);
document.querySelector("#logoutButton").addEventListener("click", logout);
initDropZone();

loadSettings()
  .then(() => {
    if (canUseApp()) {
      return Promise.all([refreshJobs(), refreshAdminCommands()]);
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
    refreshAdminCommands();
  }
}, 5000);
