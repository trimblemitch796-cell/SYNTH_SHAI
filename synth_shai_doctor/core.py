"""AAA Doctor V1: conservative, non-diagnostic simulated decision support.

This is NOT a clinically validated triage tool. No patient treatment,
diagnosis, dispatch, medical device interfaces, or remote operations.
"""
from dataclasses import dataclass, asdict
from typing import Optional
import json

VERSION = 'AAA_SHA13_444000_V1'
EMERGENCY = 'EMERGENCY_ESCALATION'
REVIEW = 'CLINICIAN_REVIEW'
HOLD = '144_HOLD'

SYNTHETIC_PREFIX = 'SYNTHETIC-'
BOOL_FIELDS = ('consent', 'suspected_rupture', 'sudden_severe_abdominal_or_back_pain',
               'abdominal_or_back_pain', 'abdominal_tenderness', 'collapse_or_fainting',
               'compressive_symptoms', 'suspected_distal_embolisation',
               'suspected_aortic_dissection')


@dataclass(frozen=True)
class Case:
    case_id: str
    consent: bool
    suspected_rupture: bool = False
    known_aaa: Optional[bool] = None
    sudden_severe_abdominal_or_back_pain: bool = False
    abdominal_or_back_pain: bool = False
    abdominal_tenderness: bool = False
    collapse_or_fainting: bool = False
    compressive_symptoms: bool = False
    suspected_distal_embolisation: bool = False
    suspected_aortic_dissection: bool = False
    notes: str = ''

    def __post_init__(self):
        # FIX: strict types. Case(consent='no') used to count as True and skip
        # 144 HOLD, because any non-empty string is truthy in Python.
        if type(self.case_id) is not str or not self.case_id.strip():
            raise TypeError('case_id must be a non-empty str')
        # FIX: synthetic data only until external clinical review.
        if not self.case_id.startswith(SYNTHETIC_PREFIX):
            raise ValueError('case_id must start with %r (synthetic data only)' % SYNTHETIC_PREFIX)
        for name in BOOL_FIELDS:
            if type(getattr(self, name)) is not bool:
                raise TypeError('%s must be True or False' % name)
        if self.known_aaa is not None and type(self.known_aaa) is not bool:
            raise TypeError('known_aaa must be True, False or None')
        if type(self.notes) is not str:
            raise TypeError('notes must be a str')
        if self.notes:
            raise ValueError('notes must be empty (no free-text patient data until clinical review)')

@dataclass(frozen=True)
class Review:
    version: str
    case_id: str
    state: str
    triggers: tuple[str, ...]
    next_step: str
    human_approval_required: bool = True
    diagnosis_made: bool = False
    autonomous_dispatch: bool = False

    def __post_init__(self) -> None:
        # Safety invariants: a human must approve, no diagnosis, no dispatch.
        if self.human_approval_required is not True:
            raise ValueError('human_approval_required must be True')
        if self.diagnosis_made is not False:
            raise ValueError('diagnosis_made must be False')
        if self.autonomous_dispatch is not False:
            raise ValueError('autonomous_dispatch must be False')

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

def emergency_code(case: Case) -> tuple[str, ...]:
    """Flag explicit potentially life-threatening presentations (never rule out)."""
    flags = []
    if case.suspected_rupture:
        flags.append('Suspected ruptured abdominal aortic aneurysm')
    if case.suspected_aortic_dissection:
        flags.append('Suspected acute aortic dissection')
    if case.sudden_severe_abdominal_or_back_pain:
        flags.append('Sudden severe abdominal or back pain')
    if case.collapse_or_fainting:
        flags.append('Collapse or fainting')
    if (case.known_aaa is True and
        (case.abdominal_or_back_pain or case.abdominal_tenderness or
         case.compressive_symptoms or case.suspected_distal_embolisation)):
        flags.append('Known AAA with potentially symptomatic presentation')
    return tuple(flags)

def assess(case: Case) -> Review:
    """Escalation-first rule layer; missing information is never a negative test."""
    flags = emergency_code(case)
    if flags:
        return Review(VERSION, case.case_id, EMERGENCY, flags,
                      'Potential emergency: in Australia call 000 and ask for an ambulance. '
                      'Do not delay seeking care for this software. A clinician must assess.')
    if case.consent is not True:   # FIX: only a real True counts as consent
        return Review(VERSION, case.case_id, HOLD, ('Consent not provided',),
                      'Stop non-emergency case processing; request informed consent. '
                      'This is not evidence of medical safety.')
    if (case.abdominal_or_back_pain or case.abdominal_tenderness or
        case.compressive_symptoms or case.suspected_distal_embolisation):
        return Review(VERSION, case.case_id, REVIEW,
                      ('Symptoms require clinical assessment; AAA cannot be excluded',),
                      'Seek prompt medical evaluation. Escalate immediately if symptoms '
                      'are severe, sudden or worsening.')
    return Review(VERSION, case.case_id, REVIEW,
                  ('Information insufficient to rule out AAA or other illness',),
                  'Clinician assessment if concerned; screening, imaging and follow-up '
                  'decisions require qualified medical professionals.')

if __name__ == '__main__':
    example = Case(case_id='SYNTHETIC-001', consent=True,
                   known_aaa=True, abdominal_or_back_pain=True)
    print(assess(example).to_json())
