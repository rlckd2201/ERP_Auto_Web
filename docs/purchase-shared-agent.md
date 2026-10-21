# Purchase execution on a shared Agent

Version 1.0.250 adds an opt-in execution route. Accounts outside the allowlist retain their current local processing. Regular automatic processing keeps its existing settings.

Set these entries in the operating backend's protected `.env` and restart the backend:

```dotenv
PURCHASE_SHARED_AGENT_IP=172.17.30.243
PURCHASE_SHARED_AGENT_ID=DESKTOP-55LQ6BN-TEST
PURCHASE_SHARED_USER_IDS=tuy1120
```

The account list accepts comma, semicolon, or whitespace separators and matches complete account IDs without regard to case. Agent ID and IP must both match a ready, current Agent. An unavailable shared Agent returns an explicit setup error; it never triggers a local retry.

Purchase one-click, purchase ERP input, and manual cash-disbursement report generation use the shared Agent. The requesting account remains the processor and document author. One-click printing returns to the original Agent and its chosen printer; PDF merging remains on the server. Completed document sets use the existing output-only path.

The shared Agent handles regular and purchase tasks one at a time in its existing synchronous loop. Shared purchases retain strict purchase validation, use longer PDF timeouts, restore task-specific environment values, and close their ERP session afterward. No automatic replay or cross-PC retry is introduced.

Errors after an ERP save command require checking the existing K-System voucher before resetting the invoice to waiting. Metadata/PDF updates preserve that warning; historical warnings cleared by older versions are checked against the invoice's current failed queue record.

To stop routing new purchases, clear `PURCHASE_SHARED_USER_IDS` and restart the backend. Already queued jobs retain their original target. Wait for running work before a version rollback; restore source and `.env` from the release backup without overwriting the live database with an older snapshot.
