"""Offline tests for the SYNTH_SHAI evidence-presence gate."""
import unittest
from verification import verify_result, HOLD, REVIEW_REQUIRED


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.valid = {
            "test_report": "sample test report",
            "source_revision": "abc123",
            "verification_evidence": "sample evidence",
        }

    def test_complete_evidence_requires_review(self):
        self.assertEqual(verify_result(self.valid), REVIEW_REQUIRED)

    def test_each_missing_field_holds(self):
        for field in self.valid:
            with self.subTest(field=field):
                record = dict(self.valid)
                del record[field]
                self.assertEqual(verify_result(record), HOLD)

    def test_each_empty_field_holds(self):
        for field in self.valid:
            with self.subTest(field=field):
                record = dict(self.valid)
                record[field] = ""
                self.assertEqual(verify_result(record), HOLD)

    def test_none_holds(self):
        self.assertEqual(verify_result(None), HOLD)

    def test_list_holds(self):
        self.assertEqual(verify_result(["evidence"]), HOLD)

    def test_empty_dict_holds(self):
        self.assertEqual(verify_result({}), HOLD)

    def test_extra_fields_do_not_approve(self):
        record = dict(self.valid, urgency="critical", operator_approval=True)
        self.assertEqual(verify_result(record), REVIEW_REQUIRED)


if __name__ == "__main__":
    unittest.main()
