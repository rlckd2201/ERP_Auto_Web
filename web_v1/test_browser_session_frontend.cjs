const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const test = require('node:test');

const source = fs.readFileSync(path.join(__dirname, 'frontend/app.js'), 'utf8');
const html = fs.readFileSync(path.join(__dirname, 'frontend/index.html'), 'utf8');
const names = ['accountingSessionHeaders', 'parseApiResponse', 'requestJson', 'requestForm', 'continueAfterLogin'];
const selected = names.map(name => {
  const match = source.match(new RegExp('^(?:async )?function ' + name + '\\([^]*?^}', 'm'));
  assert.ok(match, name);
  return match[0];
}).join('\n');

function context({ token = 'test-session', status = 200 } = {}) {
  const values = new Map(token ? [['accountingWebSession', token]] : []);
  const calls = [], expired = [];
  const storage = { getItem: key => values.get(key), setItem: (key, value) => values.set(key, value) };
  const ctx = { sessionStorage: storage, localStorage: storage, state: {},
    renderSetupStatus() {}, showApp() {}, showView() {}, agentConnectedFromSetup: () => true,
    clearLoginAndShowLogin: message => expired.push(message),
    fetch: async (url, options) => {
      calls.push({ url, options });
      return { ok: status === 200, status, text: async () => JSON.stringify({ detail: 'expired' }) };
    } };
  vm.createContext(ctx);
  vm.runInContext(selected, ctx);
  return { ctx, calls, values, expired };
}

test('JSON requests preserve session and caller headers', async () => {
  const { ctx, calls } = context();
  await ctx.requestJson('/api/setup/status', { headers: { Accept: 'application/json' } });
  assert.equal(calls[0].options.headers['X-Accounting-Session'], 'test-session');
  assert.equal(calls[0].options.headers.Accept, 'application/json');
});

test('multipart uploads carry the same session without forcing JSON content type', async () => {
  const { ctx, calls } = context();
  const body = {};
  await ctx.requestForm('/api/invoices/1/quote', body);
  assert.equal(calls[0].options.headers['X-Accounting-Session'], 'test-session');
  assert.equal(calls[0].options.headers['Content-Type'], undefined);
  assert.equal(calls[0].options.body, body);
});

test('expired session returns to login instead of displaying absent installations', async () => {
  const { ctx, expired } = context({ status: 401 });
  await assert.rejects(ctx.requestJson('/api/setup/status'), /expired/);
  assert.deepEqual(expired, ['expired']);
});

test('successful login saves the newly verified session for following requests', async () => {
  const { ctx, values } = context({ token: '' });
  await ctx.continueAfterLogin({ user: { id: 'alice' }, session_token: 'verified', setup: { ready: true } });
  assert.equal(values.get('accountingWebSession'), 'verified');
});

test('without JavaScript, login cannot submit credentials into a GET URL', () => {
  const form = html.match(/<form\b[^>]*\bid="loginForm"[^>]*>/)[0];
  const button = html.match(/<button\b[^>]*\bid="loginSubmitButton"[^>]*>/)[0];
  assert.match(form, /\bmethod="post"/);
  assert.match(button, /\bdisabled\b/);
  assert.ok(source.indexOf('els.loginForm?.addEventListener("submit", handleLogin)') <
            source.indexOf('loginSubmitButton.disabled = false'));
});
