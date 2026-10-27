"""Fix tests: per-sender and global rate limits (dropped, no HOLD, still 200)."""
import hashlib, hmac, json, os, threading, unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from whatsapp import bridge
from whatsapp.bridge import RateLimiter, SeenIds, apply_rate_limit, extract_messages


def payload(sender, *ids):
    return {'object': 'whatsapp_business_account', 'entry': [{'changes': [{'field': 'messages', 'value': {
        'messages': [{'id': i, 'from': sender, 'type': 'text', 'text': {'body': 'hi'}} for i in ids]}}]}]}


class LimiterTests(unittest.TestCase):
    def test_per_sender_window(self):
        t = [0.0]
        lim = RateLimiter(per_sender=2, global_limit=100, window=10, clock=lambda: t[0])
        self.assertEqual([lim.allow('a') for _ in range(3)], [True, True, False])
        self.assertTrue(lim.allow('b'))                 # other sender unaffected
        t[0] = 11
        self.assertTrue(lim.allow('a'))                 # window slid

    def test_global_cap(self):
        lim = RateLimiter(per_sender=100, global_limit=3, window=10, clock=lambda: 0.0)
        self.assertEqual([lim.allow(str(i)) for i in range(5)], [True, True, True, False, False])

    def test_sender_only_hashed(self):
        rows = extract_messages(payload('61400000000', 'm1'))
        self.assertNotIn('61400000000', repr(rows))
        self.assertEqual(rows[0]['sender_sha256'], hashlib.sha256(b'61400000000').hexdigest())

    def test_apply_drops(self):
        rows = extract_messages(payload('s', 'm1', 'm2', 'm3'))
        kept, dropped = apply_rate_limit(rows, RateLimiter(per_sender=2, clock=lambda: 0.0))
        self.assertEqual((len(kept), dropped), (2, 1))

    def test_env_config(self):
        with patch.dict(os.environ, {'SHAI_RATE_PER_SENDER': '3', 'SHAI_RATE_GLOBAL': 'bad'}), \
             patch.object(bridge, 'LIMITER', None):
            lim = bridge.get_limiter()
            self.assertEqual((lim.per_sender, lim.global_limit), (3, 100))


class HttpRateLimitTests(unittest.TestCase):
    def test_over_limit_is_200_without_hold(self):
        env = patch.dict(os.environ, {'SHAI_META_APP_SECRET': 's3cret'}); env.start(); self.addCleanup(env.stop)
        for name, val in (('SEEN', SeenIds()), ('LIMITER', RateLimiter(per_sender=1, global_limit=10))):
            p = patch.object(bridge, name, val); p.start(); self.addCleanup(p.stop)
        srv = ThreadingHTTPServer(('127.0.0.1', 0), bridge.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close); self.addCleanup(srv.shutdown)
        logs, codes = [], []
        with patch('builtins.print', side_effect=lambda *a, **k: logs.append(json.loads(a[0]))):
            for mid in ('m1', 'm2'):
                body = json.dumps(payload('6140', mid)).encode()
                sig = 'sha256=' + hmac.new(b's3cret', body, hashlib.sha256).hexdigest()
                c = HTTPConnection('127.0.0.1', srv.server_port, timeout=5)
                c.request('POST', '/webhook', body, {'X-Hub-Signature-256': sig})
                r = c.getresponse(); r.read(); c.close(); codes.append(r.status)
        self.assertEqual(codes, [200, 200])
        self.assertEqual([(l['states'], l['rate_limited']) for l in logs], [(['144 HOLD'], 0), ([], 1)])


if __name__ == '__main__':
    unittest.main()
