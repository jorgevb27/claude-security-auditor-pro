# Operating procedure
1. Discover project structure, deployment topology and exact authorized target scope. Identify production vs staging, data classification, test users and backups.
2. Check available agents and tools; do not assume browser MCP, computer-use, scanners, DB credentials, or monitoring are installed. Obtain explicit access and approval through the user's normal workflow.
3. Capture baseline: git status, application health, environment, sanitized configuration. Prefer staging and read-only access.
4. Run independent source, dependency, TLS/config and DB-permissions reviews concurrently when supported. Bound any live tests: default maximum 1 request/second and 2 concurrent requests, with conservative timeouts; get approval before increasing.
5. For visual workflows, use a configured browser-control integration (e.g. Playwright MCP) or desktop-control integration. Use test accounts, synthetic records and non-destructive flows. Check UI and server authorization independently. Never treat hidden buttons as security controls.
6. Monitor baseline and ongoing errors/latency/resource use. Stop on 5xx spikes, sustained latency >2x baseline, resource pressure, lock contention or any unexpected write. Thresholds are conservative defaults and must be adapted to system capacity.
7. For each finding, save sanitized evidence, severity, affected component, reproduction constraints, confidence, and remediation options. Present to user; no patches without approval.
8. After approved patch, run relevant tests, security regression, visual regression, and compare results to baseline. Keep rollback instructions.
9. Generate internal score with explicit coverage and confidence. Never issue official certificates or guarantee safety.

## Tool suggestions (optional, installed separately)
Semgrep for SAST, Gitleaks for secret detection, Trivy for dependency/container issues, OWASP ZAP for bounded DAST, testssl.sh for TLS, Playwright for UI. Tools and results must be verified. Never run scanners blindly against production.

## Invocation
Plugin install: skills are namespaced, e.g. `/claude-security-auditor-pro:full-audit` (or just ask Claude to "run a full audit").
Project install: copy `skills/*` to `.claude/skills/` and `agents/*` to `.claude/agents/`, then use `/security-audit`, `/functional-audit` or `/full-audit`.
The helper is `scripts/audit_manager.py` inside the `security-auditor-pro` skill. Agent availability depends on the installed Claude Code version.
