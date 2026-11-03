---
name: security-audit
description: "Run an authorized security audit (source, secrets, dependencies, auth, APIs, database, TLS/config, bounded validation) with evidence, approval-gated fixes and an internal rating. Use when the user invokes security-audit or asks for a security audit/vulnerability review of their own authorized project."
---

# security-audit

Mode: **SECURITY**.

Load and follow the core procedure in `../security-auditor-pro/SKILL.md` (relative to this skill's directory),
including its policy (`../security-auditor-pro/references/POLICY.md`), steps and hard rules.

Focus: SAST and OWASP Top 10 / CWE review with file:line evidence, secret detection, vulnerable dependencies, authentication and session handling, server-side authorization (IDOR), API exposure, DB roles/grants and query construction, TLS and security headers, container/infra config. Live validation only after approval, within scope, rate-limited.

Start with step 1 (authorization and scope). If scope is unknown, ask for it before doing anything else.
