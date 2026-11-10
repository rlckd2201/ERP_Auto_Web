"""Bounded, read-only operational log views. Never expose payload/config JSON."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

MAX_ROWS = 10000
MAX_BYTES = 1024 * 1024
MAX_FILES = 50
_SECRET = re.compile(
    r'''(?i)(["']?(?:erp[_-]?)?(?:password(?:_blob)?|pwd|secret|(?:access_|refresh_)?token|api[_-]?key|verification[_-]?code|otp|비밀번호|인증번호)["']?\s*[:=]\s*)(?:"[^"\r\n]*"|'[^'\r\n]*'|[^,;&}\]\r\n]+)'''
)


def redact(value):
    text = str(value or '')
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    text = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?(?:-----END [^-]*PRIVATE KEY-----|$)', '[REDACTED PRIVATE KEY]', text)
    text = re.sub(r'(?im)^(\s*(?:authorization|cookie|set-cookie)\s*:\s*).+$', r'\1[REDACTED]', text)
    text = _SECRET.sub(r'\1[REDACTED]', text)
    text = re.sub(r'(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)dpapi:[A-Za-z0-9+/=]+', 'dpapi:[REDACTED]', text)
    return re.sub(r'(://)[^/@\s]+:[^/@\s]+@', r'\1[REDACTED]@', text)


def _level(message):
    if re.search(r'\b(ERROR|CRITICAL|FATAL|Traceback|Exception)\b|오류|실패', message, re.I):
        return 'error'
    if re.search(r'\b(WARN|WARNING)\b|경고', message, re.I):
        return 'warning'
    return 'info'


def _lines(text, context):
    # Redact before splitting so multiline credential blocks cannot leak.
    entries = []
    for number, line in enumerate(redact(text).splitlines(), 1):
        if not line.strip():
            continue
        stamp = re.match(r'^(\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d(?:[.,]\d+)?)', line)
        entries.append({'id': str(number), 'time': stamp[1] if stamp else '',
                        'level': _level(line), 'context': context, 'message': line})
    return list(reversed(entries[-MAX_ROWS:]))


def _plain_json(raw):
    try:
        result = json.loads(raw or '{}')
        return result if isinstance(result, dict) else {}
    except (TypeError, ValueError):
        return {}


def _job_entries(store, job_id, start, end):
    where, params = [], []
    if job_id:
        where.append('e.job_id = ?')
        params.append(job_id)
    if start:
        where.append('substr(e.created_at,1,10) >= ?')
        params.append(start.isoformat())
    if end:
        where.append('substr(e.created_at,1,10) <= ?')
        params.append(end.isoformat())
    condition = ' WHERE ' + ' AND '.join(where) if where else ''
    with store.connect() as conn:
        rows = conn.execute(
            'SELECT e.id,e.job_id,e.status,e.message,e.created_at,j.title '
            'FROM job_events e LEFT JOIN jobs j ON j.id=e.job_id' + condition +
            ' ORDER BY e.id DESC LIMIT ?', (*params, MAX_ROWS + 1)).fetchall()
        jobs = conn.execute('SELECT id,title FROM jobs ORDER BY created_at DESC LIMIT 500').fetchall()
    return ([{'id': str(row['id']), 'time': row['created_at'],
              'level': 'error' if row['status'] == 'error' else _level(row['message']),
              'context': redact(row['title'] or row['job_id']), 'job_id': row['job_id'],
              'message': redact(row['message'])} for row in rows[:MAX_ROWS]],
            [{'id': row['id'], 'label': redact(row['title'])} for row in jobs], len(rows) > MAX_ROWS)


def _agent_entries(store, file_id, target_agent_id):
    with store.connect() as conn:
        # Only text snapshots, never arbitrary command payloads or job credentials.
        rows = conn.execute(
            "SELECT id,created_at,finished_at,result_json FROM agent_admin_commands "
            "WHERE command='tail-log' AND status='done' AND target_agent_id=? "
            'ORDER BY created_at DESC LIMIT ?', (target_agent_id, MAX_FILES)).fetchall()
        pending = conn.execute(
            "SELECT id,status,created_at,error FROM agent_admin_commands "
            "WHERE command='tail-log' AND target_agent_id=? ORDER BY created_at DESC LIMIT 1",
            (target_agent_id,)).fetchone()
    files = [{'id': row['id'], 'label': row['finished_at'] or row['created_at']} for row in rows]
    selected = next((row for row in rows if row['id'] == file_id), None) if file_id else (rows[0] if rows else None)
    if file_id and selected is None:
        raise HTTPException(404, '선택한 Agent 로그가 없습니다.')
    result = _plain_json(selected['result_json']) if selected else {}
    text = str(result.get('tail') or '')
    limited = len(text.encode('utf-8')) > MAX_BYTES
    if limited:
        text = text.encode('utf-8')[-MAX_BYTES:].decode('utf-8', errors='replace').partition('\n')[2]
    limited = limited or len(text.splitlines()) > MAX_ROWS
    return (_lines(text, 'Agent'), files, selected['id'] if selected else '', limited,
            {k: redact(pending[k]) for k in ('id', 'status', 'created_at', 'error')} if pending else None)


def _unlinked(path):
    for item in (path, *path.parents):
        try:
            if item.is_symlink() or getattr(item.lstat(), 'st_file_attributes', 0) & 1024:
                return False
        except OSError:
            return False
    return True


def _server_entries(data_dir, server_log_dir, file_id):
    files = []
    for root, pattern, label in ((data_dir / 'service_logs', 'web-*.log', 'Web'),
                                 (server_log_dir, 'native-*.log', 'Portal')):
        if not root.is_dir() or not _unlinked(root):
            continue
        try:
            candidates = root.glob(pattern)
            for path in candidates:
                if not path.is_file() or not _unlinked(path):
                    continue
                stat = path.stat()
                token = hashlib.sha256(str(path.resolve()).encode('utf-8')).hexdigest()[:24]
                files.append({'id': token, 'label': label + ' / ' + path.name,
                              'mtime': stat.st_mtime, 'path': path})
        except OSError:
            continue
    files.sort(key=lambda item: item['mtime'], reverse=True)
    files = files[:MAX_FILES]
    selected = next((item for item in files if item['id'] == file_id), None) if file_id else (files[0] if files else None)
    if file_id and selected is None:
        raise HTTPException(404, '선택한 서버 로그가 없습니다.')
    text, limited = '', False
    if selected:
        try:
            path = selected['path']
            if not _unlinked(path):
                raise OSError('Log path changed')
            with path.open('rb') as stream:
                size = stream.seek(0, 2)
                limited = size > MAX_BYTES
                stream.seek(max(0, size - MAX_BYTES))
                raw = stream.read(MAX_BYTES)
            if limited:
                raw = raw.partition(b'\n')[2]
            text = raw.decode('utf-8-sig', errors='replace')
        except OSError as exc:
            raise HTTPException(409, '로그 파일이 변경되었습니다. 다시 조회해 주세요.') from exc
    limited = limited or len(text.splitlines()) > MAX_ROWS
    return (_lines(text, selected['label'] if selected else ''),
            [{k: item[k] for k in ('id', 'label')} for item in files],
            selected['id'] if selected else '', limited)


def read_logs(store, settings, *, source='jobs', q='', level='all', job_id='', file_id='',
              start=None, end=None, page=1, page_size=100):
    if start and end and start > end:
        raise HTTPException(422, '종료일은 시작일보다 빠를 수 없습니다.')
    files, jobs, selected, command, limited = [], [], '', None, False
    if source == 'jobs':
        entries, jobs, limited = _job_entries(store, job_id, start, end)
    elif source == 'agent':
        entries, files, selected, limited, command = _agent_entries(store, file_id, settings.target_agent_id)
    elif source == 'server':
        entries, files, selected, limited = _server_entries(settings.data_dir, settings.server_log_dir, file_id)
    else:
        raise HTTPException(422, '지원하지 않는 로그 종류입니다.')
    needle = q.strip().casefold()
    entries = [entry for entry in entries if (level == 'all' or entry['level'] == level)
               and (not needle or needle in (entry['message'] + ' ' + entry['context']).casefold())]
    total = len(entries)
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, pages)
    offset = (page - 1) * page_size
    return {'ok': True, 'source': source, 'items': entries[offset:offset + page_size],
            'total': total, 'page': page, 'pages': pages, 'page_size': page_size,
            'files': files, 'selected_file': selected, 'jobs': jobs, 'limited': limited,
            'command': command, 'fetched_at': datetime.now().isoformat(timespec='seconds')}
