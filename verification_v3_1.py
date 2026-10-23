"""SYNTH_SHAI V3.1: strict-scope authenticated evidence and durable replay gate.

Only run this against explicitly provisioned trusted public keys. REVIEW_REQUIRED
is not approval. SQLite replay storage is local and requires protected access.
"""
import re
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from verification_v3 import verify_result as verify_v3, HOLD, REVIEW_REQUIRED

_ID = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
_CHALLENGE = re.compile(r"^[A-Za-z0-9_.:-]{16,128}$")
_SIGNED = {"source_id", "key_id", "source_revision", "report_sha256", "challenge", "signature"}
_TOP = {"test_report", "source_revision", "challenge", "verification_evidence"}


def verify_result(record, *, trusted_keys=None, expected_sha256=None,
                  expected_challenge=None, used_challenges=None):
    """Check record and optional known-used challenges. Does not mark as used."""
    try:
        if not isinstance(record, dict) or set(record) != _TOP:
            return HOLD
        if not isinstance(record['test_report'], str) or not 0 < len(record['test_report'].encode('utf8')) <= 1_000_000:
            return HOLD
        if not isinstance(record['source_revision'], str) or not _ID.fullmatch(record['source_revision']):
            return HOLD
        if not isinstance(record['challenge'], str) or not _CHALLENGE.fullmatch(record['challenge']):
            return HOLD
        if not isinstance(trusted_keys, Mapping) or len(trusted_keys) != 2:
            return HOLD
        for kid, config in trusted_keys.items():
            if not isinstance(kid, str) or not _ID.fullmatch(kid):
                return HOLD
            if not isinstance(config, Mapping) or set(config) != {'source_id', 'public_key'}:
                return HOLD
            if not isinstance(config['source_id'], str) or not _ID.fullmatch(config['source_id']):
                return HOLD
        entries = record['verification_evidence']
        if not isinstance(entries, list) or len(entries) != 2:
            return HOLD
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != _SIGNED:
                return HOLD
            if not isinstance(entry['signature'], str) or len(entry['signature']) != 128 or any(c not in '0123456789abcdef' for c in entry['signature']):
                return HOLD
        if used_challenges is not None:
            if not isinstance(used_challenges, (set, frozenset)):
                return HOLD
            if record['challenge'] in used_challenges:
                return HOLD
        return verify_v3(record, trusted_keys=trusted_keys,
                         expected_sha256=expected_sha256,
                         expected_challenge=expected_challenge)
    except (ValueError, TypeError, UnicodeError, OverflowError):
        return HOLD


def verify_once(record, *, database_path, trusted_keys, expected_sha256, expected_challenge):
    """Atomic, durable single-use challenge check for local offline execution.

    sqlite file must be access-controlled; corruption/DB errors fail closed.
    This does not solve cross-machine replay or signer trust provisioning.
    """
    try:
        if not isinstance(database_path, (str, Path)) or not str(database_path):
            return HOLD
        with sqlite3.connect(str(database_path), timeout=3) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS used_challenges (challenge TEXT PRIMARY KEY)')
            state = verify_result(record, trusted_keys=trusted_keys,
                                  expected_sha256=expected_sha256,
                                  expected_challenge=expected_challenge)
            if state != REVIEW_REQUIRED:
                db.rollback()
                return HOLD
            db.execute('INSERT INTO used_challenges(challenge) VALUES (?)', (record['challenge'],))
            db.commit()
            return REVIEW_REQUIRED
    except (sqlite3.Error, ValueError, TypeError, OSError):
        return HOLD
