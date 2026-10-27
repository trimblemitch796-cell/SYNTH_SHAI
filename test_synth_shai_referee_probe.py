"""Probe set ported from test_meta_ai_referee_probe.py to the SYNTH_SHAI Referee V0.1 API.
ADAPTED = scenario re-expressed for this API; SPEC = asserts the merged spec's wording."""
import unittest
from unittest.mock import patch
from maniac.synth_shai_referee import Plan, Answer, evaluate, message

PLAN = Plan('SYNTHETIC-1', ('200', '212'))


def ans(*values):
    return tuple(Answer('SYNTHETIC-%d' % (i + 1), 'SYNTHETIC-1', 'SYNTHETIC-%d' % (i + 1), v)
                 for i, v in enumerate(values))


def ev(*values, plan=PLAN):
    return evaluate(plan, ans(*values), plan.commitment)


class Ported(unittest.TestCase):
    def test1_recompute_picks_A_412(self):
        r = ev('412', '421')
        self.assertEqual((r['outcome'], r['winners'], r['verdict']), ('MATCH', ['SYNTHETIC-1'], '412'))
        self.assertEqual([l['attempt'] for l in r['losers']], ['SYNTHETIC-2'])

    def test2_cosmetic_no_flag(self):
        r = ev('4.0', '4', plan=Plan('SYNTHETIC-1', ('2', '2')))
        self.assertFalse(r['disagreement']); self.assertTrue(r['cosmetic_diff'])

    def test3_no_match_holds(self):
        r = ev('400', '421')
        self.assertEqual((r['outcome'], r['state']), ('NO_MATCH', '144 HOLD'))

    def test4_no_check_holds(self):
        self.assertEqual(ev('412', '421', plan=Plan('SYNTHETIC-1', ('200', '212'), 'none'))['state'], '144 HOLD')

    def test4b_two_vs_one_no_check_holds(self):
        self.assertEqual(ev('412', '412', '421', plan=Plan('SYNTHETIC-1', ('200', '212'), 'none'))['state'], '144 HOLD')

    def test5_flaky_check_holds_unstable(self):   # ADAPTED: flakiness injected by patching check()
        with patch('maniac.synth_shai_referee.check', side_effect=['412', '413']):
            r = ev('412', '421')
        self.assertEqual((r['state'], r['reason']), ('144 HOLD', 'check_unstable'))

    def test11_deterministic(self):
        self.assertEqual(ev('412', '421'), ev('412', '421'))

    @unittest.skip("N/A by design: only exact_sum_v1 exists, which binds every passer to one value")
    def test_a_two_passers_differ_is_check_insufficient_hold(self):
        pass

    def test_b_two_passers_agree_match_winners_all_passers(self):
        r = ev('421', '412', '412.0')
        self.assertEqual(r['winners'], ['SYNTHETIC-2', 'SYNTHETIC-3'])
        self.assertEqual([l['attempt'] for l in r['losers']], ['SYNTHETIC-1'])
        self.assertEqual(r['verdict'], '412')

    def test_c1_one_answer_plus_timeout_holds(self):
        r = ev('412', None)
        self.assertEqual((r['state'], r['reason']), ('144 HOLD', 'insufficient_answers'))

    def test_c2_single_model_only_reason_is_insufficient_answers(self):   # SPEC
        r = ev('412')
        self.assertEqual(r['state'], '144 HOLD')
        self.assertEqual(r['reason'], 'insufficient_answers')

    def test_c3_empty_string_answer(self):   # ADAPTED: empty is rejected at construction, not no_answer
        with self.assertRaises(ValueError):
            ans('412', '')

    def test_d_personal_data_rejected_not_stored(self):   # ADAPTED: rejected by exception
        with self.assertRaises(ValueError):
            ans('Call John Citizen on 0412 345 678, john.citizen@example.com', '421')

    def test_d2_privacy_rejected_hold_with_hash(self):   # SPEC: HOLD privacy_rejected + sha256/len record
        import hashlib, tempfile
        from pathlib import Path
        from maniac.synth_shai_referee import make_answer, Journal, RejectedAnswer
        pii = 'Call John Citizen on 0412 345 678, john.citizen@example.com'
        aa = (make_answer('SYNTHETIC-1', 'SYNTHETIC-1', 'SYNTHETIC-1', pii),
              make_answer('SYNTHETIC-2', 'SYNTHETIC-1', 'SYNTHETIC-2', '421'))
        self.assertIs(type(aa[0]), RejectedAnswer)
        with self.assertRaises(ValueError):          # direct construction still rejects
            Answer('SYNTHETIC-1', 'SYNTHETIC-1', 'SYNTHETIC-1', pii)
        with tempfile.TemporaryDirectory() as d:
            j = Journal(Path(d) / 'a.db')
            r = j.record(PLAN, aa, PLAN.commitment)
            self.assertEqual((r['state'], r['reason']), ('144 HOLD', 'privacy_rejected'))
            self.assertIs(r['approval_granted'], False)
            self.assertTrue(j.verify(r['audit_anchor']))
            with j.connect() as db:
                dump = repr(list(db.execute('SELECT * FROM audit')))
            self.assertNotIn('john.citizen', dump); self.assertNotIn('0412 345', dump)
            stored = j.read('SYNTHETIC-1')['answers'][0]
            self.assertEqual(stored['raw_sha256'], hashlib.sha256(pii.encode()).hexdigest())
            self.assertEqual(stored['raw_length'], len(pii))
            self.assertTrue(stored['redacted'].startswith('REDACTED'))

    def test_d3_personal_alias_is_redacted_too(self):
        from maniac.synth_shai_referee import make_answer
        a = make_answer('Bob Smith', 'SYNTHETIC-1', 'SYNTHETIC-1', '412')
        self.assertNotIn('Bob', repr(a))
        r = evaluate(PLAN, (a, ans('412')[0]), PLAN.commitment)
        self.assertEqual(r['reason'], 'privacy_rejected')

    def test_e_approval_granted_always_false(self):
        for vals in [('412', '421'), ('400', '421'), ('412', None), ('412', '412')]:
            self.assertIs(ev(*vals)['approval_granted'], False)

    def test_f_no_majority_vote_or_confidence(self):
        r = ev('412', '412', '421', plan=Plan('SYNTHETIC-1', ('200', '212'), 'none'))
        self.assertEqual(r['state'], '144 HOLD'); self.assertNotIn('confidence', r)
        self.assertEqual(ev('421', '421', '412')['winners'], ['SYNTHETIC-3'])

    def test_g_verdict_never_states_failing_claim(self):
        self.assertEqual(ev('421', '412', '412')['verdict'], '412')

    def test_h_empty_answer_is_not_a_loser(self):
        r = ev('412', '421', None)
        self.assertNotIn('SYNTHETIC-3', [l['attempt'] for l in r['losers']])

    def test_i_non_synthetic_item_id_rejected(self):
        with self.assertRaises(ValueError):
            Plan('CUST-1', ('1',))

    def test_j_privacy_reject_even_when_answers_agree(self):
        with self.assertRaises(ValueError):
            ans('bob@example.com', 'bob@example.com')

    @unittest.skip("N/A: result is a plain dict, no Verdict constructor")
    def test_k_approval_granted_not_a_constructor_arg(self):
        pass

    def test_l_match_still_requires_verify(self):
        r = ev('412', '421')
        self.assertEqual(r['state'], '444000 VERIFY REQUIRED')
        self.assertTrue(any(g.startswith('444000') for g in r['gates']))
        self.assertNotIn('Δ BALANCE', r['gates'])
        self.assertIn('VERIFY required; no approval granted', message(r))

    def test_m_space_inside_number_is_material(self):   # ADAPTED: rejected as invalid numeric
        for bad in ('1 2', '1_2'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ans(bad, '12')

    @unittest.skip("N/A by design: check recomputes from the plan, never runs on claims or item text")
    def test_n_self_test_runs_on_claims_not_item_text(self):
        pass

    def test_o_hold_gate_path_includes_spec_gates(self):   # SPEC: 555000 ... 999000 on the HOLD path
        for vals in [('400', '421'), ('412',), ('412', None)]:
            g = ev(*vals)['gates']
            self.assertEqual(g[:3], ['555000 TRIANGULATE', '144 HOLD', '999000 AUDIT'])
            self.assertIn('444000 VERIFY / HUMAN APPROVAL', g)

    def test_p_hold_outcome_label_for_insufficient_answers(self):   # SPEC: outcome HOLD, not NO_CHECK
        self.assertEqual(ev('412', None)['outcome'], 'HOLD')
        self.assertIsNone(ev('412', None)['check_outcome'])
        r = ev('400', '421')                               # check ran: label kept
        self.assertEqual((r['outcome'], r['check_outcome'], r['state']), ('NO_MATCH', 'NO_MATCH', '144 HOLD'))
        r = ev('412', '421', plan=Plan('SYNTHETIC-1', ('200', '212'), 'none'))
        self.assertEqual((r['outcome'], r['reason']), ('NO_CHECK', 'no_registered_check'))
        with patch('maniac.synth_shai_referee.check', side_effect=RuntimeError('x')):
            self.assertEqual(ev('412', None)['outcome'], 'HOLD')   # held before the check

    def test_r_check_exception_is_no_check_unstable(self):
        with patch('maniac.synth_shai_referee.check', side_effect=RuntimeError('private text')):
            r = ev('412', '421')
        self.assertEqual((r['outcome'], r['check_outcome'], r['reason'], r['state']),
                         ('NO_CHECK', 'NO_CHECK', 'check_unstable', '144 HOLD'))
        self.assertIs(r['approval_granted'], False); self.assertIsNone(r['verdict'])
        self.assertNotIn('private', str(r))

    def test_q_replay_rejected_not_persisted(self):
        import tempfile
        from pathlib import Path
        from maniac.synth_shai_referee import Journal
        with tempfile.TemporaryDirectory() as d:
            j = Journal(Path(d) / 'a.db')
            first = j.record(PLAN, ans('412', '421'), PLAN.commitment)
            r = j.record(PLAN, ans('421', '421'), PLAN.commitment)
            self.assertEqual((r['outcome'], r['state'], r['reason']), ('HOLD', '144 HOLD', 'replay_rejected'))
            self.assertIsNone(r['verdict']); self.assertIs(r['approval_granted'], False)
            self.assertNotIn('audit_anchor', r)
            self.assertTrue(j.verify(first['audit_anchor']))      # journal unchanged
            self.assertEqual(j.read('SYNTHETIC-1')['answers'][0]['raw'], '412')

    def test_s_raw_inputs_cannot_bypass_privacy_record(self):
        import tempfile
        from pathlib import Path
        from maniac.synth_shai_referee import Journal
        pii = 'jane.doe@example.com'
        tampered = ans('412')[0]
        object.__setattr__(tampered, 'raw', pii)            # frozen record tampered after construction
        cases = [
            (('SYNTHETIC-1', 'SYNTHETIC-1', 'SYNTHETIC-1', pii), ans('421', '421')[1]),     # raw tuple
            ({'model': 'SYNTHETIC-1', 'version': 'SYNTHETIC-1', 'attempt': 'SYNTHETIC-1', 'raw': pii},
             ans('421', '421')[1]),                                                           # raw dict
            (tampered, ans('421', '421')[1]),
        ]
        for i, aa in enumerate(cases):
            with self.subTest(case=i), tempfile.TemporaryDirectory() as d:
                self.assertEqual(evaluate(PLAN, aa, PLAN.commitment)['reason'], 'privacy_rejected')
                j = Journal(Path(d) / 'a.db')
                r = j.record(PLAN, aa, PLAN.commitment)
                self.assertEqual((r['outcome'], r['reason']), ('HOLD', 'privacy_rejected'))
                with j.connect() as db:
                    self.assertNotIn('jane.doe', repr(list(db.execute('SELECT * FROM audit'))))
                self.assertIn('raw_sha256', j.read('SYNTHETIC-1')['answers'][0])
        # raw tuples of valid numbers work like Answer
        r = evaluate(PLAN, (('SYNTHETIC-1', 'SYNTHETIC-1', 'SYNTHETIC-1', '412'),
                            ('SYNTHETIC-2', 'SYNTHETIC-1', 'SYNTHETIC-2', '421')), PLAN.commitment)
        self.assertEqual(r['outcome'], 'MATCH')
        self.assertEqual(evaluate(PLAN, (object(), object()), PLAN.commitment)['reason'], 'invalid_input')


if __name__ == '__main__':
    unittest.main()
