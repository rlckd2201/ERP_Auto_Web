'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const path = require('node:path');
const { accessPolicy } = require(path.resolve(process.env.NATIVE_BRIDGE_PATH));

const routes = [
  { method: 'GET', path: '/api/setup/installers/{company}' },
  { method: 'GET', path: '/api/version' },
  { method: 'POST', path: '/api/agent/heartbeat' },
  { method: 'GET', path: '/api/agent/jobs/{job_id}/print-file/{invoice_id}/{file_index}' },
];
const policy = () => accessPolicy({ serviceRoutes: routes });

test('all three existing Korean ERP bundles are allowed after URL decoding', () => {
  const p = policy();
  for (const company of ['대승', '대승정밀', '일강']) {
    const decoded = decodeURIComponent('/api/setup/installers/' + encodeURIComponent(company));
    assert.equal(p.isService('GET', decoded), true, company);
  }
});
test('other Unicode names are not added to the service boundary', () => {
  const p = policy();
  for (const company of ['다른회사', '앞대승', '대승추가', '대승 정밀', '大承']) {
    assert.equal(p.isService('GET', '/api/setup/installers/' + company), false, company);
  }
});
test('company downloads remain GET only', () => {
  for (const method of ['POST', 'HEAD', 'PUT', 'DELETE']) {
    assert.equal(policy().isService(method, '/api/setup/installers/대승'), false);
  }
});
test('other parameterized service routes still reject Unicode', () => {
  assert.equal(policy().isService('GET', '/api/agent/jobs/대승/print-file/1/0'), false);
});
test('ASCII compatibility routes are preserved', () => {
  const p = policy();
  assert.equal(p.isService('GET', '/api/version'), true);
  assert.equal(p.isService('POST', '/api/agent/heartbeat'), true);
  assert.equal(p.isService('GET', '/api/setup/installers/legacy_ascii'), true);
  assert.equal(p.isService('GET', '/api/agent/jobs/job-1/print-file/293/0'), true);
});
test('unknown or extended paths remain outside the service boundary', () => {
  for (const value of ['/api/login', '/api/users', '/api/setup/private',
                       '/api/setup/installers/대승/extra', '/api/setup/installers/../secret',
                       '/api/setup/installers/%252fsecret']) {
    assert.equal(policy().isService('GET', value), false, value);
  }
});
test('a configured different method does not inherit the Korean exception', () => {
  const p = accessPolicy({ serviceRoutes: [{ method: 'POST', path: '/api/setup/installers/{company}' }] });
  assert.equal(p.isService('POST', '/api/setup/installers/대승'), false);
});
test('missing route and malformed route configuration remain rejected', () => {
  assert.equal(accessPolicy().isService('GET', '/api/setup/installers/대승'), false);
  assert.throws(() => accessPolicy({ serviceRoutes: [...routes, routes[0]] }));
  assert.throws(() => accessPolicy({ serviceRoutes: [{ method: 'GET', path: '/api/setup/대승' }] }));
});
