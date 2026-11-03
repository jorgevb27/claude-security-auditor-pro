---
name: full-audit
description: "Run a full authorized audit combining security and functional/visual testing, correlate findings across code, APIs, database and UI, and compute a coverage-qualified internal 1-5 star rating. Use when the user invokes full-audit or asks for a complete audit of their own authorized project."
---

# full-audit

Mode: **FULL**.

Load and follow the core procedure in `../security-auditor-pro/SKILL.md` (relative to this skill's directory),
including its policy (`../security-auditor-pro/references/POLICY.md`), steps and hard rules.

Run SECURITY and FUNCTIONAL in the same audit, then correlate: e.g. a UI flow that exposes an API weakness, or a code finding confirmed visually. Finish with the rating (step 9) and the Markdown report.

Start with step 1 (authorization and scope). If scope is unknown, ask for it before doing anything else.
