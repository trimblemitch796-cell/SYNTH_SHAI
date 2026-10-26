import concurrent.futures
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from referee.referee import Plan, Answer, Journal, evaluate, message


def answers(*values):
    return tuple(Answer('SYNTHETIC-'+str(i+1), 'SYNTHETIC-1', 'SYNTHETIC-'+str(i+1), v)
                 for i, v in enumerate(values))


class RefereeTests(unittest.TestCase):
    def setUp(self):
        self.plan = Plan('SYNTHETIC-1', ('200', '212'))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journal = Journal(Path(self.tmp.name) / 'audit.db')

    def run_case(self, *values, plan=None):
        p = plan or self.plan
        return evaluate(p, answers(*values), p.commitment)

    def test_correct_minority_wins(self):
        r = self.run_case('421', '421', '412')
        self.assertEqual(r['winners'], ['SYNTHETIC-3'])
        self.assertFalse(r['approval_granted'])

    def test_multiple_matching_answers(self):
        r = self.run_case('412', '412.0', '421')
        self.assertEqual(len(r['winners']), 2)
        self.assertTrue(r['disagreement'])

    def test_all_match_cosmetic(self):
        r = self.run_case('412', ' 412.0 ')
        self.assertFalse(r['disagreement'])
        self.assertTrue(r['cosmetic_diff'])

    def test_wrong_agreement_is_not_truth(self):
        self.assertEqual(self.run_case('421', '421')['outcome'], 'NO_MATCH')

    def test_no_check_never_votes(self):
        p = Plan('SYNTHETIC-1', ('200', '212'), 'none')
        self.assertEqual(self.run_case('412', '412', '421', plan=p)['state'], '144 HOLD')

    def test_no_check_even_when_models_agree(self):
        p = Plan('SYNTHETIC-1', ('200', '212'), 'none')
        self.assertEqual(self.run_case('412', '412', plan=p)['state'], '144 HOLD')

    def test_missing_answers(self):
        for values in [('412', None), (None, None)]:
            self.assertEqual(self.run_case(*values)['reason'], 'insufficient_answers')

    def test_timeout_with_two_remaining(self):
        self.assertEqual(self.run_case('412', '421', None)['outcome'], 'MATCH')

    def test_flaky_check(self):
        with patch('referee.referee.check', side_effect=['412', '413']):
            self.assertEqual(self.run_case('412', '421')['reason'], 'check_unstable')

    def test_check_error(self):
        with patch('referee.referee.check', side_effect=RuntimeError('private text')):
            r = self.run_case('412', '421')
            self.assertEqual(r['state'], '144 HOLD')
            self.assertNotIn('private', str(r))

    def test_same_model_reruns(self):
        aa = (Answer('SYNTHETIC-1', 'SYNTHETIC-1', 'SYNTHETIC-1', '412'),
              Answer('SYNTHETIC-1', 'SYNTHETIC-1', 'SYNTHETIC-2', '421'))
        self.assertTrue(evaluate(self.plan, aa, self.plan.commitment)['disagreement'])

    def test_duplicate_attempt_rejected(self):
        a = answers('412')[0]
        self.assertEqual(evaluate(self.plan, (a, a), self.plan.commitment)['reason'], 'duplicate_attempt')

    def test_changed_plan_commitment(self):
        p = Plan('SYNTHETIC-1', ('1', '2'))
        self.assertEqual(evaluate(p, answers('3', '4'), self.plan.commitment)['reason'], 'commitment_mismatch')

    def test_exact_decimal(self):
        p = Plan('SYNTHETIC-1', ('0.1', '0.2'))
        self.assertEqual(self.run_case('0.3', '0.4', plan=p)['verdict'], '3/10')

    def test_reject_free_text_and_unbounded_numbers(self):
        for value in ['my name is Bob', 'NaN', '1e999', '9'*100, True, 4.0, '1/0']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                answers(value)

    def test_reject_personal_alias(self):
        with self.assertRaises(ValueError):
            Answer('Bob', 'SYNTHETIC-1', 'SYNTHETIC-1', '412')

    def test_deterministic(self):
        self.assertEqual(self.run_case('412', '421'), self.run_case('412', '421'))

    def test_default_message_excludes_raw_outputs(self):
        self.assertNotIn('421', message(self.run_case('412', '421')))
        self.assertEqual(message(self.run_case('420', '421')), '144 HOLD — awaiting human review')

    def test_audit_retrieval_and_anchor(self):
        r = self.journal.record(self.plan, answers('412', '421'), self.plan.commitment)
        self.assertTrue(self.journal.verify(r['audit_anchor']))
        self.assertEqual(self.journal.read('SYNTHETIC-1')['answers'][1]['raw'], '421')

    def test_replay_holds(self):
        for _ in range(2):
            r = self.journal.record(self.plan, answers('412', '421'), self.plan.commitment)
        self.assertEqual(r['reason'], 'replay_rejected')  # was 'audit_failed' before fix (5)

    def test_tampering_and_append_refusal(self):
        self.journal.record(self.plan, answers('412', '421'), self.plan.commitment)
        with self.journal.connect() as db:
            db.execute("UPDATE audit SET payload='{}'")
        self.assertFalse(self.journal.verify())
        p = Plan('SYNTHETIC-2', ('1',))
        self.assertEqual(self.journal.record(p, answers('1', '2'), p.commitment)['state'], '144 HOLD')

    def test_disagreement_deletion_detected(self):
        self.journal.record(self.plan, answers('412', '421'), self.plan.commitment)
        with self.journal.connect() as db:
            db.execute('DELETE FROM disagreements')
        self.assertFalse(self.journal.verify())

    def test_external_anchor_detects_truncation(self):
        r = self.journal.record(self.plan, answers('412', '421'), self.plan.commitment)
        with self.journal.connect() as db:
            db.execute('DELETE FROM disagreements')
            db.execute('DELETE FROM audit')
        self.assertTrue(self.journal.verify())
        self.assertFalse(self.journal.verify(r['audit_anchor']))

    def test_concurrent_append(self):
        def work(i):
            p = Plan('SYNTHETIC-'+str(i), ('200', '212'))
            return self.journal.record(p, answers('412', '421'), p.commitment)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(work, range(1, 9)))
        self.assertTrue(all(r['outcome'] == 'MATCH' for r in results))
        self.assertTrue(self.journal.verify())

    def test_audit_storage_failure_holds(self):
        with patch.object(self.journal, 'connect', side_effect=sqlite3.OperationalError('disk')):
            r = self.journal.record(self.plan, answers('412', '421'), self.plan.commitment)
        self.assertEqual(r['state'], '144 HOLD')


if __name__ == '__main__':
    unittest.main()
