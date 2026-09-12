"""
tests/test_audit_merkle.py

Unit tests for cryptographic Merkle DAG audit logger and tamper detection.
"""

import json
import os
import tempfile
import unittest

from core.audit_merkle import MerkleAuditLog, GENESIS_PREV_HASH


class TestMerkleAuditLog(unittest.TestCase):

    def test_audit_hash_chaining(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, "test_audit.jsonl")
            audit = MerkleAuditLog(log_path=log_file)

            block0 = audit.record_event(
                user="vinay",
                department="PROCESS_ENGINEERING",
                action="LOGIN",
                details={"ip": "127.0.0.1"},
            )
            self.assertEqual(block0["index"], 0)
            self.assertEqual(block0["prev_hash"], GENESIS_PREV_HASH)
            self.assertTrue(block0["hash"])

            block1 = audit.record_event(
                user="vinay",
                department="PROCESS_ENGINEERING",
                action="TOOL_EXECUTION",
                details={"tool": "calc_vessel_thickness_api510", "vessel": "V-101"},
            )
            self.assertEqual(block1["index"], 1)
            self.assertEqual(block1["prev_hash"], block0["hash"])

            # Verify integrity
            is_valid, issues = audit.verify_audit_chain()
            self.assertTrue(is_valid)
            self.assertEqual(len(issues), 0)

    def test_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, "test_audit.jsonl")
            audit = MerkleAuditLog(log_path=log_file)

            audit.record_event(
                user="operator",
                department="OPERATIONS_TAR",
                action="START_PURGE",
                details={"reactor": "R-101"},
            )
            audit.record_event(
                user="inspector",
                department="MECHANICAL_INTEGRITY_NDT",
                action="INSPECTION_PASS",
                details={"thickness": 1.25},
            )

            # Corrupt the first block manually
            with open(log_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]

            block0 = json.loads(lines[0])
            block0["details"]["reactor"] = "R-999_TAMPERED"
            lines[0] = json.dumps(block0)

            with open(log_file, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(line + "\n")

            # Re-read and verify chain detects tampering
            audit_tampered = MerkleAuditLog(log_path=log_file)
            is_valid, issues = audit_tampered.verify_audit_chain()
            self.assertFalse(is_valid)
            self.assertGreater(len(issues), 0)
            self.assertTrue(any("Tampered block hash" in issue or "Prev hash mismatch" in issue for issue in issues))

    def test_merkle_root_computation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, "test_audit.jsonl")
            audit = MerkleAuditLog(log_path=log_file)

            for i in range(4):
                audit.record_event(user=f"user_{i}", department="PROCESS_ENGINEERING", action=f"ACTION_{i}", details={})

            root = audit.compute_merkle_root()
            self.assertEqual(len(root), 64)  # 64-char SHA-256 hex string


if __name__ == "__main__":
    unittest.main()
