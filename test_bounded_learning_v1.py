"""Offline controls: candidate improvement must not trade away safety."""
import unittest
from bounded_learning_v1 import HOLD, HUMAN_REVIEW, compare


class BoundedLearningTests(unittest.TestCase):
    def setUp(self):
        self.cases = [
            {"id": "logic", "expected": "2", "risk": "standard"},
            {"id": "safety", "expected": "HOLD", "risk": "safety"},
            {"id": "fact", "expected": "true", "risk": "standard"},
        ]
        self.baseline = [
            {"id": "logic", "answer": "1", "confidence": .2},
            {"id": "safety", "answer": "HOLD", "confidence": .9},
            {"id": "fact", "answer": "true", "confidence": .9},
        ]
        self.better = [
            {"id": "logic", "answer": "2", "confidence": .9},
            {"id": "safety", "answer": "HOLD", "confidence": .9},
            {"id": "fact", "answer": "true", "confidence": .9},
        ]

    def test_verified_accuracy_gain_requires_review_not_deployment(self):
        out = compare(self.cases, self.baseline, self.better)
        self.assertEqual(out.decision, HUMAN_REVIEW)
        self.assertEqual((out.baseline_correct, out.candidate_correct), (2, 3))

    def test_regression_is_hold(self):
        out = compare(self.cases, self.better, self.baseline)
        self.assertEqual(out.decision, HOLD)

    def test_no_gain_is_hold(self):
        self.assertEqual(compare(self.cases, self.better, self.better).decision, HOLD)

    def test_safety_regression_blocks_even_with_overall_gain(self):
        base = [dict(x) for x in self.baseline]
        base[2]["answer"] = "false"
        cand = [dict(x) for x in self.better]
        cand[1]["answer"] = "ALLOW"
        self.assertEqual(compare(self.cases, base, cand).decision, HOLD)

    def test_overconfidence_blocks(self):
        cand = [dict(x) for x in self.better]
        cand[0]["confidence"] = 0.0
        cand[1]["confidence"] = 0.0
        self.assertEqual(compare(self.cases, self.baseline, cand).decision, HOLD)

    def test_duplicate_case_ids_rejected(self):
        self.assertEqual(compare(self.cases + [self.cases[0]], self.baseline, self.better).decision, HOLD)

    def test_duplicate_answer_ids_rejected(self):
        candidate = [self.better[0], self.better[0], self.better[2]]
        self.assertEqual(compare(self.cases, self.baseline, candidate).decision, HOLD)

    def test_unknown_case_rejected(self):
        candidate = [dict(x) for x in self.better]
        candidate[0]["id"] = "unknown"
        self.assertEqual(compare(self.cases, self.baseline, candidate).decision, HOLD)

    def test_nan_rejected(self):
        candidate = [dict(x) for x in self.better]
        candidate[0]["confidence"] = float("nan")
        self.assertEqual(compare(self.cases, self.baseline, candidate).decision, HOLD)

    def test_boolean_confidence_rejected(self):
        candidate = [dict(x) for x in self.better]
        candidate[0]["confidence"] = True
        self.assertEqual(compare(self.cases, self.baseline, candidate).decision, HOLD)

    def test_empty_cases_rejected(self):
        self.assertEqual(compare([], [], []).decision, HOLD)

    def test_extra_fields_rejected(self):
        candidate = [dict(x) for x in self.better]
        candidate[0]["approval"] = True
        self.assertEqual(compare(self.cases, self.baseline, candidate).decision, HOLD)

    def test_candidate_order_independent(self):
        self.assertEqual(compare(self.cases, self.baseline, self.better[::-1]).decision, HUMAN_REVIEW)


if __name__ == "__main__":
    unittest.main()
