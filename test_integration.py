import tempfile
import unittest
from pathlib import Path
from maniac.synth_shai_referee import Answer
from whatsapp.referee_adapter import review_numeric_fixture
from whatsapp.bridge import decide


class IntegrationTests(unittest.TestCase):
    def test_offline_fixture_referee_never_sends(self):
        with tempfile.TemporaryDirectory() as d:
            answers = (
                Answer('SYNTHETIC-1', 'SYNTHETIC-1', 'SYNTHETIC-1', '412'),
                Answer('SYNTHETIC-2', 'SYNTHETIC-1', 'SYNTHETIC-2', '421'),
            )
            output = review_numeric_fixture('SYNTHETIC-97', ('200', '212'), answers, str(Path(d) / 'audit.sqlite'))
            self.assertFalse(output['sent'])
            self.assertFalse(output['result']['approval_granted'])
            self.assertEqual(output['result']['verdict'], '412')
            self.assertIn('VERIFY required', output['display_draft'])

    def test_whatsapp_compare_remains_hold_not_model_routing(self):
        self.assertEqual(decide('/compare 200+212')['state'], '144 HOLD')
