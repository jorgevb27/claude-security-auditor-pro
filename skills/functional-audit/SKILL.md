---
name: functional-audit
description: "Run an authorized functional and visual audit of the user's own application: user journeys with test accounts, UI vs server-side authorization, error states, timeouts, accessibility and visual regressions, using a configured browser integration or producing a manual test plan. Use when the user invokes functional-audit or asks for functional/visual QA."
---

# functional-audit

Mode: **FUNCTIONAL**.

Load and follow the core procedure in `../security-auditor-pro/SKILL.md` (relative to this skill's directory),
including its policy (`../security-auditor-pro/references/POLICY.md`), steps and hard rules.

Focus: critical user journeys with test accounts and synthetic data; check that every UI restriction is also enforced server-side (hidden buttons are not security controls); error, empty and timeout states; accessibility basics; visual regressions. If no browser integration (e.g. Playwright MCP) is available, deliver a step-by-step manual test plan and mark visual coverage as NOT TESTED.

Start with step 1 (authorization and scope). If scope is unknown, ask for it before doing anything else.
