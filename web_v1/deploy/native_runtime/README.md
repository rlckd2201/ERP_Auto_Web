# Native runtime supervision on server 105

This directory tracks the external runtime repair deployed on 2026-11-11. It is not an alternate application server or a new authentication path. The operating scheduled task `AccountingWeb-Backend` calls `C:/ERP_DB/run_accounting_backend.ps1`; the native host remains under `D:/PortalConnectedSystems/accounting-automation/feature/backend/screens/connection/native-host.py`.

The installed Uvicorn 0.46.0 chooses a Proactor event-loop factory on Windows even when the process previously set the Selector policy. The one-line native-host patch explicitly selects `asyncio:SelectorEventLoop` on Windows and preserves `auto` elsewhere. It leaves the native guard, signed requests, identity resolver, keys, cohort, TLS and ports unchanged. Retest this override when upgrading Python or Uvicorn; Windows Selector loops have different subprocess support and descriptor limits.

The supervisor records the exact child immediately after launch, allows 180 seconds for startup, and returns to recovery when its pinned process exits or loses its listener. Recovery still requires the exact executable, arguments, PID, creation timestamp and command hash. A foreign listener, mismatched record or multiple matching processes fails closed. A listener appearing during recovery aborts termination.

The November 12 installer-path patches must be applied together: both `native-host.py` and `native-bridge.cjs` independently validate service routes. The installed ERP bundles use the company names `대승`, `대승정밀`, and `일강`; the original ASCII-only parameter pattern rejected their percent-encoded download requests. The patches add only these three literal names to the configured `GET /api/setup/installers/{company}` route. Other parameters, browser authentication, signed portal requests, TLS checks, and the existing ASCII route contract stay intact.

Run the two boundary tests against the actual staged source files before deployment:

```powershell
python tests/test_installer_route_policy.py --native-host <staged-native-host.py>
$env:NATIVE_BRIDGE_PATH = '<staged-native-bridge.cjs>'
node --test tests/test_bridge_installer_policy.cjs
```

After applying both patches, verify each public company download using `Range: bytes=0-0`, and verify that unknown company names, unsigned browser requests, and unauthenticated DB requests are still rejected. Native-loopback success alone is insufficient because the public bridge has its own validator. Keep the original host and bridge, task XML, runtime identity, and a consistent database backup before restarting their exact registered tasks. Do not change Agent ownership by IP alone; the separate administrative PC repair must verify the supplied Windows identity, prior account ownership, current unowned profile, and a fresh heartbeat, then audit only the exact ownership change.

Do not reconcile a stale record automatically. The incident recovery verified the unique orphan's executable/arguments, creation time, parent supervisor PID and matching launch logs before replacing its stale bookkeeping record. Preserve that evidence and back up files, task XML and consistent SQLite before maintenance. Do not restore an old PID record after a restart or replay financial jobs to test availability.

Run the mocked lifecycle tests with Windows PowerShell; they do not launch or stop real processes:

```powershell
powershell -NoProfile -File web_v1/deploy/native_runtime/tests/test_supervisor.ps1
```

Run the TLS fixture with the same Python/Uvicorn as production. It binds only an ephemeral loopback port, uses an isolated ASGI fixture, reads the supplied host source without importing the application, and verifies the supplied certificate. It does not access the application database or dispatch business work:

```powershell
python web_v1/deploy/native_runtime/tests/verify_event_loop.py --native-host <patched-host.py> --certificate <chain.pem> --private-key <key.pem>
```

For deployment, compare the live files to the reviewed baseline, apply the host patch and supervisor under the existing `Global\DSIGAccountingNativeRuntimeSupervisor` mutex, and start the existing scheduled task. Do not change the bridge, portal or other service tasks. Verify native8081/public3010 responses, exact pinned ownership, installation-check readiness, fresh243 heartbeat, unchanged Agent bundle and invoice-row fingerprint. A successful HTTP check is not an authenticated portal rendering check.
