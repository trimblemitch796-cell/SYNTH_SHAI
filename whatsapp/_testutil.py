"""Test helper: give a test its own temporary review queue so HTTP webhook tests
never write into the repo's .shai_data/."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from whatsapp import bridge
from whatsapp.review_queue import ReviewQueue


def isolate_review_queue(testcase):
    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    queue = ReviewQueue(Path(tmp.name) / 'review.sqlite')
    p = patch.object(bridge, 'REVIEW_QUEUE', queue)
    p.start()
    testcase.addCleanup(p.stop)
    return queue
