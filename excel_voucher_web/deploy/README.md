# Finance Server Migration (2026-10-27)

New origin: **https://172.16.19.105:3011**. Previous origin:
`https://172.17.39.121:8081`.

## Cutover Status

The cutover completed on 2026-10-27 at 09:16 KST after the network administrator allowed TCP 3011. The Agent now connects to 105. The old 121/8081 web process was stopped and its startup shortcut moved to the backup directory; the old database and artifacts remain intact.

- HTTPS 200 with certificate validation, account data/password hashes unchanged (except normal sync timestamps), 6 historical jobs, 22 PDFs with matching hashes, and old PDF HTTP download verified.
- Service stop/start verified: the 105 listener exits with its task and starts again without a duplicate. The existing localhost 3011 bridge remains PID 22268.
- Agent first-stage update `d16af0eeeefb` completed using revision `e1203bd`.
- Target-switch commands `6cb62de74228` and `918e3277ea6a` failed before modifying the Agent task, with a TCP connect timeout to 105:3011.
- A short, SYN-only packet capture on 105 during the failed attempt received no Agent connection packet. After the administrator permitted `172.17.30.243 -> 172.16.19.105 TCP 3011`, target-switch command `03b933a574d9` completed using revision `3e14ef3`. Fresh Agent heartbeats on 105 were verified at 09:15:55 and 09:16:16, before retiring 8081. No broad firewall exception or firewall disabling was used.
- Agent task remains under `DESKTOP-55LQ6BN\TEST`, with the existing real ERP mode and printer settings. Only its server address changed.
- The final local regression suite passed 244 tests. No ERP voucher, printer job, or notification email was sent for this migration.

## Runtime

- Web code: `C:\ERP_Auto_Web\excel_voucher_web` on 105.
- Python: `.venv\Scripts\python.exe`, with application dependencies pinned to the source server versions.
- Task: `FinanceVoucher-Web-3011`, SYSTEM, at startup, automatic restart on failure.
- The task starts the venv Python with `deploy/run_service.py` directly. Uvicorn stays in that same process so stopping the task also stops the listening socket.
- Bind **172.16.19.105 only**, not `0.0.0.0`: another accounting application's native bridge owns `127.0.0.1:3011`. Do not stop it.
- Data: `C:\ERP_DB\finance_3011_data`. Do not overwrite the existing `C:\ERP_DB\excel_voucher_web_data` on 105.
- Private configuration: `C:\ERP_DB\finance_web105\environment.json`.
- Dedicated certificate/key: `C:\ERP_DB\finance_web105\finance.cert.pem` and `finance.key.pem`.
- Logs: `C:\ERP_DB\finance_3011_data\service_logs`.
- The new certificate has the 105 IP SAN and is signed by the existing internal CA. Clients must trust that CA.
- Firewall allows TCP 3011 on the 105 interface from `172.16.0.0/12`.

On 105, use an elevated PowerShell to manage the existing task:

```powershell
Get-ScheduledTask -TaskName 'FinanceVoucher-Web-3011'
Stop-ScheduledTask -TaskName 'FinanceVoucher-Web-3011'
Start-ScheduledTask -TaskName 'FinanceVoucher-Web-3011'
Get-NetTCPConnection -State Listen -LocalPort 3011
```

Do not launch the migrated web app manually as Administrator: saved ERP credentials are protected with the web service's SYSTEM identity. Legacy `run_server.ps1` / `install_server_autostart.ps1` defaults describe the old 121 installation, not this service.

## Migration Safety

`migrate_server.py` exports a consistent SQLite snapshot, code, artifacts and the source process's `EXCEL_VOUCHER_*` environment. It refuses active jobs and existing destination data. Install `requirements-migration.txt` only where these migration tools are used.

The entire bundle uses AES-GCM with an RSA-OAEP wrapped key. No decoded ERP password is written as a plaintext migration file. Private keys and configuration must remain in directories accessible only to SYSTEM and Administrators. Never commit them.

Import runs under SYSTEM and re-protects readable DPAPI secrets for that identity. Unreadable source secrets remain unchanged and are counted in the report. The existing finance account's stored ERP credential was readable; the admin account's stored ERP credential was already unreadable on 121 and must be entered again if used.

Snapshot: 18 accounts, 6 terminal jobs, 63 events, 2 saved ERP credential records. There were no queued/running vouchers. The import verified 254 file hashes; all 22 PDF files match the source. Web password hashes are preserved. Failure emails remain disabled. No voucher is resubmitted or completion email resent during migration.

The optional legacy data-server dependency remains `http://172.17.39.121:18080`; it is not silently redirected to a different application on 105.

## Agent Cutover

Agent: `finance-agent-172-17-30-243`, on `172.17.30.243`.

1. Update the running Agent to the migration-capable revision using its existing `update-agent` admin command. Keep the old server address in this first command.
2. After the restarted Agent reports to 121, issue `update-agent` again with the same pinned ZIP revision and `target_server: "https://172.16.19.105:3011"`.
3. The Agent checks the new server's `/api/settings` origin before replacing its scheduled task. Existing ERP mode, printer, print mode and TLS verification setting are preserved.
4. Verify a fresh heartbeat on 105, not the imported historical heartbeat. Only then disable the old 8081 startup shortcut and stop that web process.

Do not create another RDP session on 243. No ERP GUI manipulation is needed for this cutover.

## Rollback

Keep the 121 code/data and the encrypted migration backup. The old startup shortcut is retained at `C:\ERP_DB\finance_migration_20261027\Excel_Voucher_Web_Server.lnk`. Freeze new submissions during rollback; do not let both servers accept new jobs.

If new vouchers have been accepted on 105, reconcile those jobs and artifacts before reverting. Never replay a completed voucher. Restart the original 121 HTTPS launcher, then issue `update-agent` with `target_server: "https://172.17.39.121:8081"` through the still-running 105 server. Verify a fresh Agent heartbeat on 121 before stopping `FinanceVoucher-Web-3011` on 105. Restore the old shortcut only after the old service is verified.
