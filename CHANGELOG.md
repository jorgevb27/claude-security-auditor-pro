# Changelog

## 1.0.0 — 2026-11-03

First public release.

- 8 role-specific agents: coordinator, code-reviewer, database-reviewer, pentest, visual-agent, observer, analyst, safety-supervisor (each with its own checklist and the shared safety rules).
- Entry skills `security-audit`, `functional-audit`, `full-audit` + core skill `security-auditor-pro` with the full procedure and a mandatory live-test approval format.
- `audit_manager.py`: `init --scope`, `add`, `update`, `list`, `rate` (implements the coverage-qualified star rules), `report --md`; secret redaction (API keys, JWTs, bearer tokens, passwords, private keys, URL credentials).
- Self-contained kit: nothing is copied into the user's `docs/` or project root; works as a Claude Code plugin, as copied skills, or as a Claude.ai skill (ZIP).
- 11 unit tests + GitHub Actions CI.
- Bilingual README and step-by-step manual (EN/ES) with screenshots.
