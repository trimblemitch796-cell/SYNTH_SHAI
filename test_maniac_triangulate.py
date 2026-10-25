import unittest
from maniac.triangulate import triangulate, readings_from_bundle, HOLD, PASS


def r(sid, stype, value):
    return {"source_id": sid, "source_type": stype, "value": value}


GOOD = [r("cam-1", "camera", 10.0), r("lid-1", "lidar", 10.2)]


class TestTriangulate(unittest.TestCase):
    def assertHold(self, readings, word):
        res = triangulate(readings)
        self.assertEqual(res.outcome, HOLD)
        self.assertIsNone(res.value)
        self.assertTrue(any(word in text for _, text in res.reasons), res.reasons)

    def test_two_independent_agreeing_sources_pass(self):
        res = triangulate(GOOD)
        self.assertEqual(res.outcome, PASS)
        self.assertAlmostEqual(res.value, 10.1)
        self.assertTrue(0.0 <= res.confidence <= 1.0)
        self.assertEqual(res.reasons, [])

    def test_three_sources_use_median_and_perfect_agreement_is_confident(self):
        res = triangulate([r("a", "camera", 5.0), r("b", "lidar", 5.0), r("c", "radar", 5.0)])
        self.assertEqual((res.value, res.confidence), (5.0, 1.0))

    def test_disagreement(self):
        self.assertHold([r("cam", "camera", 10.0), r("lid", "lidar", 20.0)], "disagree")

    def test_too_few_sources(self):
        self.assertHold(GOOD[:1], "fewer than 2")
        self.assertHold([], "fewer than 2")

    def test_same_type_not_independent(self):
        self.assertHold([r("cam-1", "camera", 10.0), r("cam-2", "camera", 10.0)], "not independent")

    def test_same_id_twice(self):
        self.assertHold([r("x", "camera", 10.0), r("x", "lidar", 10.0)], "source_id appears twice")

    def test_malformed_input(self):
        self.assertHold("lots", "must be a list")
        self.assertHold([None, GOOD[1]], "malformed")
        self.assertHold([dict(GOOD[0], extra=1), GOOD[1]], "malformed")
        self.assertHold([r("", "camera", 1.0), GOOD[1]], "non-empty")

    def test_bad_numbers(self):
        for bad in (float("nan"), float("inf"), True, "10"):
            with self.subTest(value=bad):
                self.assertHold([r("cam", "camera", bad), GOOD[1]], "not a real number")

    def test_readings_from_bundle(self):
        bundle = {"sensors": [{"source": "cam", "type": "camera", "quantity": "distance", "value": 1.0},
                              {"source": "lid", "quantity": "distance", "value": 1.0},
                              {"source": "t", "quantity": "temp", "value": 30.0}]}
        self.assertEqual(readings_from_bundle(bundle),
                         [r("cam", "camera", 1.0), r("lid", "lid", 1.0)])
        self.assertEqual(readings_from_bundle(None), [])


if __name__ == "__main__":
    unittest.main()
