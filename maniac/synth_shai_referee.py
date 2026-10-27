"""SYNTH_SHAI bounded offline numeric referee, version 0.1.0.
No model APIs, execution of submitted code, or approval authority.
"""
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from datetime import datetime, timezone


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def number(value):
    # Strings only: reject booleans, floats, exponents, NaN and unbounded inputs.
    if not isinstance(value, str) or len(value) > 80:
        raise ValueError('invalid_numeric_claim')
    if not re.fullmatch(r'\s*[+-]?\d{1,30}(?:\.\d{1,30})?\s*', value):
        raise ValueError('invalid_numeric_claim')
    return Fraction(value.strip())


def synthetic(value):
    if not isinstance(value, str) or not re.fullmatch(r'SYNTHETIC-[0-9]{1,12}', value):
        raise ValueError('synthetic_numeric_id_required')
    return value


@dataclass(frozen=True)
class Plan:
    """Construct BEFORE collecting answers. Immutable, bounded pinned input."""
    item_id: str
    operands: tuple
    check: str = 'exact_sum_v1'

    def __post_init__(self):
        synthetic(self.item_id)
        if type(self.operands) is not tuple or not 1 <= len(self.operands) <= 100:
            raise ValueError('invalid_operands')
        for operand in self.operands:
            number(operand)
        if self.check not in ('exact_sum_v1', 'none'):
            raise ValueError('unknown_check')

    @property
    def commitment(self):
        return digest({'plan': asdict(self), 'code_sha256': code_hash()})


def code_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True)
class Answer:
    # Model and version are numeric synthetic aliases; mapping is external.
    model: str
    version: str
    attempt: str
    raw: str | None

    def __post_init__(self):
        for value in (self.model, self.version, self.attempt):
            synthetic(value)
        if self.raw is not None:
            number(self.raw)


PRIVACY_REASONS = ('REDACTED: invalid_alias', 'REDACTED: invalid_numeric_claim')


@dataclass(frozen=True)
class RejectedAnswer:
    """An answer that failed the synthetic-data gate. Holds NO raw text:
    only the SHA-256 and length of the rejected input and a REDACTED marker."""
    model: str
    version: str
    attempt: str
    raw_sha256: str
    raw_length: int
    redacted: str

    def __post_init__(self):
        for value in (self.model, self.version, self.attempt):
            if value != 'REDACTED':
                synthetic(value)
        if type(self.raw_sha256) is not str or not re.fullmatch(r'[0-9a-f]{64}', self.raw_sha256):
            raise ValueError('invalid_rejected_answer')
        if type(self.raw_length) is not int or self.raw_length < 0:
            raise ValueError('invalid_rejected_answer')
        if self.redacted not in PRIVACY_REASONS:
            raise ValueError('invalid_rejected_answer')


def _alias_or_redacted(value):
    try:
        return synthetic(value)
    except ValueError:
        return None


def make_answer(model, version, attempt, raw):
    """Safe factory: returns a validated Answer, or a RejectedAnswer that keeps
    only sha256 + length + REDACTED marker. Answer() itself still raises."""
    try:
        return Answer(model, version, attempt, raw)
    except ValueError:
        pass
    aliases = [_alias_or_redacted(v) for v in (model, version, attempt)]
    if None in aliases:
        # The rejected record covers the whole answer, aliases included.
        blob, why = repr((model, version, attempt, raw)), PRIVACY_REASONS[0]
        aliases = ['REDACTED'] * 3
    else:
        blob, why = raw if isinstance(raw, str) else repr(raw), PRIVACY_REASONS[1]
    return RejectedAnswer(*aliases, hashlib.sha256(blob.encode('utf-8', 'replace')).hexdigest(),
                          len(blob), why)


_ANSWER_KEYS = ('model', 'version', 'attempt', 'raw')


