import unittest
from decimal import Decimal
from shai_finance import Budget,repayment_schedule,reconcile,wellbeing_inputs,hardship_review,money
class FinanceTests(unittest.TestCase):
    def test_jobseeker_case(self):
        b=Budget('833.70','585','50','100','1000')
        self.assertEqual(b.remaining,Decimal('98.70'))
        self.assertEqual(b.months_of_essential_coverage,Decimal('0.79'))
    def test_missing_savings_not_zero(self):
        self.assertIsNone(Budget('100','90','0').months_of_essential_coverage)
    def test_shortfall(self):
        self.assertEqual(Budget(100,110,0).overview()['status'],'SHORTFALL')
    def test_reject_negative(self):
        with self.assertRaises(ValueError): Budget(-1,0,0)
    def test_reject_nan(self):
        with self.assertRaises(ValueError): money('NaN')
    def test_zero_rate_schedule(self):
        r=repayment_schedule(1200,0,100)
        self.assertEqual(r['months'],12); self.assertEqual(r['balance'],'0.00')
    def test_interest_only_flag(self):
        self.assertEqual(repayment_schedule(1200,12,12)['status'],'NOT_AMORTISING')
    def test_partial_final_payment(self):
        self.assertEqual(repayment_schedule(100,0,60)['months'],2)
    def test_unconfirmed_transfer(self):
        self.assertEqual(reconcile(600,0,True,False)['status'],'HOLD_UNCONFIRMED')
    def test_reference_mismatch(self):
        self.assertEqual(reconcile(600,600,False,True)['status'],'HOLD_REFERENCE_MISMATCH')
    def test_amount_mismatch(self):
        self.assertEqual(reconcile(600,500,True,True)['status'],'HOLD_AMOUNT_MISMATCH')
    def test_reconciled(self):
        self.assertEqual(reconcile(600,600,True,True)['status'],'MATCHED')
    def test_wellbeing_unknowns(self):
        w=wellbeing_inputs(Budget(100,50,0))
        self.assertIsNone(w['financial_autonomy_self_report']); self.assertEqual(w['composite_score'],'NOT_VALIDATED')
    def test_bad_self_report(self):
        with self.assertRaises(ValueError): wellbeing_inputs(Budget(100,50,0),11)
    def test_hardship_affordability(self):
        b=Budget(500,450,0)
        self.assertEqual(hardship_review(b,200,100)['scenario'],'SHORTFALL_OR_UNAFFORDABLE')
    def test_no_false_lender_approval(self):
        b=Budget(500,400,0)
        self.assertEqual(hardship_review(b,200,40)['scenario'],'ARITHMETICALLY_POSSIBLE_NOT_APPROVED')
if __name__=='__main__': unittest.main()
