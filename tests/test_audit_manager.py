import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "skills" / "security-auditor-pro" / "scripts" / "audit_manager.py"
sys.path.insert(0, str(SCRIPT.parent))
import audit_manager as am  # noqa: E402


class CLITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.tmp.name, env=self.env,
                              capture_output=True, text=True, encoding="utf-8", check=True).stdout

    def findings(self):
        p = pathlib.Path(self.tmp.name) / ".security-audit" / "history" / "findings.json"
        return json.loads(p.read_text(encoding="utf-8"))

    def test_init_add_report(self):
        self.run_cli("init")
        self.run_cli("add", "--title", "test", "--severity", "medium", "--component", "api", "--evidence", "redacted")
        out = self.run_cli("report")
        self.assertIn("Findings: 1", out)
        self.assertIn("NOT ASSESSED", out)

    def test_secrets_are_redacted(self):
        self.run_cli("init")
        self.run_cli("add", "--title", "leak", "--severity", "high", "--component", "cfg",
                     "--evidence", "api_key=sk-abcdefghijklmnopqrstuvwx token: abc123 Bearer abcdefghijkl")
        ev = self.findings()[0]["evidence"]
        self.assertNotIn("sk-abcdef", ev)
        self.assertNotIn("abc123", ev)
        self.assertNotIn("abcdefghijkl", ev)

    def test_update_and_markdown_report(self):
        self.run_cli("init")
        self.run_cli("add", "--title", "IDOR", "--severity", "high", "--component", "API", "--evidence", "x")
        fid = self.findings()[0]["id"]
        self.run_cli("update", fid, "--status", "confirmed", "--confidence", "high", "--note", "reproduced on staging")
        f = self.findings()[0]
        self.assertEqual((f["status"], f["confidence"]), ("confirmed", "high"))
        md = self.run_cli("report", "--md")
        self.assertIn("| " + fid + " | HIGH | high |", md)


class RatingTest(unittest.TestCase):
    full = {k: 100.0 for k in am.DIMENSIONS}

    def test_insufficient_coverage_gives_no_stars(self):
        scores = dict(self.full, db=None, infra=None)  # 70% assessed
        self.assertIsNone(am.compute_rating(scores, [])["stars"])

    def test_perfect_full_coverage_gives_five(self):
        self.assertEqual(am.compute_rating(self.full, [])["stars"], 5)

    def test_critical_caps_at_two(self):
        f = [{"severity": "critical", "status": "confirmed"}]
        self.assertEqual(am.compute_rating(self.full, f)["stars"], 2)

    def test_high_caps_at_three(self):
        f = [{"severity": "high", "status": "accepted"}]
        self.assertEqual(am.compute_rating(self.full, f)["stars"], 3)

    def test_fixed_findings_do_not_cap(self):
        f = [{"severity": "critical", "status": "fixed"}]
        self.assertEqual(am.compute_rating(self.full, f)["stars"], 5)

    def test_five_stars_need_95_percent_coverage(self):
        scores = dict(self.full, validation=None)  # 85% assessed
        self.assertEqual(am.compute_rating(scores, [])["stars"], 4)

    def test_stale_evidence_blocks_five_stars(self):
        self.assertEqual(am.compute_rating(self.full, [], evidence_age_days=60)["stars"], 4)

    def test_score_bands(self):
        for value, stars in ((30, 1), (50, 2), (70, 3), (90, 4)):
            scores = {k: float(value) for k in am.DIMENSIONS}
            self.assertEqual(am.compute_rating(scores, [])["stars"], stars, value)


if __name__ == "__main__":
    unittest.main()