def coerce_answers(answers):
    """Single privacy boundary for evaluate() and Journal.record().
    Every element is (re)built through make_answer(), so personal-looking or
    non-numeric input always becomes a RejectedAnswer (sha256 + length + REDACTED)
    and can never reach storage as raw text. Accepts Answer, RejectedAnswer,
    a 4-tuple (model, version, attempt, raw) or a dict with exactly those keys.
    Returns a tuple, or None for structurally invalid input (-> invalid_input HOLD)."""
    if type(answers) is not tuple or len(answers) > 16:
        return None
    out = []
    for a in answers:
        if type(a) is RejectedAnswer:
            try:
                a.__post_init__()
            except ValueError:
                return None
            out.append(a)
        elif type(a) is Answer:
            # Re-validate even frozen records (object.__setattr__ can tamper them).
            out.append(make_answer(a.model, a.version, a.attempt, a.raw))
        elif type(a) is tuple and len(a) == 4:
            out.append(make_answer(*a))
        elif type(a) is dict and tuple(sorted(a)) == tuple(sorted(_ANSWER_KEYS)):
            out.append(make_answer(*(a[k] for k in _ANSWER_KEYS)))
        else:
            return None
    return tuple(out)


def check(plan):
    return str(sum((number(x) for x in plan.operands), Fraction(0)))


# Route labels per docs/DISAGREEMENT_REFEREE_SPEC.md section 6. Labels only:
# evaluate() does not itself audit; Journal.record() is the 999000 step.
HOLD_GATES = ('555000 TRIANGULATE', '144 HOLD', '999000 AUDIT', '444000 VERIFY / HUMAN APPROVAL')
MATCH_GATES = ('555000 TRIANGULATE', '999000 AUDIT', '444000 VERIFY REQUIRED')


def evaluate(plan, answers, commitment):
    """Pure decision. Unsupported/invalid data fail closed; no input text echoed."""
    # outcome per spec section 5: MATCH / NO_MATCH / NO_CHECK from the check, or HOLD
    # (with reason) when the item is held before/without a check result.
    # check_outcome keeps the underlying check result (None = check not run).
    base = dict(outcome='HOLD', check_outcome=None, state='144 HOLD', approval_granted=False,
                verdict=None, reason='invalid_input', winners=[], losers=[],
                disagreement=False, cosmetic_diff=False, check_output=None,
                note='', gates=list(HOLD_GATES))
    try:
        answers = coerce_answers(answers)
        if type(plan) is not Plan or answers is None:
            return base
        if commitment != plan.commitment:
            return dict(base, reason='commitment_mismatch')
        # Revalidate frozen records as a defensive boundary.
        plan.__post_init__()
        for a in answers:
            a.__post_init__()
        if any(type(a) is RejectedAnswer for a in answers):
            # Synthetic-data gate, reject-by-default: hash + length + REDACTED only.
            return dict(base, reason='privacy_rejected')
        if len({a.attempt for a in answers}) != len(answers):
            return dict(base, reason='duplicate_attempt')
        present = [a for a in answers if a.raw is not None]
        if len(present) < 2:
            return dict(base, reason='insufficient_answers')
        values = {number(a.raw) for a in present}
        disagreement = len(values) > 1
        base.update(disagreement=disagreement,
                    cosmetic_diff=len(values) == 1 and len({a.raw for a in present}) > 1,
                    note='Models disagreed; unresolved.' if disagreement else '')
        if plan.check == 'none':
            return dict(base, outcome='NO_CHECK', check_outcome='NO_CHECK', reason='no_registered_check')
        try:
            first, second = check(plan), check(plan)
        except Exception:
            # Spec: a check that errors is unstable -> NO_CHECK / check_unstable -> HOLD.
            # The exception text is never echoed.
            return dict(base, outcome='NO_CHECK', check_outcome='NO_CHECK', reason='check_unstable')
        if first != second:
            return dict(base, outcome='NO_CHECK', check_outcome='NO_CHECK', reason='check_unstable')
        expected = Fraction(first)
        winners = [a.attempt for a in present if number(a.raw) == expected]
        losers = [{'attempt': a.attempt, 'reason': 'exact_sum_mismatch'}
                  for a in present if number(a.raw) != expected]
        if not winners:
            return dict(base, outcome='NO_MATCH', check_outcome='NO_MATCH', reason='no_claim_matches',
                        check_output=first, losers=losers)
        # This check binds every passing answer to ONE exact value.
        return dict(base, outcome='MATCH', check_outcome='MATCH', state='444000 VERIFY REQUIRED',
                    verdict=first, reason='exact_sum_match', winners=winners,
                    losers=losers, check_output=first,
                    note='Models disagreed; exact recomputation resolved the total.' if disagreement else '',
                    gates=list(MATCH_GATES))
    except Exception:
        return dict(base, reason='internal_error')


