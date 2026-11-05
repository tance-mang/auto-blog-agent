import unittest

from autoblog.guardian import report


class GuardianTest(unittest.TestCase):
    def test_report_classifies_without_echoing_raw_logs(self):
        run = {"id": 123, "run_attempt": 2, "conclusion": "failure"}
        result = report("example/blog", run, "HTTP Error 429\nprivate-data", True)
        self.assertIn("rate_limit", result)
        self.assertIn("/attempts/2", result)
        self.assertNotIn("private-data", result)

    def test_no_logs_keeps_outcome_unknown(self):
        run = {"id": 123, "run_attempt": 1, "conclusion": "failure"}
        self.assertIn("证据不足", report("example/blog", run, "", False))

    def test_timeout_is_visible_without_logs(self):
        run = {"id": 123, "run_attempt": 1, "conclusion": "timed_out"}
        self.assertIn("GitHub 标记运行超时", report("example/blog", run, "", False))
