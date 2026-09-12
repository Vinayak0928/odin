"""
tests/test_pid_inspector.py

Unit tests for P&ID Drawing inspector, ISA-5.1 tag parsing, and safety discrepancy audits.
"""

import os
import tempfile
import unittest
from PIL import Image

from src.tools.pid_inspector import (
    parse_pid_entities_from_text,
    audit_pid_safety_discrepancies,
    decompose_pid_tiles,
)


class TestPidInspector(unittest.TestCase):

    def test_parse_pid_entities_from_text(self):
        sample_ocr = """
        MRPL CDU-2 Unit P&ID Drawing Sheet 04
        Column C-101 overhead vapor line 12"-HC-101-A1A feeds into condenser E-102.
        Reflux drum V-103 collects condensate.
        Transmitters: Flow FT-101, Pressure PT-102, Level LT-103, Temp TT-104.
        Safety Valve: PSV-105 on drum V-103 set at 150 PSIG.
        Pumps: P-104A and P-104B discharge through check valves into 8"-HC-102-A1A.
        Control Valve: FCV-101 controls column reflux.
        """
        entities = parse_pid_entities_from_text(sample_ocr)

        # Check instruments
        inst_tags = {i["tag"] for i in entities["instruments"]}
        self.assertIn("FT-101", inst_tags)
        self.assertIn("PT-102", inst_tags)
        self.assertIn("LT-103", inst_tags)
        self.assertIn("TT-104", inst_tags)
        self.assertIn("PSV-105", inst_tags)

        # Check equipment
        eq_tags = {e["tag"] for e in entities["equipment"]}
        self.assertIn("C-101", eq_tags)
        self.assertIn("E-102", eq_tags)
        self.assertIn("V-103", eq_tags)
        self.assertIn("P-104A", eq_tags)

        # Check lines
        line_nums = {l["line_number"] for l in entities["piping_lines"]}
        self.assertIn('12"-HC-101-A1A', line_nums)
        self.assertIn('8"-HC-102-A1A', line_nums)

    def test_audit_pid_safety_discrepancies_missing_psv(self):
        # Pressure vessel present but NO PSV
        sample_ocr = """
        Flash Drum V-201 operates at 180 psig.
        Transmitters: PT-201, TT-201.
        """
        entities = parse_pid_entities_from_text(sample_ocr)
        discrepancies = audit_pid_safety_discrepancies(entities)

        critical_alerts = [d for d in discrepancies if d["severity"] == "CRITICAL"]
        self.assertGreaterEqual(len(critical_alerts), 1)
        self.assertIn("Pressure Safety", critical_alerts[0]["rule"])

    def test_decompose_pid_tiles(self):
        # Create a mock drawing image (2000 x 1500)
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_path = os.path.join(tmp_dir, "sample_pid.png")
            img = Image.new("RGB", (2000, 1500), color=(255, 255, 255))
            img.save(img_path)

            tiles = decompose_pid_tiles(img_path, output_dir=os.path.join(tmp_dir, "tiles"), tile_size=1024, overlap=200)
            self.assertGreater(len(tiles), 1)
            first_tile = tiles[0]
            self.assertEqual(first_tile["tile_index"], 0)
            self.assertEqual(first_tile["coordinates"]["x1"], 0)
            self.assertEqual(first_tile["coordinates"]["y1"], 0)
            self.assertTrue(os.path.exists(first_tile["tile_path"]))


if __name__ == "__main__":
    unittest.main()
