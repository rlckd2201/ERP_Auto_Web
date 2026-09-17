const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const staticDir = path.join(__dirname, "..", "app", "static");
const html = fs.readFileSync(path.join(staticDir, "index.html"), "utf8");
const script = fs.readFileSync(path.join(staticDir, "app.js"), "utf8");

test("ERP verification input is in the login modal, not job status", () => {
  const modal = html.slice(html.indexOf('id="erpVerificationDialog"'));
  assert.match(modal, /id="erpVerificationForm"/);
  assert.match(modal, /id="verificationCodeInput"/);
  assert.ok(html.indexOf('id="erpVerificationDialog"') > html.indexOf('id="erpCredentialDialog"'));
  assert.doesNotMatch(script, /renderVerificationInput\(job\)/);
});

test("refresh keeps an in-progress verification code and focus", () => {
  const start = script.indexOf("function updateVerificationDialog(job)");
  const end = script.indexOf("async function submitVerificationCode", start);
  assert.ok(start >= 0 && end > start);

  const dialog = { hidden: true };
  const input = {
    value: "",
    focused: 0,
    focus() { this.focused += 1; },
    setCustomValidity() {},
  };
  const document = {
    querySelector(selector) {
      return selector === "#erpVerificationDialog" ? dialog : input;
    },
  };
  const context = vm.createContext({ document });
  vm.runInContext(script.slice(start, end), context);

  vm.runInContext('updateVerificationDialog({ status: "running", result: { verification_required: true } })', context);
  assert.equal(dialog.hidden, false);
  assert.equal(input.focused, 1);
  input.value = "12345";
  vm.runInContext('updateVerificationDialog({ status: "running", result: { verification_required: true } })', context);
  assert.equal(input.value, "12345");
  assert.equal(input.focused, 1);
  vm.runInContext('updateVerificationDialog({ status: "done", result: {} })', context);
  assert.equal(dialog.hidden, true);
  assert.equal(input.value, "");
});
