"""Fix tests: persistent (SQLite) duplicate protection survives a restart."""
import hashlib, hmac, json, os, sqlite3, tempfile, threading, unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from whatsapp import bridge
from whatsapp.bridge import SqliteSeenIds


def payload(*ids):
    return {'object': 'whatsapp_business_account', 'entry': [{'changes': [{'field': 'messages', 'value': {
        'messages': [{'id': i, 'from': '61400000000', 'type': 'text', 'text': {'body': 'hi'}} for i in ids]}}]}]}


class SqliteSeenTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.addCleanup(self.d.cleanup)
        self.path = Path(self.d.name) / 'sub' / 'seen.sqlite'

    def test_survives_restart_and_stores_only_hash(self):
        self.assertTrue(SqliteSeenIds(self.path).first_time('wamid.A'))
        self.assertFalse(SqliteSeenIds(self.path).first_time('wamid.A'))    # new instance = restart
        with sqlite3.connect(self.path) as db:
            dump = repr(list(db.execute('SELECT * FROM seen')))
        db.close()
        self.assertNotIn('wamid.A', dump)
        self.assertIn(hashlib.sha256(b'wamid.A').hexdigest(), dump)

    def test_ttl_and_cap(self):
        t = [1000.0]
        s = SqliteSeenIds(self.path, ttl=10, max_ids=3, clock=lambda: t[0])
        self.assertTrue(s.first_time('a')); self.assertFalse(s.first_time('a'))
        t[0] += 11
        self.assertTrue(s.first_time('a'))
        for i in 'bcdef':
            t[0] += 1; s.first_time(i)
        self.assertEqual(s.count(), 3)

    def test_concurrent_first_time_only_once(self):
        s = SqliteSeenIds(self.path)
        out = []
        ts = [threading.Thread(target=lambda: out.append(s.first_time('same'))) for _ in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(out.count(True), 1)


class RestartHttpTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.addCleanup(self.d.cleanup)
        env = patch.dict(os.environ, {'SHAI_META_APP_SECRET': 's3cret', 'SHAI_VERIFY_TOKEN': 'tok',
                                      'SHAI_DEDUPE_DB': str(Path(self.d.name) / 'seen.sqlite')})
        env.start(); self.addCleanup(env.stop)
        p = patch.object(bridge, 'SEEN', None); p.start(); self.addCleanup(p.stop)
        lim = patch.object(bridge, 'LIMITER', None, create=True); lim.start(); self.addCleanup(lim.stop)

    def serve(self):
        srv = ThreadingHTTPServer(('127.0.0.1', 0), bridge.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv

    def post(self, srv, body):
        sig = 'sha256=' + hmac.new(b's3cret', body, hashlib.sha256).hexdigest()
        c = HTTPConnection('127.0.0.1', srv.server_port, timeout=5)
        c.request('POST', '/webhook', body, {'X-Hub-Signature-256': sig})
        r = c.getresponse(); r.read(); c.close()
        return r.status

    def test_duplicate_after_restart_is_200_no_second_hold(self):
        body = json.dumps(payload('wamid.R')).encode()
        logs = []
        with patch('builtins.print', side_effect=lambda *a, **k: logs.append(json.loads(a[0]))):
            srv = self.serve(); self.assertEqual(self.post(srv, body), 200); srv.shutdown(); srv.server_close()
            bridge.SEEN = None                                          # simulated process restart
            if hasattr(bridge, 'LIMITER'):
                bridge.LIMITER = None
            srv = self.serve(); self.assertEqual(self.post(srv, body), 200); srv.shutdown(); srv.server_close()
        self.assertEqual([l['states'] for l in logs], [['144 HOLD'], []])
        self.assertEqual(logs[1]['duplicates_ignored'], 1)

    def test_store_failure_fails_closed_503(self):
        class Broken:
            def first_time(self, _):
                raise sqlite3.OperationalError('disk')
        bridge.SEEN = Broken()
        with patch('builtins.print'):
            srv = self.serve()
            try:
                self.assertEqual(self.post(srv, json.dumps(payload('x')).encode()), 503)
            finally:
                srv.shutdown(); srv.server_close()


if __name__ == '__main__':
    unittest.main()
