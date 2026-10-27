const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const test = require('node:test');

const source = fs.readFileSync(path.join(__dirname, 'frontend/app.js'), 'utf8');
const names = ['accountingSessionHeaders', 'requestJson', 'requestForm', 'loadMailCollectStatus'];
const selected = names.map(name => {
  const match = source.match(new RegExp('^(?:async )?function ' + name + '\\([^]*?^}', 'm'));
  assert.ok(match, name);
  return match[0];
}).join('\n');
const guardSource = fs.readFileSync(path.join(__dirname, 'frontend/api-response-guard.js'), 'utf8');
const html = '<!DOCTYPE html><html><head><title>502 gateway</title></head><body>proxy details</body></html>';

function harness(responses) {
  const calls = [], expired = [];
  const summary = { textContent: '' };
  const ctx = {
    setTimeout: (fn, delay) => setTimeout(fn, 0), clearTimeout, DOMException,
    sessionStorage: { getItem: () => 'test-session' },
    clearLoginAndShowLogin: message => expired.push(message),
    els: { mailCollectSummary: summary },
    formatTime: value => value,
    fetch: async (url, options) => {
      calls.push({ url, options });
      assert.ok(responses.length, 'Unexpected extra request');
      const { status, body } = responses.shift();
      return { status, ok: status >= 200 && status < 300, text: async () => body };
    },
  };
  ctx.window = ctx; ctx.URL = URL; ctx.location = { href: 'https://portal.example/accounting/', origin: 'https://portal.example' };
  vm.createContext(ctx);
  vm.runInContext(guardSource, ctx);
  vm.runInContext(selected, ctx);
  return { ctx, calls, expired, summary };
}

test('IIS gateway HTML becomes a short connection error with its HTTP status', async () => {
  for (const status of [502, 503, 504]) {
    const { ctx, calls, expired } = harness([{ status, body: html }]);
    await assert.rejects(ctx.requestJson('/api/invoices'), error => {
      assert.match(error.message, new RegExp('HTTP ' + status));
      assert.doesNotMatch(error.message, /DOCTYPE|<html|proxy details/);
      assert.ok(error.message.length < 150);
      return true;
    });
    assert.equal(calls.length, 1);
    assert.equal(expired.length, 0);
  }
});

test('HTML with HTTP 200 is rejected instead of becoming empty setup data', async () => {
  const { ctx } = harness([{ status: 200, body: html }]);
  await assert.rejects(ctx.requestJson('/api/setup/status'), error => error.status === 200 && !error.message.includes('<html'));
});

test('session expiry clears login even when a proxy returns HTML', async () => {
  const { ctx, expired } = harness([{ status: 401, body: html }]);
  await assert.rejects(ctx.requestJson('/api/setup/status'));
  assert.equal(expired.length, 1);
  assert.doesNotMatch(expired[0], /DOCTYPE|proxy details/);
});

test('JSON business errors and empty successful responses remain supported', async () => {
  const { ctx } = harness([{ status: 409, body: JSON.stringify({ detail: 'Printer mapping required' }) }, { status: 204, body: '' }]);
  await assert.rejects(ctx.requestJson('/api/setup/printers'), /Printer mapping required/);
  assert.equal(JSON.stringify(await ctx.requestJson('/api/agent/erp/next')), '{}');
});

test('uploads use the same safe error handling and never resubmit automatically', async () => {
  const { ctx, calls } = harness([{ status: 502, body: html }]);
  const form = {};
  await assert.rejects(ctx.requestForm('/api/invoices/1/quote', form), error => error.message.includes('HTTP 502') && !error.message.includes('DOCTYPE'));
  assert.equal(calls.length, 1);
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.body, form);
  assert.equal(calls[0].options.headers['X-Accounting-Session'], 'test-session');
});

test('mail status shows a bounded failure and recovers on the next successful poll', async () => {
  const { ctx, summary } = harness([
    { status: 502, body: html },
    { status: 200, body: JSON.stringify({ last_finished_at: '11:25:00', saved_count: 2, auto_analyzed_count: 1, failed_count: 0 }) },
  ]);
  await ctx.loadMailCollectStatus();
  assert.match(summary.textContent, /HTTP 502/);
  assert.doesNotMatch(summary.textContent, /DOCTYPE|proxy details/);
  await ctx.loadMailCollectStatus();
  assert.match(summary.textContent, /11:25:00/);
  assert.doesNotMatch(summary.textContent, /HTTP 502/);
});

