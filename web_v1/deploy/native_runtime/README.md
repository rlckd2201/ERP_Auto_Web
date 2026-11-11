# Native runtime supervision on server 105

This directory tracks the external runtime repair deployed on 2026-11-11. It is not an alternate application server or a new authentication path. The operating scheduled task `AccountingWeb-Backend` calls `C:/ERP_DB/run_accounting_backend.ps1`; the native host remains under `D:/PortalConnectedSystems/accounting-automation/feature/backend/screens/connection/native-host.py`.

The installed Uvicorn 0.46.0 chooses a Proactor event-loop factory on Windows even when the process previously set the Selector policy. The one-line native-host patch explicitly selects `asyncio:SelectorEventLoop` on Windows and preserves `auto` elsewhere. It leaves the native guard, signed requests, identity resolver, keys, cohort, TLS and ports unchanged. Retest this override when upgrading Python or Uvicorn; Windows Selector loops have different subprocess support and descriptor limits.

The supervisor records the exact child immediately after launch, allows 180 seconds for startup, and returns to recovery when its pinned process exits or loses its listener. Recovery still requires the exact executable, arguments, PID, creation timestamp and command hash. A foreign listener, mismatched record or multiple matching processes fails closed. A listener appearing during recovery aborts termination.

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
