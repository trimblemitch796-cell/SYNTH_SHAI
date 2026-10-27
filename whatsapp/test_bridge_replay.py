"""Fix tests: webhook duplicate/replay protection and constant-time verify token."""
import hashlib, hmac, json, os, threading, unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from whatsapp import bridge
from whatsapp.bridge import SeenIds, new_messages, verify_token_ok


def payload(*ids):
    return {'object': 'whatsapp_business_account', 'entry': [{'changes': [{'field': 'messages', 'value': {
        'messages': [{'id': i, 'type': 'text', 'text': {'body': 'SHAI hi'}} for i in ids]}}]}]}


class SeenIdsTests(unittest.TestCase):
    def test_duplicate_id_dropped(self):
        seen = SeenIds()
        rows = bridge.extract_messages(payload('wamid.1', 'wamid.2'))
        self.assertEqual(len(new_messages(rows, seen)[0]), 2)
        fresh, dupes = new_messages(bridge.extract_messages(payload('wamid.1', 'wamid.3')), seen)
        self.assertEqual(([r['id'] for r in fresh], dupes), (['wamid.3'], 1))

    def test_same_id_twice_in_one_batch(self):
        fresh, dupes = new_messages(bridge.extract_messages(payload('a', 'a')), SeenIds())
        self.assertEqual((len(fresh), dupes), (1, 1))

    def test_ttl_expiry_and_bound(self):
        t = [0.0]
        seen = SeenIds(ttl=10, max_ids=2, clock=lambda: t[0])
        self.assertTrue(seen.first_time('a')); self.assertFalse(seen.first_time('a'))
        t[0] = 11
        self.assertTrue(seen.first_time('a'))          # expired
        seen.first_time('b'); seen.first_time('c')
        self.assertLessEqual(len(seen._ids), 2)        # bounded


class VerifyTokenTests(unittest.TestCase):
    def test_verify_token(self):
        self.assertTrue(verify_token_ok('tok', ['subscribe'], ['tok']))
        for mode, prov in [(['subscribe'], ['nope']), (['other'], ['tok']), (['subscribe'], None),
                           (['subscribe'], ['tok', 'tok'])]:
            self.assertFalse(verify_token_ok('tok', mode, prov))
        self.assertFalse(verify_token_ok('', ['subscribe'], ['']))

    def test_uses_compare_digest(self):
        with patch('whatsapp.bridge.hmac.compare_digest', return_value=False) as cd:
            self.assertFalse(verify_token_ok('tok', ['subscribe'], ['tok']))
            cd.assert_called_once()


class HttpReplayTests(unittest.TestCase):
    """End-to-end on 127.0.0.1 (loopback only): a retried webhook returns 200, no second HOLD."""
    def setUp(self):
        self.env = patch.dict(os.environ, {'SHAI_META_APP_SECRET': 's3cret', 'SHAI_VERIFY_TOKEN': 'tok'})
        self.env.start(); self.addCleanup(self.env.stop)
        seen = patch.object(bridge, 'SEEN', SeenIds()); seen.start(); self.addCleanup(seen.stop)
        self.srv = ThreadingHTTPServer(('127.0.0.1', 0), bridge.Handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close); self.addCleanup(self.srv.shutdown)

    def post(self, body):
        sig = 'sha256=' + hmac.new(b's3cret', body, hashlib.sha256).hexdigest()
        c = HTTPConnection('127.0.0.1', self.srv.server_port, timeout=5)
        c.request('POST', '/webhook', body, {'X-Hub-Signature-256': sig, 'Content-Type': 'application/json'})
        r = c.getresponse(); r.read(); c.close()
        return r.status

    def test_retry_is_200_without_second_hold(self):
        body = json.dumps(payload('wamid.X')).encode()
        logs = []
        with patch('builtins.print', side_effect=lambda *a, **k: logs.append(json.loads(a[0]))):
            self.assertEqual(self.post(body), 200)
            self.assertEqual(self.post(body), 200)
        self.assertEqual([(l['text_messages'], l['duplicates_ignored']) for l in logs], [(1, 0), (0, 1)])
        self.assertEqual(logs[0]['states'], ['144 HOLD']); self.assertEqual(logs[1]['states'], [])

    def test_get_verify(self):
        c = HTTPConnection('127.0.0.1', self.srv.server_port, timeout=5)
        c.request('GET', '/webhook?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=42')
        r = c.getresponse(); r.read(); c.close()
        self.assertEqual(r.status, 403)


if __name__ == '__main__':
    unittest.main()
