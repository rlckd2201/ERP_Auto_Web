const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { createHash } = require("node:crypto");

test("portal-adapted app.js preserves the verified operating source contract", () => {
  // The portal transforms this legacy source before serving it. Changing its
  // declarations broke the real portal although standalone browser tests passed.
  // New UI behavior belongs in a separate extension unless both ends are updated.
  const source = readFileSync(join(__dirname, "frontend/app.js"), "utf8").replace(/\r\n/g, "\n").trimEnd();
  assert.equal(createHash("sha256").update(source).digest("hex"),
    "e87a80caaa0a6d148932c0206064c37f447936afa8eb0a9d38cd0546c8e0a57e");
});

test("viewer navigation is a separate deferred extension loaded after the original app", () => {
  const html = readFileSync(join(__dirname, "frontend/index.html"), "utf8");
  const scripts = [...html.matchAll(/<script\b[^>]*src="([^"]+)"[^>]*><\/script>/g)].map(match => match[0]);
  const index = scripts.findIndex(script => script.includes("/assets/app.js?"));
  assert.ok(index >= 0);
  assert.ok(scripts[index].includes("v=20261027_http_errors"));
  assert.ok(scripts[index + 1].includes("/assets/viewer-navigation.js?"));
  assert.ok(scripts[index + 1].includes("defer"));
});