test('HTML embedded in a JSON detail is not displayed', async () => {
  const { ctx } = harness([{ status: 500, body: JSON.stringify({ detail: html }) }]);
  await assert.rejects(ctx.requestJson('/api/jobs'), error => !error.message.includes('DOCTYPE'));
});

test('guard delegates to the installed portal transport without changing request arguments', async () => {
  const calls = [];
  const original = new Response('{"ready":true}', { status: 200, headers: { 'Content-Type': 'application/json' } });
  const ctx = { URL, location: { href: 'https://portal.example/accounting/', origin: 'https://portal.example' },
    fetch: async (...args) => { calls.push(args); return original; } };
  ctx.window = ctx;
  vm.createContext(ctx); vm.runInContext(guardSource, ctx);
  const options = { method: 'POST', headers: { 'X-Accounting-Session': 'verified', 'X-Portal-Proof': 'transport-proof' }, body: '{}' };
  const response = await ctx.fetch('/api/setup/status', options);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], '/api/setup/status');
  assert.equal(calls[0][1], options);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('Content-Type'), 'application/json');
  assert.deepEqual(await response.clone().json(), { ready: true });
  assert.equal(await response.text(), '{"ready":true}');
});

test('binary downloads and non-API assets retain native Response behavior', async () => {
  const ctx = { URL, location: { href: 'https://portal.example/accounting/', origin: 'https://portal.example' },
    fetch: async () => new Response('%PDF-fixture', { headers: { 'Content-Type': 'application/pdf' } }) };
  ctx.window = ctx;
  vm.createContext(ctx); vm.runInContext(guardSource, ctx);
  const response = await ctx.fetch('/api/invoices/1/pdf');
  assert.equal(await (await response.blob()).text(), '%PDF-fixture');
  assert.equal(await (await ctx.fetch('/assets/example.txt')).text(), '%PDF-fixture');
});

test('setup status GET recovers from two gateway failures with the same verified headers', async () => {
  const { ctx, calls } = harness([
    { status: 502, body: html }, { status: 503, body: html },
    { status: 200, body: '{"ready":false,"agent_id":"owned-pc"}' },
  ]);
  const result = await ctx.requestJson('/accounting-automation/api/setup/status?user_id=alice');
  assert.equal(result.ready, false);
  assert.equal(result.agent_id, 'owned-pc');
  assert.equal(calls.length, 3);
  for (const call of calls) assert.equal(call.options.headers['X-Accounting-Session'], 'test-session');
});

test('persistent setup failure stops after three attempts and keeps the real failure visible', async () => {
  const { ctx, calls } = harness(Array.from({ length: 3 }, () => ({ status: 502, body: html })));
  await assert.rejects(ctx.requestJson('/api/setup/status'), /HTTP 502/);
  assert.equal(calls.length, 3);
});

test('setup POST and unauthorized GET are never retried', async () => {
  const post = harness([{ status: 502, body: html }]);
  await assert.rejects(post.ctx.requestJson('/api/setup/status', { method: 'POST', body: '{}' }), /HTTP 502/);
  assert.equal(post.calls.length, 1);
  const unauthorized = harness([{ status: 401, body: html }]);
  await assert.rejects(unauthorized.ctx.requestJson('/api/setup/status'));
  assert.equal(unauthorized.calls.length, 1);
  assert.equal(unauthorized.expired.length, 1);
});

test('cancelled setup retry does not issue another request', async () => {
  const { ctx, calls } = harness([{ status: 502, body: html }]);
  const controller = new AbortController();
  ctx.setTimeout = (fn, delay) => {
    const timer = setTimeout(fn, 1000);
    queueMicrotask(() => controller.abort());
    return timer;
  };
  await assert.rejects(ctx.requestJson('/api/setup/status', { signal: controller.signal }), error => error.name === 'AbortError');
  assert.equal(calls.length, 1);
});
