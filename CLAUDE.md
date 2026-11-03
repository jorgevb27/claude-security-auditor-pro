# CLAUDE.md (contributors)

- `skills/security-auditor-pro/SKILL.md` is authoritative; entry skills only select a mode.
- Never weaken `references/POLICY.md` or the approval / stop-condition rules.
- Every agent must keep the shared "Rules that always apply" section.
- Keep `audit_manager.py` stdlib-only and network-free; add a test for every behavior change.
- Release checklist: `python -m unittest discover -s tests` · validate frontmatter · update CHANGELOG · rebuild the ZIP.
