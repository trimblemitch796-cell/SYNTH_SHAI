# SYNTH_SHAI Financial Decision Support V1

**Status:** Offline educational prototype, not a licensed financial adviser, debt collector, banking interface, or validated financial-wellbeing instrument.

## Included
- `shai_finance.py`: Decimal-precision fortnightly cash flow, emergency liquidity coverage, fixed-rate illustrative debt amortisation, hardship affordability flag, cautious payment reconciliation, and wellbeing inputs (no unsupported composite score).
- `test_shai_finance.py`: standard-library unit tests for arithmetic, missing values, invalid input, non-amortising debt, unconfirmed payment handling and approvals.
- `VALIDATION.md`: results and remaining work.

## Use
Install Python 3.10+; no external packages or network required.

```sh
python shai_finance.py
python -m unittest -v test_shai_finance.py
```

## Boundaries
- No account linking, banking credentials, scraping, payments, transactions or third-party contact.
- Do not interpret an affordability calculation as lender approval, regulated advice, or entitlement calculation.
- Does not determine debts owed, tax, benefit eligibility, interest rates, fees or financial product suitability.
- All amounts and rates are operator-provided assumptions; replace with verified data only with consent.
- Missing values stay `None`, not zero. No personalised product selection.
- `144 HOLD`: automatic real-world financial actions prohibited. `444000`: required evidence and human authorisation for future scope changes.

## Official Australian references (checked 24 October 2026)
- https://moneysmart.gov.au/managing-debt/financial-hardship
- https://moneysmart.gov.au/financial-advice/general-and-personal-financial-advice
- https://moneysmart.gov.au/managing-debt/financial-counselling

Connection over control. Competence before authority.
