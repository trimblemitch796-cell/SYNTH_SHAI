"""Tests: 144 HOLD review queue (persistence, decisions, audit) and the
authenticated review endpoints. Offline: loopback HTTP only, no outbound calls."""
import hashlib
import hmac
import json
import os
import socket
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from whatsapp import bridge, review_queue
from whatsapp.bridge import RateLimiter, SeenIds
from whatsapp.review_queue import (APPROVED, PENDING, REJECTED, ReviewError, ReviewQueue)

TOKEN = 'r' * 40
ENV = {'SHAI_META_APP_SECRET': 's3cret', 'SHAI_VERIFY_TOKEN': 'verify-tok', 'SHAI_REVIEW_TOKEN': TOKEN}


def payload(*msgs):
    return {'object': 'whatsapp_business_account', 'entry': [{'changes': [{'field': 'messages', 'value': {
        'messages': [{'id': i, 'from': '61400000000', 'type': 'text', 'text': {'body': b}} for i, b in msgs]}}]}]}


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'q' / 'review.sqlite'
        self.q = ReviewQueue(self.path)

    def add(self, mid='wamid.1', body='hello SHAI'):
        return self.q.enqueue(mid, 'ab' * 32, body, 'draft', 'Human review required')

    def test_enqueue_idempotent_and_hashes_ids(self):
        a = self.add(); b = self.add()
        self.assertEqual(a, b)
        self.assertEqual(len(self.q.list_items()), 1)
        with closing(sqlite3.connect(self.path)) as db:
            dump = repr(list(db.execute('SELECT * FROM items')))
        self.assertNotIn('wamid.1', dump)
        self.assertIn(hashlib.sha256(b'wamid.1').hexdigest(), dump)

    def test_persists_across_restart(self):
        item = self.add()
        self.q.decide(item, 'approve', 'mitch', 'fine')
        q2 = ReviewQueue(self.path)                       # simulated restart
        got = q2.get(item)
        self.assertEqual((got['status'], got['decision']['reviewer'], got['sent']), (APPROVED, 'mitch', False))
        self.assertTrue(q2.verify_decisions())

    def test_approve_reject_and_listing(self):
        a, b, c = self.add('1'), self.add('2'), self.add('3')
        self.assertEqual(self.q.decide(a, 'approve', 'mitch', 'ok')['decision'], APPROVED)
        self.assertEqual(self.q.decide(b, 'reject', 'mitch', 'spam')['decision'], REJECTED)
        self.assertEqual([i['item_id'] for i in self.q.list_items(PENDING)], [c])
        self.assertEqual([i['item_id'] for i in self.q.list_items(APPROVED)], [a])
        self.assertEqual([i['item_id'] for i in self.q.list_items(REJECTED)], [b])

    def test_double_decide_refused_identical_is_idempotent(self):
        item = self.add()
        first = self.q.decide(item, 'approve', 'mitch', 'ok')
        again = self.q.decide(item, 'approve', 'mitch', 'ok')
        self.assertTrue(again['idempotent']); self.assertEqual(again['hash'], first['hash'])
        for action, who, why in [('reject', 'mitch', 'changed mind'), ('approve', 'other', 'ok'),
                                 ('approve', 'mitch', 'different reason')]:
            with self.subTest(action=action, who=who, why=why), self.assertRaises(ReviewError) as cm:
                self.q.decide(item, action, who, why)
            self.assertEqual(cm.exception.code, 'already_decided')
        self.assertEqual(len(self.q.audit_trail()), 1)

    def test_input_validation(self):
        item = self.add()
        for args, code in [((item, 'approve', 'mitch', ''), 'reason_required'),
                           ((item, 'approve', 'mitch', '   '), 'reason_required'),
                           ((item, 'approve', 'mitch', 'x' * 501), 'reason_required'),
                           ((item, 'approve', 'Mitch Smith!', 'ok'), 'invalid_reviewer'),
                           ((item, 'send', 'mitch', 'ok'), 'invalid_decision'),
                           (('HOLD-' + '0' * 32, 'approve', 'mitch', 'ok'), 'not_found'),
                           (('../etc', 'approve', 'mitch', 'ok'), 'invalid_item_id')]:
            with self.subTest(code=code), self.assertRaises(ReviewError) as cm:
                self.q.decide(*args)
            self.assertEqual(cm.exception.code, code)
        self.assertEqual(self.q.audit_trail(), [])

    def test_audit_trail_append_only_and_chained(self):
        ids = [self.add(str(i)) for i in range(3)]
        for i, item in enumerate(ids):
            self.q.decide(item, 'approve' if i % 2 == 0 else 'reject', 'mitch', 'reason %d' % i)
        trail = self.q.audit_trail()
        self.assertEqual([d['seq'] for d in trail], [1, 2, 3])
        self.assertEqual(trail[1]['prev_hash'], trail[0]['hash'])
        self.assertTrue(self.q.verify_decisions(trail[-1]['hash']))
        self.assertFalse(self.q.verify_decisions('f' * 64))
        with closing(sqlite3.connect(self.path)) as db:
            for sql in ("UPDATE decisions SET reason='edited'", 'DELETE FROM decisions',
                        'DELETE FROM items'):
                with self.subTest(sql=sql), self.assertRaises(sqlite3.DatabaseError):
                    db.execute(sql)
            # bypass the triggers to simulate a raw tamper: verification catches it
            db.execute('DROP TRIGGER decisions_no_update')
            db.execute("UPDATE decisions SET reason='edited' WHERE seq=2"); db.commit()
        self.assertFalse(self.q.verify_decisions())

    def test_no_outbound_code_or_calls(self):
        src = Path(review_queue.__file__).read_text()
        for word in ('urllib', 'http.client', 'requests', 'socket', 'subprocess', 'smtplib'):
            self.assertNotIn(word, src)
        with patch.object(socket, 'create_connection', side_effect=AssertionError('outbound')), \
             patch.object(socket.socket, 'connect', side_effect=AssertionError('outbound')):
            item = self.add()
            r = self.q.decide(item, 'approve', 'mitch', 'ok')
        self.assertEqual((r['decision'], r['sent']), (APPROVED, False))


class ReviewHttpTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, ENV); env.start(); self.addCleanup(env.stop)
        os.environ.pop('SHAI_REVIEW_ALLOW_REMOTE', None)
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.queue = ReviewQueue(Path(self.tmp.name) / 'review.sqlite')
        for name, val in (('SEEN', SeenIds()), ('LIMITER', RateLimiter()), ('REVIEW_QUEUE', self.queue)):
            p = patch.object(bridge, name, val); p.start(); self.addCleanup(p.stop)
        self.srv = ThreadingHTTPServer(('127.0.0.1', 0), bridge.Handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close); self.addCleanup(self.srv.shutdown)
        self.print = patch('builtins.print'); self.print.start(); self.addCleanup(self.print.stop)

    def call(self, method, path, body=None, token=TOKEN, headers=None):
        h = dict(headers or {})
        if token is not None:
            h['Authorization'] = 'Bearer ' + token
        data = json.dumps(body).encode() if isinstance(body, dict) else body
        c = HTTPConnection('127.0.0.1', self.srv.server_port, timeout=5)
        try:
            c.request(method, path, data, h)
            r = c.getresponse()
            raw = r.read()
        finally:
            c.close()
        ctype = r.getheader('Content-Type', '')
        return r.status, (json.loads(raw) if 'json' in ctype else raw.decode())

    def webhook(self, *msgs):
        body = json.dumps(payload(*msgs)).encode()
        sig = 'sha256=' + hmac.new(b's3cret', body, hashlib.sha256).hexdigest()
        return self.call('POST', '/webhook', body, token=None, headers={'X-Hub-Signature-256': sig})

    def test_webhook_creates_pending_hold_and_returns_200(self):
        self.assertEqual(self.webhook(('wamid.A', 'SHAI hello'))[0], 200)
        self.assertEqual(self.webhook(('wamid.A', 'SHAI hello'))[0], 200)    # retry: no second item
        status, data = self.call('GET', '/review/items')
        self.assertEqual(status, 200)
        self.assertEqual([(i['body'], i['status'], i['sent']) for i in data['items']],
                         [('SHAI hello', PENDING, False)])
        self.assertNotIn('61400000000', json.dumps(data))

    def test_auth_missing_wrong_right(self):
        self.assertEqual(self.call('GET', '/review/items', token=None)[0], 401)
        self.assertEqual(self.call('GET', '/review/items', token='x' * 40)[0], 401)
        self.assertEqual(self.call('GET', '/review/items', token='verify-tok')[0], 401)
        self.assertEqual(self.call('GET', '/review/items', headers={'Authorization': TOKEN}, token=None)[0], 401)
        self.assertEqual(self.call('GET', '/review/items')[0], 200)

    def test_fail_closed_without_proper_token(self):
        for env, err in [({'SHAI_REVIEW_TOKEN': ''}, 'review_disabled'),
                         ({'SHAI_REVIEW_TOKEN': 'short'}, 'review_token_too_short'),
                         ({'SHAI_REVIEW_TOKEN': 'v' * 40, 'SHAI_VERIFY_TOKEN': 'v' * 40}, 'review_token_reused'),
                         ({'SHAI_REVIEW_TOKEN': 's' * 40, 'SHAI_META_APP_SECRET': 's' * 40}, 'review_token_reused')]:
            with self.subTest(err=err), patch.dict(os.environ, env):
                status, data = self.call('GET', '/review/items', token=os.environ['SHAI_REVIEW_TOKEN'])
                self.assertEqual((status, data['error']), (503, err))

    def test_uses_constant_time_compare(self):
        with patch('whatsapp.bridge.hmac.compare_digest', return_value=False) as cd:
            self.assertFalse(bridge.review_auth_ok('Bearer ' + TOKEN))
        self.assertTrue(cd.called)

    def test_remote_clients_refused_by_default(self):
        self.assertFalse(bridge._loopback('192.168.1.5'))
        self.assertTrue(bridge._loopback('127.0.0.1')); self.assertTrue(bridge._loopback('::1'))

    def test_view_approve_reject_double_decide_audit(self):
        self.webhook(('m1', 'first'), ('m2', 'second'))
        items = self.call('GET', '/review/items')[1]['items']
        a, b = items[0]['item_id'], items[1]['item_id']
        self.assertEqual(self.call('GET', '/review/items/' + a)[1]['body'], 'first')
        st, d = self.call('POST', '/review/items/%s/approve' % a, {'reviewer': 'mitch', 'reason': 'ok to reply'})
        self.assertEqual((st, d['decision'], d['sent']), (200, APPROVED, False))
        st, d = self.call('POST', '/review/items/%s/approve' % a, {'reviewer': 'mitch', 'reason': 'ok to reply'})
        self.assertEqual((st, d['idempotent']), (200, True))
        self.assertEqual(self.call('POST', '/review/items/%s/reject' % a,
                                   {'reviewer': 'mitch', 'reason': 'no'})[0], 409)
        self.assertEqual(self.call('POST', '/review/items/%s/reject' % b, {'reviewer': 'mitch'})[0], 400)
        self.assertEqual(self.call('POST', '/review/items/%s/reject' % b,
                                   {'reviewer': 'mitch', 'reason': 'spam'})[1]['decision'], REJECTED)
        st, audit = self.call('GET', '/review/audit')
        self.assertEqual((st, audit['chain_ok'], [x['decision'] for x in audit['decisions']]),
                         (200, True, [APPROVED, REJECTED]))
        self.assertEqual(self.call('GET', '/review/items/HOLD-' + '0' * 32)[0], 404)
        self.assertEqual(self.call('POST', '/review/items/%s/approve' % b, b'not json')[0], 400)
        self.assertEqual(self.call('GET', '/review/items?status=bogus')[0], 400)

    def test_review_store_failure_on_webhook_is_503_and_retry_works(self):
        class Broken:
            def enqueue(self, *a):
                raise sqlite3.OperationalError('disk')
        with patch.object(bridge, 'REVIEW_QUEUE', Broken()):
            self.assertEqual(self.webhook(('wamid.F', 'hi'))[0], 503)
        self.assertEqual(self.webhook(('wamid.F', 'hi'))[0], 200)            # Meta retry accepted
        self.assertEqual(len(self.call('GET', '/review/items')[1]['items']), 1)

    def test_rate_limited_messages_create_no_hold(self):
        with patch.object(bridge, 'LIMITER', RateLimiter(per_sender=1)):
            self.assertEqual(self.webhook(('r1', 'a'), ('r2', 'b'))[0], 200)
        self.assertEqual(len(self.call('GET', '/review/items')[1]['items']), 1)


if __name__ == '__main__':
    unittest.main()
