(() => {
  const $ = (id) => document.getElementById(id);
  const view = { allowed: false, active: false, source: 'jobs', page: 1, pages: 1,
    sequence: 0, controller: null, data: null, collecting: false };
  const levelNames = { error: '오류', warning: '경고', info: '일반' };
  let pollTimer;

  function notice(message = '', error = false) {
    $('logsNotice').textContent = message;
    $('logsNotice').className = error ? 'notice error' : 'notice';
  }

  function setAccess(allowed) {
    view.allowed = Boolean(allowed);
    $('workspaceTabs').hidden = !view.allowed;
    if (!view.allowed) {
      view.active = false;
      view.sequence += 1;
      view.controller?.abort();
      view.data = null;
      view.collecting = false;
      clearTimeout(pollTimer);
      $('logsRows').replaceChildren();
      $('logsShell').hidden = true;
      $('appShell').hidden = !canUseApp();
      $('workTab').setAttribute('aria-selected', 'true');
      $('workTab').tabIndex = 0;
      $('logsTab').setAttribute('aria-selected', 'false');
      $('logsTab').tabIndex = -1;
      $('logsResult').setAttribute('aria-busy', 'false');
      $('logsCollect').disabled = false;
      $('logsDownload').disabled = true;
      $('logsAuto').checked = false;
      notice();
    } else {
      $('appShell').hidden = view.active;
      $('logsShell').hidden = !view.active;
    }
  }

  function selectTab(active) {
    if (!view.allowed) return;
    view.active = active;
    $('appShell').hidden = active;
    $('logsShell').hidden = !active;
    for (const [id, selected] of [['workTab', !active], ['logsTab', active]]) {
      $(id).setAttribute('aria-selected', String(selected));
      $(id).tabIndex = selected ? 0 : -1;
    }
    if (active) load();
    else {
      view.sequence += 1;
      view.controller?.abort();
    }
  }

  function options(select, items, placeholder) {
    const previous = select.value;
    select.replaceChildren(new Option(placeholder, ''));
    for (const item of items) select.add(new Option(item.label, item.id));
    select.value = [...select.options].some((item) => item.value === previous) ? previous : '';
  }

  function render(data) {
    view.data = data;
    view.page = data.page;
    view.pages = data.pages;
    options($('logsJob'), data.jobs || [], '전체 작업');
    options($('logsFile'), data.files || [], '최신 로그');
    const rows = $('logsRows');
    rows.replaceChildren();
    for (const entry of data.items) {
      const row = document.createElement('tr');
      for (const [kind, value] of [['time', entry.time ? entry.time.replace('T', ' ') : '-'],
        ['level', levelNames[entry.level] || '일반'], ['context', entry.context], ['message', entry.message]]) {
        const cell = document.createElement('td');
        cell.className = 'logCell-' + kind;
        if (kind === 'level') {
          const badge = document.createElement('span');
          badge.className = 'logLevel ' + (Object.hasOwn(levelNames, entry.level) ? entry.level : 'info');
          badge.textContent = value;
          cell.append(badge);
        } else {
          cell.textContent = value || '-';
        }
        row.append(cell);
      }
      rows.append(row);
    }
    if (!data.items.length) {
      const row = document.createElement('tr');
      const cell = document.createElement('td');
      cell.colSpan = 4;
      cell.className = 'tableEmpty';
      cell.textContent = view.source === 'agent' && !data.files.length
        ? '수집된 Agent 로그가 없습니다.' : '조회 조건에 맞는 로그가 없습니다.';
      row.append(cell);
      rows.append(row);
    }
    const snapshot = data.files?.find((item) => item.id === data.selected_file);
    const extra = view.source === 'agent' && snapshot ? ` · 수집 ${snapshot.label.replace('T', ' ')}` : '';
    $('logsSummary').textContent = `${data.total.toLocaleString('ko-KR')}건 · ${data.fetched_at.replace('T', ' ')} 조회${extra}${data.limited ? ' · 최근 로그 일부' : ''}`;
    $('logsPage').textContent = `${data.page} / ${data.pages}`;
    $('logsPrevious').disabled = data.page <= 1;
    $('logsNext').disabled = data.page >= data.pages;
    $('logsDownload').disabled = !data.items.length;
    if (view.source === 'agent' && !view.collecting && data.command?.status === 'error') {
      notice(data.command.error || '최근 Agent 로그 수집에 실패했습니다.', true);
    }
  }

  async function load() {
    if (!view.allowed || !view.active) return;
    const sequence = ++view.sequence;
    view.controller?.abort();
    view.controller = new AbortController();
    const params = new URLSearchParams({ source: view.source, q: $('logsQuery').value.trim(),
      level: $('logsLevel').value, page: view.page, page_size: $('logsPageSize').value });
    if (view.source === 'jobs') {
      if ($('logsJob').value) params.set('job_id', $('logsJob').value);
      if ($('logsStart').value) params.set('start', $('logsStart').value);
      if ($('logsEnd').value) params.set('end', $('logsEnd').value);
      if ($('logsStart').value && $('logsEnd').value && $('logsStart').value > $('logsEnd').value) {
        view.data = null;
        $('logsRows').replaceChildren();
        $('logsDownload').disabled = true;
        $('logsSummary').textContent = '조회 조건 확인 필요';
        notice('종료일은 시작일보다 빠를 수 없습니다.', true);
        $('logsResult').setAttribute('aria-busy', 'false');
        return;
      }
    } else if ($('logsFile').value) params.set('file_id', $('logsFile').value);
    $('logsResult').setAttribute('aria-busy', 'true');
    if (!view.collecting) notice();
    try {
      const response = await fetch('/api/admin/logs?' + params, { signal: view.controller.signal, cache: 'no-store' });
      const data = await response.json();
      if (sequence !== view.sequence || !view.allowed) return;
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          setAccess(false);
          $('uploadNotice').textContent = '로그 조회 권한이 없거나 로그인이 만료되었습니다. 다시 로그인해 주세요.';
          $('uploadNotice').className = 'notice error';
          return;
        }
        throw new Error(typeof data.detail === 'string' ? data.detail : '로그를 불러오지 못했습니다.');
      }
      render(data);
    } catch (error) {
      if (error.name !== 'AbortError' && sequence === view.sequence) {
        view.data = null;
        $('logsDownload').disabled = true;
        $('logsRows').replaceChildren();
        $('logsSummary').textContent = '조회 실패';
        notice(error.message, true);
      }
    } finally {
      if (sequence === view.sequence) $('logsResult').setAttribute('aria-busy', 'false');
    }
  }

  function selectSource(source) {
    view.source = source;
    view.page = 1;
    $('logsFile').value = '';
    for (const button of document.querySelectorAll('[data-log-source]')) {
      button.setAttribute('aria-pressed', String(button.dataset.logSource === source));
    }
    for (const id of ['logsJobField', 'logsStartField', 'logsEndField']) $(id).hidden = source !== 'jobs';
    $('logsFileField').hidden = source === 'jobs';
    $('logsCollect').hidden = source !== 'agent';
    load();
  }

  async function collect() {
    if (!view.allowed || view.collecting) return;
    view.collecting = true;
    $('logsCollect').disabled = true;
    notice('243 Agent 로그 수집 요청 중...');
    try {
      const created = await postJson('/api/admin/agent-commands', { command: 'tail-log' });
      const id = created.command?.id;
      if (!id) throw new Error('로그 수집 명령 번호를 받지 못했습니다.');
      const deadline = Date.now() + 90000;
      const poll = async () => {
        if (!view.allowed) return;
        try {
          const response = await fetchJson('/api/admin/agent-commands');
          if (!view.allowed) return;
          const command = response.commands?.find((item) => item.id === id);
          if (command?.status === 'error') throw new Error(command.error || 'Agent 로그 수집에 실패했습니다.');
          if (command?.status === 'done') {
            view.collecting = false;
            $('logsCollect').disabled = false;
            $('logsFile').value = '';
            view.page = 1;
            await load();
            notice('Agent 로그 수집 완료');
            return;
          }
          if (Date.now() > deadline) throw new Error('Agent 응답 대기 시간이 초과되었습니다. 연결 상태를 확인해 주세요.');
          notice(command?.status === 'running' ? '243에서 로그를 수집하고 있습니다...' : '243 Agent 응답 대기 중...');
          pollTimer = setTimeout(poll, 2000);
        } catch (error) {
          view.collecting = false;
          $('logsCollect').disabled = false;
          notice(error.message, true);
        }
      };
      pollTimer = setTimeout(poll, 1000);
    } catch (error) {
      view.collecting = false;
      $('logsCollect').disabled = false;
      notice(error.message, true);
    }
  }

  $('workTab').addEventListener('click', () => selectTab(false));
  $('logsTab').addEventListener('click', () => selectTab(true));
  $('workspaceTabs').addEventListener('keydown', (event) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const active = event.key === 'Home' ? false : event.key === 'End' ? true : !view.active;
    selectTab(active);
    $(active ? 'logsTab' : 'workTab').focus();
  });
  document.querySelectorAll('[data-log-source]').forEach((button) => button.addEventListener('click', () => selectSource(button.dataset.logSource)));
  $('logsFilters').addEventListener('submit', (event) => { event.preventDefault(); view.page = 1; load(); });
  for (const id of ['logsJob', 'logsFile', 'logsStart', 'logsEnd', 'logsLevel', 'logsPageSize']) {
    $(id).addEventListener('change', () => { view.page = 1; load(); });
  }
  $('logsRefresh').addEventListener('click', load);
  $('logsCollect').addEventListener('click', collect);
  $('logsPrevious').addEventListener('click', () => { view.page = Math.max(1, view.page - 1); load(); });
  $('logsNext').addEventListener('click', () => { view.page = Math.min(view.pages, view.page + 1); load(); });
  $('logsDownload').addEventListener('click', () => {
    if (!view.allowed || !view.data?.items.length) return;
    const data = view.data;
    const text = data.items.map((item) => [item.time, item.level, item.context, item.message].join('\t')).join('\r\n');
    const url = URL.createObjectURL(new Blob(['\uFEFF' + text], { type: 'text/plain;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `finance-${data.source}-${data.fetched_at.replace(/[^0-9]/g, '')}-p${data.page}.txt`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  setInterval(() => {
    if (view.allowed && view.active && $('logsAuto').checked && !document.hidden && $('logsResult').getAttribute('aria-busy') !== 'true') load();
  }, 10000);
  window.financeLogs = { setAccess };
  setAccess(isAdmin() && canUseApp());
})();
