import hashlib
import hmac
import unittest
from whatsapp.bridge import decide, extract_messages, verify_signature

class Tests(unittest.TestCase):
    def test_signed(self):
        data = b'hello'
        digest = hmac.new(b'secret', data, hashlib.sha256).hexdigest()
        self.assertTrue(verify_signature('secret', data, 'sha256='+digest))
        self.assertFalse(verify_signature('secret', data, 'sha256='+'0'*64))
        self.assertFalse(verify_signature('', data, 'sha256='+digest))
        self.assertFalse(verify_signature('secret', data, ''))
    def test_hold_default(self):
        for message in ('SHAI help','/compare reason','/status','anything',''):
            result = decide(message)
            self.assertEqual(result['state'], '144 HOLD')
    def test_extract(self):
        payload = {'object':'whatsapp_business_account','entry':[{'changes':[{'field':'messages','value':{'messages':[{'id':'a','type':'text','text':{'body':'/status'}},{'id':'b','type':'image'}]}}]}]}
        rows = extract_messages(payload)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['decision']['state'],'144 HOLD')
    def test_ignore_other_event(self):
        self.assertEqual(extract_messages({'object':'something_else'}), [])

if __name__ == '__main__': unittest.main()
