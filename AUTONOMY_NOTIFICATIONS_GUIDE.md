# AstraGuard — Risk-Aware Autonomy & Admin Notifications

This upgrade adds a policy layer after Minimum Safe Remediation.

## Decision model

AstraGuard deliberately separates:

- **Incident risk** — how serious the outage is.
- **Action risk** — how dangerous the proposed remediation is.

Policy:

- LOW action risk -> auto-execution permitted.
- MEDIUM/HIGH action risk -> human approval required.
- Destructive actions -> blocked by policy.

Current examples:

- Network latency -> reroute traffic -> LOW -> auto execute.
- Traffic spike -> temporary throttling -> LOW -> auto execute.
- DB overload -> increase DB connection pool -> MEDIUM -> human approval.
- Payment failure -> restart payment worker pool -> MEDIUM -> human approval.

The existing remediation contract, verified recovery, rollback, audit trail and adaptive learning remain active.

## Notifications

AstraGuard creates an administrator notification when:

1. an incident is detected/correlated;
2. human approval is required;
3. recovery is verified;
4. recovery verification fails and rollback begins.

Without SMTP configuration, the notification remains visible in the dashboard as `IN_APP_ONLY` and incident processing continues.

## Enable real email with SMTP

Use provider-specific SMTP credentials. For Gmail, use an App Password rather than your normal account password.

PowerShell example for the current terminal:

```powershell
$env:ASTRA_EMAIL_ENABLED="true"
$env:ASTRA_SMTP_HOST="smtp.gmail.com"
$env:ASTRA_SMTP_PORT="587"
$env:ASTRA_SMTP_TLS="true"
$env:ASTRA_SMTP_USERNAME="your-email@gmail.com"
$env:ASTRA_SMTP_PASSWORD="YOUR_APP_PASSWORD"
$env:ASTRA_FROM_EMAIL="your-email@gmail.com"
$env:ASTRA_ADMIN_EMAIL="admin@example.com"

uvicorn main:app --reload
```

Never commit SMTP passwords or app passwords to Git.

## Test sequence

### Human approval path

1. Inject DB Overload.
2. Wait for correlation/RCA.
3. Confirm `Incident risk` and `Action risk` are separate.
4. Confirm `HUMAN APPROVAL REQUIRED`.
5. Confirm the admin notification appears.
6. Approve remediation.
7. Wait for verification.
8. Confirm recovery notification.

### Autonomous low-risk path

1. Reset Demo.
2. Inject Network Latency or Traffic Spike.
3. Wait for incident creation.
4. Confirm `AUTO EXECUTION PERMITTED`.
5. Remediation should enter `EXECUTING` without pressing Approve.
6. Verification still runs before the incident closes.

### Rollback notification

1. Reset Demo.
2. Enable Force Remediation Failure.
3. Inject an incident and execute/approve its remediation.
4. Verification fails.
5. Confirm rollback and recovery-failure notification.
