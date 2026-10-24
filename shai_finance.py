"""SYNTH_SHAI Financial Decision Support V1 - offline, standard-library only.
No banking connections, money movement, personalised financial product recommendations.
All calculations use Decimal and AUD amounts supplied by operator.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

C = Decimal('0.01')
def money(value):
    d = Decimal(str(value))
    if not d.is_finite():
        raise ValueError('Finite amounts required')
    return d.quantize(C, rounding=ROUND_HALF_UP)

def nonnegative(value):
    v = money(value)
    if v < 0: raise ValueError('Amount cannot be negative')
    return v

@dataclass(frozen=True)
class Budget:
    income_fortnight: Decimal
    essential_fortnight: Decimal
    contracted_debt_fortnight: Decimal
    optional_spending_fortnight: Decimal = Decimal('0')
    liquid_savings: Optional[Decimal] = None

    def __post_init__(self):
        for key in ['income_fortnight','essential_fortnight','contracted_debt_fortnight','optional_spending_fortnight']:
            object.__setattr__(self, key, nonnegative(getattr(self,key)))
        if self.liquid_savings is not None:
            object.__setattr__(self,'liquid_savings',nonnegative(self.liquid_savings))

    @property
    def remaining(self):
        return self.income_fortnight-self.essential_fortnight-self.contracted_debt_fortnight-self.optional_spending_fortnight

    @property
    def essentials_monthly(self):
        return (self.essential_fortnight*Decimal(26)/Decimal(12)).quantize(C)

    @property
    def months_of_essential_coverage(self):
        if self.liquid_savings is None or not self.essential_fortnight:
            return None
        return (self.liquid_savings / (self.essential_fortnight*Decimal(26)/Decimal(12))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)

    def overview(self):
        return dict(income=str(self.income_fortnight), expenses=str(self.essential_fortnight+self.contracted_debt_fortnight+self.optional_spending_fortnight),remaining=str(self.remaining),months_essential_coverage=None if self.months_of_essential_coverage is None else str(self.months_of_essential_coverage),status='SHORTFALL' if self.remaining<0 else 'NON_NEGATIVE',needs_human_review=True)

def repayment_schedule(principal,annual_rate_percent,payment_monthly,max_months=600):
    """Illustrative fixed annual nominal interest rate, monthly compounding, end-of-month payment.
    No fees, rate variations, arrears or lender-specific allocation rules.
    """
    balance=nonnegative(principal)
    rate=nonnegative(annual_rate_percent)/Decimal(1200)
    payment=nonnegative(payment_monthly)
    if balance and payment <= balance*rate:
        return {'status':'NOT_AMORTISING','reason':'payment does not exceed first-month interest'}
    interest_total=Decimal('0'); months=0
    while balance and months<max_months:
        interest=money(balance*rate)
        due=balance+interest
        paid=min(payment,due)
        balance=money(due-paid)
        interest_total+=interest
        months+=1
    return {'status':'PAID' if balance==0 else 'NOT_PAID_WITHIN_HORIZON','months':months,'interest':str(money(interest_total)),'balance':str(balance)}

def reconcile(expected,recorded,reference_matches,settlement_confirmed):
    """Unknown/uncertain settlements never produce an instruction to resend."""
    e=nonnegative(expected); r=nonnegative(recorded)
    if not settlement_confirmed:
        return {'status':'HOLD_UNCONFIRMED','difference':str(e-r),'action':'Verify status with authorised bank channel; do not retry automatically'}
    if not reference_matches:
        return {'status':'HOLD_REFERENCE_MISMATCH','difference':str(e-r),'action':'Investigate identity/reference mismatch through bank'}
    return {'status':'MATCHED' if e==r else 'HOLD_AMOUNT_MISMATCH','difference':str(e-r),'action':'Record as matched' if e==r else 'Investigate discrepancy; do not retry automatically'}

def wellbeing_inputs(budget:Budget, autonomy_answer:Optional[int]=None,access_answer:Optional[int]=None):
    """Returns indicators, NEVER a validated composite rating.
    Optional autonomy/access self-reports range 0-10. Missing != zero.
    """
    for v in (autonomy_answer,access_answer):
        if v is not None and (not isinstance(v,int) or isinstance(v,bool) or not 0<=v<=10):
            raise ValueError('Self-report must be integer from 0 through 10')
    return dict(essential_affordable=budget.income_fortnight>=budget.essential_fortnight,
                after_obligations_margin=str(budget.remaining),
                emergency_coverage_months=None if budget.months_of_essential_coverage is None else str(budget.months_of_essential_coverage),
                financial_autonomy_self_report=autonomy_answer,
                payment_access_self_report=access_answer,
                composite_score='NOT_VALIDATED',
                note='Missing values remain unknown; do not infer security from wealth alone')

def hardship_review(budget:Budget, arrears, proposed_arrears_payment):
    arrears=nonnegative(arrears); proposed=nonnegative(proposed_arrears_payment)
    available=budget.remaining
    return dict(arrears=str(arrears),proposed_payment=str(proposed),headroom_after_proposal=str(money(available-proposed)),
                scenario='SHORTFALL_OR_UNAFFORDABLE' if available<proposed else 'ARITHMETICALLY_POSSIBLE_NOT_APPROVED',
                next_step='Seek lender hardship assessment; confirm loan terms and extra charges; preserve essentials. No automatic negotiation.')

if __name__=='__main__':
    case=Budget('833.70','585','50','0','1000')
    print('SYNTH_SHAI FINANCE — illustrative case only')
    print('Budget:',case.overview())
    print('Wellbeing:',wellbeing_inputs(case))
    print('Hardship:',hardship_review(case,'2400','50'))
    print('Uncertain transfer:',reconcile('600','0',True,False))
