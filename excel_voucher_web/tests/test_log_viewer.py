import json
from dataclasses import replace
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main, log_viewer
from app.storage import JobStore


@pytest.fixture
def logs(tmp_path, monkeypatch):
    config = replace(main.settings, data_dir=tmp_path / 'data', server_log_dir=tmp_path / 'portal')
    store = JobStore(config.db_path)
    with store.connect() as db:
        db.execute("INSERT INTO jobs(id,title,created_at,updated_at) VALUES ('j1','November voucher','2026-11-01','2026-11-01')")
        for n, status in enumerate(('running', 'error', 'done'), 1):
            db.execute('INSERT INTO job_events(job_id,status,progress,message,created_at) VALUES (?,?,?,?,?)',
                       ('j1', status, n * 20, 'message ' + str(n), f'2026-11-0{n}T10:00:00'))
        db.execute('INSERT INTO agent_admin_commands(id,command,target_agent_id,status,result_json,created_by,created_at,updated_at,finished_at) VALUES (?,?,?,?,?,?,?,?,?)',
                   ('a1', 'tail-log', config.target_agent_id, 'done', json.dumps({'tail': '2026-11-02 10:00:00 INFO password=hidden\nERROR failed', 'private': 'never-export'}), 'admin', '2026-11-02', '2026-11-02', '2026-11-02'))
    config.server_log_dir.mkdir()
    (config.server_log_dir / 'native-20261102.log').write_text('INFO ready\nWARNING slow\nERROR token=hidden\n', encoding='utf-8')
    monkeypatch.setattr(main, 'settings', config)
    monkeypatch.setattr(main, 'store', store)
    monkeypatch.setattr(main, '_current_user', lambda _: SimpleNamespace(active=True, is_admin=True))
    return store, config


def test_jobs_filter_search_and_pagination(logs):
    store, config = logs
    result = log_viewer.read_logs(store, config, page_size=1)
    assert result['total'] == 3 and result['pages'] == 3
    assert result['items'][0]['message'] == 'message 3'
    assert log_viewer.read_logs(store, config, page=99, page_size=1)['page'] == 3
    result = log_viewer.read_logs(store, config, level='error', q='MESSAGE', job_id='j1', start=date(2026, 11, 2), end=date(2026, 11, 2))
    assert result['total'] == 1
    assert result['items'][0]['level'] == 'error'
    assert log_viewer.read_logs(store, config, job_id="' OR 1=1 --")['total'] == 0


def test_agent_only_returns_sanitized_tail(logs):
    store, config = logs
    result = log_viewer.read_logs(store, config, source='agent')
    serialized = json.dumps(result)
    assert 'hidden' not in serialized and 'never-export' not in serialized
    assert '[REDACTED]' in serialized
    assert result['selected_file'] == 'a1' and result['command']['status'] == 'done'
    with pytest.raises(HTTPException) as error:
        log_viewer.read_logs(store, config, source='agent', file_id='other-command')
    assert error.value.status_code == 404


def test_server_files_are_allowlisted_and_redacted(logs):
    store, config = logs
    (config.server_log_dir / 'environment.json').write_text('private settings')
    (config.server_log_dir / 'secret.log').write_text('not an application log')
    result = log_viewer.read_logs(store, config, source='server')
    assert len(result['files']) == 1
    assert result['total'] == 3
    assert 'hidden' not in json.dumps(result)
    assert str(config.server_log_dir) not in json.dumps(result)
    assert log_viewer.read_logs(store, config, source='server', level='warning')['total'] == 1
    for path in ('../environment.json', 'C:\\private.txt', '../../secret.log'):
        with pytest.raises(HTTPException) as error:
            log_viewer.read_logs(store, config, source='server', file_id=path)
        assert error.value.status_code == 404


def test_server_tail_is_bounded_and_reparse_paths_are_ignored(logs, monkeypatch):
    store, config = logs
    (config.server_log_dir / 'native-20261102.log').write_text('old line\n' * 200000 + 'ERROR newest\n')
    result = log_viewer.read_logs(store, config, source='server')
    assert result['limited'] and result['items'][0]['message'] == 'ERROR newest'
    assert result['total'] <= log_viewer.MAX_ROWS
    monkeypatch.setattr(log_viewer, '_unlinked', lambda _: False)
    assert not log_viewer.read_logs(store, config, source='server')['files']


@pytest.mark.parametrize('line,secret', [
    ('password=abc xyz', 'abc'), ('"erp_password": "sensitive phrase"', 'sensitive'),
    ('인증번호: 123456', '123456'), ('verification_code=456789', '456789'),
    ('Authorization: Bearer abcdefg', 'abcdefg'), ('Cookie: session=abcdefg', 'abcdefg'),
    ('https://admin:secret123@host/', 'secret123'), ('dpapi:YWJjZGVm', 'YWJjZGVm'),
    ('-----BEGIN PRIVATE KEY-----\nsecret123\n-----END PRIVATE KEY-----', 'secret123'),
])
def test_redaction(line, secret):
    assert secret not in log_viewer.redact(line)
    assert 'REDACTED' in log_viewer.redact(line)


def test_log_api_requires_active_admin_and_does_not_cache(logs, monkeypatch):
    client = TestClient(main.app)
    monkeypatch.setattr(main, '_current_user', lambda _: None)
    assert client.get('/api/admin/logs').status_code == 401
    for active, admin in ((True, False), (False, True)):
        monkeypatch.setattr(main, '_current_user', lambda _, a=active, b=admin: SimpleNamespace(active=a, is_admin=b))
        assert client.get('/api/admin/logs').status_code == 403
    monkeypatch.setattr(main, '_current_user', lambda _: SimpleNamespace(active=True, is_admin=True))
    response = client.get('/api/admin/logs')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    for query in ('source=private', 'page=0', 'page_size=201', 'q=' + 'x' * 201,
                  'start=invalid', 'start=2026-11-03&end=2026-11-01'):
        assert client.get('/api/admin/logs?' + query).status_code == 422


def test_reads_do_not_mutate_jobs_or_queue_agent_commands(logs):
    store, config = logs
    with store.connect() as db:
        before = list(db.iterdump())
    for source in ('jobs', 'agent', 'server'):
        log_viewer.read_logs(store, config, source=source)
    with store.connect() as db:
        assert list(db.iterdump()) == before
