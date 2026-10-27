# Finance Server Migration (2026-10-27)

Current origin: **https://172.16.19.105:3012**. Original origin:
`https://172.17.39.121:8081`.

## Port Reassignment

Ports 3010 and 3011 belong to the existing accounting system. Finance is being
reassigned to 3012; the accounting bridge and its scheduled task must not be
modified. The Agent must validate the new HTTPS endpoint before switching.
The old finance listener is retired only after the Agent reconnects on 3012.
Keep the data directory `C:\ERP_DB\finance_3011_data` unchanged: its name is
historical, and stored artifact paths must continue to resolve.

## Initial Cutover History

The cutover completed on 2026-10-27 at 09:16 KST after the network administrator allowed TCP 3011. The Agent now connects to 105. The old 121/8081 web process was stopped and its startup shortcut moved to the backup directory; the old database and artifacts remain intact.

- HTTPS 200 with certificate validation, account data/password hashes unchanged (except normal sync timestamps), 6 historical jobs, 22 PDFs with matching hashes, and old PDF HTTP download verified.
- Service stop/start verified: the 105 listener exits with its task and starts again without a duplicate. The existing localhost 3011 bridge remains PID 22268.
- Agent first-stage update `d16af0eeeefb` completed using revision `e1203bd`.
- Target-switch commands `6cb62de74228` and `918e3277ea6a` failed before modifying the Agent task, with a TCP connect timeout to 105:3011.
- A short, SYN-only packet capture on 105 during the failed attempt received no Agent connection packet. After the administrator permitted `172.17.30.243 -> 172.16.19.105 TCP 3011`, target-switch command `03b933a574d9` completed using revision `3e14ef3`. Fresh Agent heartbeats on 105 were verified at 09:15:55 and 09:16:16, before retiring 8081. No broad firewall exception or firewall disabling was used.
- Agent task remains under `DESKTOP-55LQ6BN\TEST`, with the existing real ERP mode and printer settings. Only its server address changed.
- The final local regression suite passed 253 tests, including upload/queue/claim without external forwarding. No ERP voucher, printer job, or notification email was sent for this migration.

## Runtime

- Web code: `C:\ERP_Auto_Web\excel_voucher_web` on 105.
- Python: `.venv\Scripts\python.exe`, with application dependencies pinned to the source server versions.
- Task: `FinanceVoucher-Web-3012`, SYSTEM, at startup, automatic restart on failure.
- The task starts the venv Python with `deploy/run_service.py` directly. Uvicorn stays in that same process so stopping the task also stops the listening socket.
- Bind **172.16.19.105:3012 only**, not `0.0.0.0`. Another accounting application's native bridge owns 3010 and localhost 3011. Do not stop it.
- Data: `C:\ERP_DB\finance_3011_data`. Do not overwrite the existing `C:\ERP_DB\excel_voucher_web_data` on 105.
- Private configuration: `C:\ERP_DB\finance_web105\environment.json`.
- Dedicated certificate/key: `C:\ERP_DB\finance_web105\finance.cert.pem` and `finance.key.pem`.
- Logs: `C:\ERP_DB\finance_3011_data\service_logs`.
- The new certificate has the 105 IP SAN and is signed by the existing internal CA. Clients must trust that CA.
- Firewall allows TCP 3012 on the 105 interface from `172.16.0.0/12`.

On 105, use an elevated PowerShell to manage the existing task:

```powershell
Get-ScheduledTask -TaskName 'FinanceVoucher-Web-3012'
Stop-ScheduledTask -TaskName 'FinanceVoucher-Web-3012'
Start-ScheduledTask -TaskName 'FinanceVoucher-Web-3012'
Get-NetTCPConnection -State Listen -LocalPort 3012
```

Do not launch the migrated web app manually as Administrator: saved ERP credentials are protected with the web service's SYSTEM identity. `run_server.ps1` starts the existing task when the private configuration is present. `install_server_autostart.ps1` retains that task instead of creating a duplicate. Launcher defaults and the reset utility now point at the 105 finance installation.

## Migration Safety

`migrate_server.py` exports a consistent SQLite snapshot, code, artifacts and the source process's `EXCEL_VOUCHER_*` environment. It refuses active jobs and existing destination data. Install `requirements-migration.txt` only where these migration tools are used.

The entire bundle uses AES-GCM with an RSA-OAEP wrapped key. No decoded ERP password is written as a plaintext migration file. Private keys and configuration must remain in directories accessible only to SYSTEM and Administrators. Never commit them.

Import runs under SYSTEM and re-protects readable DPAPI secrets for that identity. Unreadable source secrets remain unchanged and are counted in the report. The existing finance account's stored ERP credential was readable; the admin account's stored ERP credential was already unreadable on 121 and must be entered again if used.

Snapshot: 18 accounts, 6 terminal jobs, 63 events, 2 saved ERP credential records. There were no queued/running vouchers. The import verified 254 file hashes; all 22 PDF files match the source. Web password hashes are preserved. Failure emails remain disabled. No voucher is resubmitted or completion email resent during migration.

The optional legacy data-server forwarding has been disabled and its URL cleared. It only copied voucher metadata elsewhere; the successfully completed historical voucher already had a failed forwarding result. Local queue/storage and Agent processing do not depend on it. Manual `/api/jobs/{id}/forward` returns 409 while disabled, without a network request or job update. Migration imports also clear this dependency instead of restoring the old address.

The production path is browser -> 105 web/SQLite/artifacts -> 243 ERP Agent. Groupware directory lookup and SMTP keep their existing independent endpoints. No operational dependency on 121 remains. Old history and rollback copies are retained as records, not live connections. The standalone legacy Manager GUI's HTTP features are not used by the finance adapter, which instantiates `ERPLoginBot` through local shims without launching `AppManager` or `ERPAutoApp`.

## Agent Cutover

Agent: `finance-agent-172-17-30-243`, on `172.17.30.243`.

1. Keep the current finance endpoint running temporarily while starting and checking the 3012 endpoint. There must be no active voucher jobs during the transition.
2. Issue `update-agent` on the current endpoint with a pinned ZIP revision and `target_server: "https://172.16.19.105:3012"`.
3. The Agent checks the new server's `/api/settings` origin before replacing its scheduled task. Existing ERP mode, printer, print mode and TLS verification setting are preserved.
4. Verify a fresh heartbeat on 3012. Then stop and remove only the old finance 3011 task and its dedicated firewall rule. Verify that the unrelated accounting bridge still owns its original listeners.

Do not create another RDP session on 243. No ERP GUI manipulation is needed for this cutover.

## Original 121 Migration Rollback (Historical Only)

121 is not part of current operations. The original migration rollback below
requires explicit approval and is not the procedure for a 3012 port issue.

Keep the 121 code/data and the encrypted migration backup. The old startup shortcut is retained at `C:\ERP_DB\finance_migration_20261027\Excel_Voucher_Web_Server.lnk`. Freeze new submissions during rollback; do not let both servers accept new jobs.

If new vouchers have been accepted on 105, reconcile those jobs and artifacts before reverting. Never replay a completed voucher. Restart the original 121 HTTPS launcher, then issue `update-agent` with `target_server: "https://172.17.39.121:8081"` through the still-running 105 server. Verify a fresh Agent heartbeat on 121 before stopping `FinanceVoucher-Web-3011` on 105. Restore the old shortcut only after the old service is verified.