class Journal:
    """Transactional append API; separate linked audit/disagreement tables.
    SQLite serializes writers. Hash-chain detects edits, not complete rewrites.
    Keep the returned anchor externally to detect deletion/rewrite.
    """
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS audit (
              seq INTEGER PRIMARY KEY, item_id TEXT UNIQUE NOT NULL,
              payload TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS disagreements (
              audit_ref TEXT PRIMARY KEY, payload TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        """Yields a connection: commits on success, rolls back on error, ALWAYS closes.
        (sqlite3's own context manager commits but never closes.)"""
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def verify(self, expected_anchor=None):
        try:
            with self.connect() as db:
                return self._verify(db, expected_anchor)
        except (sqlite3.Error, ValueError, TypeError, KeyError):
            return False

    @staticmethod
    def _verify(db, expected_anchor=None):
        previous = '0' * 64
        expected_flags = {}
        for index, row in enumerate(db.execute('SELECT seq,item_id,payload,previous,hash FROM audit ORDER BY seq'), 1):
            seq, item, payload, prev, current = row
            data = json.loads(payload)
            if seq != index or prev != previous or current != digest([previous, data]) or data['item_id'] != item:
                return False
            if data['result']['disagreement']:
                expected_flags[current] = payload
            previous = current
        actual = dict(db.execute('SELECT audit_ref,payload FROM disagreements'))
        return actual == expected_flags and (expected_anchor is None or previous == expected_anchor)

    def record(self, plan, answers, commitment):
        # Persist exactly what was evaluated: the coerced (privacy-gated) answers.
        answers = coerce_answers(answers)
        result = evaluate(plan, answers, commitment)
        if result['reason'] in ('invalid_input', 'internal_error', 'commitment_mismatch', 'duplicate_attempt'):
            return result  # Do not persist unvalidated input.
        payload = dict(item_id=plan.item_id, item_sha256=digest(asdict(plan)),
                       timestamp=datetime.now(timezone.utc).isoformat(),
                       check={'id': plan.check, 'version': '1', 'code_sha256': code_hash(),
                              'commitment': commitment},
                       answers=[asdict(a) for a in answers], result=result,
                       human_decision=None)
        try:
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if not self._verify(db):
                    raise ValueError('journal_integrity')
                if db.execute('SELECT 1 FROM audit WHERE item_id=?', (plan.item_id,)).fetchone():
                    db.rollback()
                    return dict(result, outcome='HOLD', state='144 HOLD', verdict=None,
                                reason='replay_rejected', gates=list(HOLD_GATES))  # not persisted
                last = db.execute('SELECT hash FROM audit ORDER BY seq DESC LIMIT 1').fetchone()
                previous = last[0] if last else '0' * 64
                anchor = digest([previous, payload])
                text = encode(payload)
                db.execute('INSERT INTO audit(item_id,payload,previous,hash) VALUES (?,?,?,?)',
                           (plan.item_id, text, previous, anchor))
                if result['disagreement']:
                    db.execute('INSERT INTO disagreements VALUES (?,?)', (anchor, text))
            return dict(result, audit_anchor=anchor)
        except (sqlite3.Error, ValueError, TypeError, KeyError):
            return dict(outcome='HOLD', check_outcome=result.get('check_outcome'),
                        state='144 HOLD', approval_granted=False,
                        verdict=None, reason='audit_failed', disagreement=result['disagreement'],
                        gates=list(HOLD_GATES))

    def read(self, item_id):
        synthetic(item_id)
        with self.connect() as db:
            if not self._verify(db):
                raise ValueError('journal_integrity')
            row = db.execute('SELECT payload FROM audit WHERE item_id=?', (item_id,)).fetchone()
            return json.loads(row[0]) if row else None


def message(result):
    if result['state'] == '144 HOLD':
        return '144 HOLD — awaiting human review'
    suffix = ('\n' + result['note']) if result['note'] else ''
    return f"Checked answer: {result['verdict']}. 444000 VERIFY required; no approval granted.{suffix}"


if __name__ == '__main__':
    plan = Plan('SYNTHETIC-1', ('200', '212'))
    commitment = plan.commitment  # Capture before requesting answers.
    answers = (Answer('SYNTHETIC-1', 'SYNTHETIC-1', 'SYNTHETIC-1', '412'),
               Answer('SYNTHETIC-2', 'SYNTHETIC-1', 'SYNTHETIC-2', '421'))
    print(message(evaluate(plan, answers, commitment)))
