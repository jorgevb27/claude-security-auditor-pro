#!/usr/bin/env python3
"""Claude Security Auditor Pro - local audit metadata manager.

Standard library only. Never touches the network or the audit target: it only
reads/writes sanitized metadata under .security-audit/ in the current project.

  init    [--scope FILE]                      create audit state (optionally store scope)
  add     --title --severity --component --evidence [--location --confidence --status]
  update  ID [--status] [--confidence] [--note]
  list    [--severity S] [--status S]
  rate    --code N --identity N --db N --infra N --api N --validation N   (N = 0-100 or na)
  report  [--md] [-o FILE]
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys
import tempfile
import uuid

VERSION = "1.0.0"
SEVERITIES = ("critical", "high", "medium", "low", "info")
STATUSES = ("unverified", "confirmed", "fixed", "false-positive", "accepted", "deferred")
CONFIDENCE = ("unknown", "low", "medium", "high")
UNRESOLVED = ("confirmed", "accepted", "deferred")
DIMENSIONS = {  # name: weight (%), see references/RATING.md
    "code": 20, "identity": 20, "db": 15, "infra": 15, "api": 15, "validation": 15,
}
DIM_LABELS = {"code": "Code", "identity": "Identity / auth", "db": "Database",
              "infra": "Infrastructure / TLS", "api": "APIs", "validation": "Controlled validation"}

ROOT = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()) / ".security-audit"
HIST = ROOT / "history"
FINDINGS = HIST / "findings.json"
RATINGS = HIST / "ratings.json"
SCOPE = ROOT / "scope.json"

SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"\b(sk-[A-Za-z0-9_\-]{16,})"), "[REDACTED]"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"), "[REDACTED]"),
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "[REDACTED]"),
    (re.compile(r"\b(xox[abprs]-[A-Za-z0-9\-]{10,})"), "[REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}"), "[REDACTED_JWT]"),
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-~+/=]{8,}"), r"\1 [REDACTED]"),
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)(\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|\S+)"), r"\1\2[REDACTED]"),
    (re.compile(r"(?i)(://[^:/\s]+:)[^@/\s]+@"), r"\1[REDACTED]@"),
]


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def clean(text, limit=500):
    text = str(text)
    for rx, repl in SECRET_PATTERNS:
        text = rx.sub(repl, text)
    return text[:limit]


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load(path):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"error: {path} must contain a JSON list")
    return data


def find(items, fid):
    for x in items:
        if x["id"] == fid:
            return x
    raise SystemExit(f"error: finding '{fid}' not found (see: audit_manager.py list)")


# --------------------------------------------------------------------------- #

def cmd_init(a):
    HIST.mkdir(parents=True, exist_ok=True)
    if not FINDINGS.exists():
        atomic_write(FINDINGS, [])
    if a.scope:
        scope = json.loads(pathlib.Path(a.scope).read_text(encoding="utf-8"))
        scope["recorded_at"] = now()
        atomic_write(SCOPE, scope)
        print(f"Scope recorded: {SCOPE}")
    print(f"Initialized audit history: {FINDINGS}")
    print("Reminder: .security-audit/ must stay out of version control.")


def cmd_add(a):
    items = load(FINDINGS)
    fid = "SA-" + uuid.uuid4().hex[:6].upper()
    items.append({
        "id": fid, "created": now(), "updated": now(),
        "title": clean(a.title, 200), "severity": a.severity,
        "component": clean(a.component, 120), "location": clean(a.location or "", 200),
        "evidence": clean(a.evidence), "status": a.status, "confidence": a.confidence,
        "notes": [],
    })
    atomic_write(FINDINGS, items)
    print(f"Finding saved: {fid} [{a.severity.upper()}] status={a.status} confidence={a.confidence}")


def cmd_update(a):
    items = load(FINDINGS)
    x = find(items, a.id)
    changes = []
    if a.status:
        changes.append(f"status {x['status']} -> {a.status}")
        x["status"] = a.status
    if a.confidence:
        changes.append(f"confidence {x['confidence']} -> {a.confidence}")
        x["confidence"] = a.confidence
    if a.note:
        x.setdefault("notes", []).append({"at": now(), "note": clean(a.note)})
        changes.append("note added")
    if not changes:
        raise SystemExit("error: nothing to update (use --status, --confidence or --note)")
    x["updated"] = now()
    atomic_write(FINDINGS, items)
    print(f"{x['id']}: " + "; ".join(changes))


def cmd_list(a):
    items = [x for x in load(FINDINGS)
             if (not a.severity or x["severity"] == a.severity) and (not a.status or x["status"] == a.status)]
    items.sort(key=lambda x: SEVERITIES.index(x["severity"]))
    if not items:
        print("No findings.")
    for x in items:
        print(f"{x['id']}  {x['severity'].upper():<8} {x['status']:<14} {x['confidence']:<7} {x['component']}: {x['title']}")


def compute_rating(scores, findings, evidence_age_days=0):
    assessed = {k: v for k, v in scores.items() if v is not None}
    weight = sum(DIMENSIONS[k] for k in assessed)
    score = round(sum(v * DIMENSIONS[k] for k, v in assessed.items()) / weight, 1) if weight else None
    crit = sum(1 for f in findings if f["severity"] == "critical" and f["status"] in UNRESOLVED)
    high = sum(1 for f in findings if f["severity"] == "high" and f["status"] in UNRESOLVED)
    unverified = sum(1 for f in findings if f["status"] == "unverified")
    limits = []
    if weight < 80:
        stars = None
        limits.append(f"insufficient coverage: {weight}% assessed (80% required for any star)")
    else:
        stars = 1 if score < 40 else 2 if score < 60 else 3 if score < 80 else 4 if score < 95 else 5
        if crit and stars > 2:
            stars = 2
            limits.append(f"capped at 2 stars: {crit} unresolved confirmed CRITICAL finding(s)")
        elif high and stars > 3:
            stars = 3
            limits.append(f"capped at 3 stars: {high} unresolved confirmed HIGH finding(s)")
        if stars == 5 and weight < 95:
            stars = 4
            limits.append(f"5 stars need >=95% coverage ({weight}% assessed)")
        if stars == 5 and evidence_age_days > 30:
            stars = 4
            limits.append(f"5 stars need recent evidence (evidence is {evidence_age_days} days old)")
    if unverified:
        limits.append(f"{unverified} unverified finding(s) not counted; verify or dismiss them")
    missing = [DIM_LABELS[k] for k, v in scores.items() if v is None]
    if missing:
        limits.append("not assessed: " + ", ".join(missing))
    return {"at": now(), "scores": scores, "assessed_weight": weight, "score": score,
            "stars": stars, "limitations": limits}


def parse_dim(v):
    if v is None or str(v).lower() in ("na", "n/a", "-", "none"):
        return None
    n = float(v)
    if not 0 <= n <= 100:
        raise SystemExit("error: dimension scores must be 0-100 or 'na'")
    return n


def stars_text(stars):
    return "NOT RATED" if stars is None else "★" * stars + "☆" * (5 - stars)


def cmd_rate(a):
    scores = {k: parse_dim(getattr(a, k)) for k in DIMENSIONS}
    r = compute_rating(scores, load(FINDINGS), a.evidence_age_days)
    ratings = load(RATINGS)
    ratings.append(r)
    atomic_write(RATINGS, ratings)
    print("Internal Security Rating (not a certification)")
    for k, w in DIMENSIONS.items():
        v = scores[k]
        print(f"  {DIM_LABELS[k]:<22} {w:>3}%  {'not assessed' if v is None else f'{v:g}/100'}")
    print(f"  Assessed weight: {r['assessed_weight']}%")
    print(f"  Provisional score: {'-' if r['score'] is None else r['score']}/100")
    print(f"  Stars: {stars_text(r['stars'])}")
    for l in r["limitations"]:
        print(f"  ! {l}")


def cmd_report(a):
    items = load(FINDINGS)
    ratings = load(RATINGS)
    counts = {s: sum(x["severity"] == s for x in items) for s in SEVERITIES}
    open_items = [x for x in items if x["status"] not in ("fixed", "false-positive")]
    open_items.sort(key=lambda x: SEVERITIES.index(x["severity"]))
    if not a.md:
        print("# Local audit metadata report\n")
        print("Findings:", len(items))
        print("Severity counts:", json.dumps(counts))
        if ratings:
            r = ratings[-1]
            print(f"Rating: {stars_text(r['stars'])} score={r['score']} coverage={r['assessed_weight']}%")
        else:
            print("Rating: NOT ASSESSED - run 'rate' after a documented audit.")
        for x in open_items:
            print(f"- [{x['severity']}] {x['id']} {x['title']} ({x['status']})")
        return
    scope = json.loads(SCOPE.read_text(encoding="utf-8")) if SCOPE.exists() else {}
    L = [f"# Security Audit Report - {scope.get('project', '<project>')}", "",
         f"Generated: {now()}  ", f"Environment: {scope.get('environment', 'not recorded')}  ",
         f"Authorized hosts: {', '.join(scope.get('authorized_hosts', [])) or 'not recorded'}", "",
         "> Internal assessment. Not a third-party certification and not proof of safety.", "",
         "## Summary", "", "| Severity | Total | Open |", "|---|---|---|"]
    for s in SEVERITIES:
        L.append(f"| {s.upper()} | {counts[s]} | {sum(1 for x in open_items if x['severity'] == s)} |")
    L += ["", "## Findings", "",
          "| ID | Severity | Confidence | Component | Location | Evidence (redacted) | Status |",
          "|---|---|---|---|---|---|---|"]
    for x in sorted(items, key=lambda x: SEVERITIES.index(x["severity"])):
        ev = x["evidence"].replace("|", "\\|").replace("\n", " ")
        L.append(f"| {x['id']} | {x['severity'].upper()} | {x['confidence']} | {x['component']} | "
                 f"{x.get('location', '')} | {ev} | {x['status']} |")
    L += ["", "## Rating", ""]
    if ratings:
        r = ratings[-1]
        L += [f"- Stars: **{stars_text(r['stars'])}**",
              f"- Provisional score: {r['score']}/100",
              f"- Assessed weight: {r['assessed_weight']}%"]
        L += [f"- Limitation: {l}" for l in r["limitations"]]
    else:
        L.append("Not assessed.")
    out = "\n".join(L) + "\n"
    if a.output:
        pathlib.Path(a.output).write_text(out, encoding="utf-8")
        print(f"Report written: {a.output}")
    else:
        print(out)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    p = argparse.ArgumentParser(prog="audit_manager", description="Claude Security Auditor Pro - local audit metadata (no network access)")
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("init", help="create .security-audit/ state")
    s.add_argument("--scope", help="scope JSON to record (see references/scope.example.json)")
    s = sub.add_parser("add", help="record a sanitized finding")
    s.add_argument("--title", required=True)
    s.add_argument("--severity", choices=SEVERITIES, required=True)
    s.add_argument("--component", required=True)
    s.add_argument("--evidence", required=True)
    s.add_argument("--location", help="file:line, endpoint or table")
    s.add_argument("--confidence", choices=CONFIDENCE, default="unknown")
    s.add_argument("--status", choices=STATUSES, default="unverified")
    s = sub.add_parser("update", help="change status/confidence or add a note")
    s.add_argument("id")
    s.add_argument("--status", choices=STATUSES)
    s.add_argument("--confidence", choices=CONFIDENCE)
    s.add_argument("--note")
    s = sub.add_parser("list", help="list findings by severity")
    s.add_argument("--severity", choices=SEVERITIES)
    s.add_argument("--status", choices=STATUSES)
    s = sub.add_parser("rate", help="compute the internal 0-100 score and stars")
    for k in DIMENSIONS:
        s.add_argument(f"--{k}", default="na", help="0-100 or na")
    s.add_argument("--evidence-age-days", type=int, default=0)
    s = sub.add_parser("report", help="summary (text) or full Markdown report")
    s.add_argument("--md", action="store_true")
    s.add_argument("-o", "--output")
    a = p.parse_args(argv)
    {"init": cmd_init, "add": cmd_add, "update": cmd_update, "list": cmd_list,
     "rate": cmd_rate, "report": cmd_report}[a.command](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
