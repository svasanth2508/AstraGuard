# AstraGuard Phase 6 test

1. Start backend and frontend.
2. Open http://localhost:5173.
3. Confirm the interactive dependency graph displays Users, API Gateway, Checkout, Payment, Database, Auth and Notification.
4. Click **Inject DB Overload**.
5. Watch Database change first, followed by Payment, Checkout and API Gateway. Red/amber graph paths should animate as the incident propagates.
6. Click different service nodes and confirm the side panel changes its telemetry and dependency details.
7. Confirm alerts correlate into one incident and RCA selects Database Connection Exhaustion for the main scenario.
8. Run Counterfactual Test.
9. Review Business Impact, Minimum Safe Remediation and the remediation contract.
10. Approve the remediation. Confirm telemetry recovers and **RECOVERY VERIFIED** appears.
11. Reset the demo. Repeat with Force Failure enabled and confirm rollback.
12. Confirm audit events are shown at the bottom of the command center.
