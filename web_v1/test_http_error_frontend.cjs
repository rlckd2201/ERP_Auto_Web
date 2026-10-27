const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const test = require('node:test');

const source = fs.readFileSync(path.join(__dirname, 'frontend/app.js'), 'utf8');
const names = ['accountingSessionHeaders', 'parseApiResponse', 'requestJson', 'requestForm', 'loadMailCollectStatus'];
const selected = names.map(name => {
  const match = source.match(new RegExp('^(?:async )?function ' + name + '\\([^]*?^}', 'm'));
  assert.ok(match, name);
  return match[0];
}).join('\n');
const html = '<!DOCTYPE html><html><head><title>502 gateway</title></head><body>proxy details</body></html>';

function harness(responses) {
  const calls = [], expired = [];
  const summary = { textContent: '' };
  const ctx = {
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
  vm.createContext(ctx);
  vm.runInContext(selected, ctx);
  return { ctx, calls, expired, summary };
}

test('IIS gateway HTML becomes a short typed connection error', async () => {
  for (const status of [502, 503, 504]) {
    const { ctx, calls, expired } = harness([{ status, body: html }]);
    await assert.rejects(ctx.requestJson('/api/setup/status'), error => {
      assert.equal(error.status, status);
      assert.equal(error.transient, true);
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
  await assert.rejects(ctx.requestForm('/api/invoices/1/quote', form), error => error.status === 502 && !error.message.includes('DOCTYPE'));
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
