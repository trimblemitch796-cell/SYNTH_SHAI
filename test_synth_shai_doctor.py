"""AAA Doctor V1 tests (simulation only, synthetic data, NOT for clinical use)."""
import itertools
import unittest

from synth_shai_doctor import Case, assess, emergency_code
from synth_shai_doctor.core import EMERGENCY, HOLD, REVIEW

ID = 'SYNTHETIC-001'
DANGER = ('suspected_rupture', 'suspected_aortic_dissection',
          'sudden_severe_abdominal_or_back_pain', 'collapse_or_fainting')
SYMPTOMS = ('abdominal_or_back_pain', 'abdominal_tenderness',
            'compressive_symptoms', 'suspected_distal_embolisation')


class SafetyTests(unittest.TestCase):
    def test_rupture(self):
        self.assertEqual(assess(Case(ID, False, suspected_rupture=True)).state, EMERGENCY)

    def test_dissection(self):
        self.assertEqual(assess(Case(ID, True, suspected_aortic_dissection=True)).state, EMERGENCY)

    def test_collapse(self):
        self.assertEqual(assess(Case(ID, True, collapse_or_fainting=True)).state, EMERGENCY)

    def test_sudden_severe_pain(self):
        self.assertEqual(assess(Case(ID, True, sudden_severe_abdominal_or_back_pain=True)).state, EMERGENCY)

    def test_symptomatic_known_aaa(self):
        self.assertEqual(assess(Case(ID, True, known_aaa=True, abdominal_or_back_pain=True)).state, EMERGENCY)

    def test_no_consent_hold(self):
        self.assertEqual(assess(Case(ID, False)).state, HOLD)

    def test_no_consent_cannot_block_emergency(self):
        self.assertEqual(assess(Case(ID, False, collapse_or_fainting=True)).state, EMERGENCY)

    def test_unspecified_never_safe(self):
        self.assertEqual(assess(Case(ID, True)).state, REVIEW)

    def test_pain_without_known_aaa_review(self):
        self.assertEqual(assess(Case(ID, True, abdominal_or_back_pain=True)).state, REVIEW)

    def test_unknown_aaa_with_pain_review(self):
        self.assertEqual(assess(Case(ID, True, known_aaa=None, abdominal_or_back_pain=True)).state, REVIEW)

    def test_no_diagnosis_or_dispatch(self):
        result = assess(Case(ID, True, suspected_rupture=True))
        self.assertFalse(result.diagnosis_made)
        self.assertFalse(result.autonomous_dispatch)
        self.assertTrue(result.human_approval_required)


class StrictInputTests(unittest.TestCase):
    def test_consent_must_be_real_bool(self):
        for bad in ('no', 'False', 'yes', '', 1, 0, None):
            with self.subTest(consent=bad):
                with self.assertRaises(TypeError):
                    Case(ID, bad)

    def test_symptom_flags_must_be_real_bool(self):
        for name in DANGER + SYMPTOMS:
            for bad in ('False', 1, None):
                with self.subTest(field=name, value=bad):
                    with self.assertRaises(TypeError):
                        Case(ID, True, **{name: bad})

    def test_known_aaa_true_false_or_none(self):
        for ok in (True, False, None):
            Case(ID, True, known_aaa=ok)
        for bad in ('True', 1, 0):
            with self.subTest(known_aaa=bad):
                with self.assertRaises(TypeError):
                    Case(ID, True, known_aaa=bad)

    def test_case_id_must_be_text(self):
        for bad in ('', '   ', None, 1):
            with self.subTest(case_id=bad):
                with self.assertRaises((TypeError, ValueError)):
                    Case(bad, True)

    def test_synthetic_only(self):
        for bad in ('x', 'patient-42', 'synthetic-001'):
            with self.subTest(case_id=bad):
                with self.assertRaises(ValueError):
                    Case(bad, True)
        with self.assertRaises(ValueError):
            Case(ID, True, notes='free text')
        with self.assertRaises(TypeError):
            Case(ID, True, notes=None)


class ExhaustiveEscalationTests(unittest.TestCase):
    """Every combination of danger signs, known_aaa, symptoms and consent
    (2^4 * 3 * 2^4 * 2 = 1536 cases)."""

    def test_no_missed_escalation(self):
        bools = (False, True)
        count = 0
        for danger in itertools.product(bools, repeat=len(DANGER)):
            for known in (True, False, None):
                for symptoms in itertools.product(bools, repeat=len(SYMPTOMS)):
                    for consent in bools:
                        kw = dict(zip(DANGER, danger))
                        kw.update(zip(SYMPTOMS, symptoms))
                        case = Case(ID, consent, known_aaa=known, **kw)
                        review = assess(case)
                        flags = emergency_code(case)
                        count += 1
                        # EMERGENCY if and only if an emergency flag exists
                        self.assertEqual(review.state == EMERGENCY, bool(flags), case)
                        # Any danger sign -> EMERGENCY, whatever the consent
                        if any(danger):
                            self.assertEqual(review.state, EMERGENCY, case)
                        if known is True and any(symptoms):
                            self.assertEqual(review.state, EMERGENCY, case)
                        # Never anything implying "safe"
                        self.assertIn(review.state, (EMERGENCY, HOLD, REVIEW))
                        self.assertNotIn('safe', review.state.lower())
                        self.assertFalse(review.diagnosis_made)
                        self.assertFalse(review.autonomous_dispatch)
                        self.assertTrue(review.human_approval_required)
                        if not flags:
                            self.assertEqual(review.state, REVIEW if consent else HOLD, case)
        self.assertEqual(count, 1536)


if __name__ == '__main__':
    unittest.main()
