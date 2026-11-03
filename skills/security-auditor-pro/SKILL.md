---
name: security-auditor-pro
description: "Core procedure for authorized, evidence-driven security and functional audits with an 8-agent team (coordinator, code reviewer, database reviewer, pentest, visual agent, observer, analyst, safety supervisor), approval-gated remediation and an internal coverage-qualified 1-5 star rating. Use for security audits, vulnerability reviews, OWASP/CWE code review, auth/API/DB/TLS configuration review, functional or visual QA of the user's own authorized application, or when security-audit, functional-audit or full-audit is invoked."
---

# Claude Security Auditor Pro: core procedure

This folder is the kit. Paths below are relative to **this skill's directory**:

| File | Purpose |
|---|---|
| `references/POLICY.md` | Mandatory operating policy. Read before every audit. |
| `references/OPERATIONS.md` | Step-by-step operating procedure, limits and stop conditions |
| `references/RATING.md` | Internal 0-100 score and star rules |
| `references/REPORT_TEMPLATE.md` | Report structure |
| `references/scope.example.json` | Scope file template |
| `scripts/audit_manager.py` | Local metadata helper (no network, no target access) |

`AM` below means `python <this skill dir>/scripts/audit_manager.py` (use `python3` on macOS/Linux).

## Modes

| Mode | Entry | Covers |
|---|---|---|
| SECURITY | `security-audit` | source (SAST), secrets, dependencies, auth/session, authorization, APIs, DB grants/queries, TLS/config, bounded live validation |
| FUNCTIONAL | `functional-audit` | user journeys, UI vs server authorization, error states, timeouts, accessibility, visual regressions |
| FULL | `full-audit` | both, correlated, plus rating |

## Procedure

1. **Authorization & scope (blocking).** Read `references/POLICY.md`. Confirm with the user: the asset is theirs or they are authorized, environment (prefer staging), authorized hosts, test accounts, data sensitivity, allowed modes, rate limits. Record them by copying `references/scope.example.json` into the project, filling it in, and running `AM init --scope <file>`. **No live test happens without a recorded scope.**
2. **Capability check.** Detect which tools really exist in this session (browser/Playwright MCP, Semgrep, Gitleaks, Trivy, ZAP, testssl.sh, DB access, monitoring). Never simulate a tool; list missing ones as coverage gaps.
3. **Baseline.** `git status`, app health, sanitized config, current error/latency levels.
4. **Parallel read-only review.** Delegate independent read-only tasks to the agents (if available): `code-reviewer`, `database-reviewer`. Give each agent the scope and the policy rules in its task.
5. **Bounded live validation (optional, approval required).** Only with explicit approval and within scope: `pentest` and/or `visual-agent`, with `observer` watching and `safety-supervisor` holding veto power. Defaults: ≤1 request/second, ≤2 concurrent.
   Before each live test, show the user this proposal and wait for an explicit answer:
   ```
   LIVE TEST PROPOSAL (requires approval)
     Agent:   <pentest | visual-agent>
     Target:  <URL/host>   (in scope ✔ / ✖)
     Goal:    <what it confirms, linked to file:line or finding ID>
     Method:  <exact minimal action, test accounts used>
     Limits:  <req/s · concurrency · timeout>
     Safety:  observer baseline <captured?> · safety-supervisor: <APPROVED | VETO + reason>
   Approve? (yes / no / modify)
   ```
6. **Analysis.** `analyst` deduplicates, separates evidence from hypothesis, assigns severity + confidence. Record each finding: `AM add --title ... --severity ... --component ... --location ... --evidence "<redacted>" --confidence ...`, then `AM update <ID> --status confirmed` once verified.
7. **Present & decide.** For every confirmed issue show evidence, impact, confidence and options: *investigate · bounded validation · propose patch for approval · defer · false positive (with justification)*. **Never patch before explicit per-change approval.**
8. **Remediate & re-test (approved only).** Apply the approved patch, run tests plus security and visual regression, compare with baseline, keep rollback steps, `AM update <ID> --status fixed`.
9. **Rate & report.** Score each dimension 0-100 (or `na` if not tested) per `references/RATING.md`: `AM rate --code .. --identity .. --db .. --infra .. --api .. --validation ..`. Then `AM report --md -o security-audit-report.md`.

## Hard rules

- Only assets the user owns or is authorized to test. If in doubt, stop and ask.
- No brute force, credential stuffing, password spraying, DoS, evasion, persistence, exfiltration, destructive SQL, uncontrolled fuzzing or CAPTCHA bypass.
- No changes to code, data or infrastructure without explicit approval for that change.
- Stop immediately on 5xx spikes, latency >2x baseline, resource pressure, lock contention or any unexpected write.
- Never claim a test ran without evidence. Never infer "secure" from an absence of findings.
- Redact secrets and personal data in all evidence and screenshots. Keep `.security-audit/` out of Git.
- The star rating is an internal prioritization aid, **never** a certification or a guarantee.
