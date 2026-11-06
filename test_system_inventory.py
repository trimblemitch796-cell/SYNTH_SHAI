import tempfile
import unittest
from pathlib import Path
from ci.system_inventory import inventory


class SystemInventoryTests(unittest.TestCase):
    def test_empty_tree_never_claims_operational_shm(self):
        with tempfile.TemporaryDirectory() as d:
            data = inventory(Path(d))
        self.assertEqual(data["components"]["USHAI"]["status"], "INCOMPLETE")
        self.assertEqual(data["components"]["DEDICATED_AI_SHM"]["status"], "NOT_FOUND_IN_NAMED_PATHS")
        self.assertEqual(data["authorization"], "144 HOLD")
        self.assertEqual(data["evidence"], "SOURCE_INVENTORY_ONLY")

    def test_related_monitor_not_equivalent_to_ai_shm(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ["maniac/monitor.py", "maniac/evidence.py",
                         "test_maniac_monitor.py", "test_maniac_evidence.py"]:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("# synthetic fixture\n")
            data = inventory(root)
        self.assertEqual(data["components"]["SHM_RELATED_SENSOR_MONITOR"]["status"], "TESTS_CONFIGURED")
        self.assertEqual(data["components"]["DEDICATED_AI_SHM"]["status"], "NOT_FOUND_IN_NAMED_PATHS")

    def test_named_source_alone_does_not_establish_validation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "shm").mkdir()
            (root / "shm/__init__.py").write_text("# dummy\n")
            data = inventory(root)
        self.assertEqual(data["components"]["DEDICATED_AI_SHM"]["status"], "SOURCE_CANDIDATE_REQUIRES_REVIEW")
        self.assertEqual(data["authorization"], "144 HOLD")
