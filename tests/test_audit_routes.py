"""
tests/test_audit_routes.py

Integration tests for Cryptographic Merkle DAG Audit Trail API routes (SIH26117).
"""

import json
import os
import tempfile
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.audit_merkle import MerkleAuditLog, GENESIS_PREV_HASH
import core.audit_merkle as audit_merkle_mod
from core.auth import AuthManager
from routes.audit_routes import setup_audit_routes
from routes.auth_routes import setup_auth_routes


class TestAuditRoutes(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.log_path = os.path.join(self.tmp_dir.name, "audit_trail.jsonl")
        self.auth_path = os.path.join(self.tmp_dir.name, "auth.json")

        # Initialize mock instances
        self.audit_log = MerkleAuditLog(log_path=self.log_path)
        # Patch the singleton instance
        self._orig_instance = audit_merkle_mod._audit_log_instance
        audit_merkle_mod._audit_log_instance = self.audit_log

        self.auth_manager = AuthManager(auth_path=self.auth_path)
        self.auth_manager.create_user(
            "admin_user",
            "AdminSecret123!",
            is_admin=True,
            department="EXECUTIVE_MANAGEMENT",
            clearance="SECRET_EXECUTIVE",
        )
        self.auth_manager.create_user(
            "process_eng",
            "EngSecret123!",
            is_admin=False,
            department="PROCESS_ENGINEERING",
            clearance="RESTRICTED_ENGINEERING",
        )

        # Create FastAPI test application
        self.app = FastAPI()

        # Add mock state and current_user middleware for authentication
        @self.app.middleware("http")
        async def mock_auth_middleware(request, call_next):
            request.app.state.auth_manager = self.auth_manager
            # Default to admin user for test client
            request.state.current_user = request.headers.get("X-Test-User", "admin_user")
            response = await call_next(request)
            return response

        self.app.include_router(setup_audit_routes(self.auth_manager))
        self.app.include_router(setup_auth_routes(self.auth_manager))
        self.client = TestClient(self.app)

    def tearDown(self):
        audit_merkle_mod._audit_log_instance = self._orig_instance
        self.tmp_dir.cleanup()

    def test_audit_stats_endpoint(self):
        res = self.client.get("/api/audit/stats")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_blocks"], 0)
        self.assertEqual(data["genesis_hash"], GENESIS_PREV_HASH)
        self.assertEqual(data["merkle_root"], GENESIS_PREV_HASH)
        self.assertTrue(data["is_valid"])
        self.assertEqual(data["egress_status"], "0-WAN_VERIFIED_INTERNAL")
        self.assertEqual(data["compliance_status"], "CERTIFIED_TAMPER_EVIDENT")

    def test_audit_record_and_blocks_endpoint(self):
        # Record event
        payload = {
            "action": "API510_INSPECTION",
            "details": {"vessel": "V-101", "thickness": 1.25},
            "department": "MECHANICAL_INTEGRITY_NDT",
        }
        res_post = self.client.post("/api/audit/record", json=payload, headers={"X-Test-User": "inspector_1"})
        self.assertEqual(res_post.status_code, 200)
        block = res_post.json()["block"]
        self.assertEqual(block["index"], 0)
        self.assertEqual(block["action"], "API510_INSPECTION")
        self.assertEqual(block["user"], "inspector_1")
        self.assertEqual(block["prev_hash"], GENESIS_PREV_HASH)

        # Query blocks
        res_get = self.client.get("/api/audit/blocks")
        self.assertEqual(res_get.status_code, 200)
        blocks_data = res_get.json()
        self.assertEqual(blocks_data["count"], 1)
        self.assertEqual(blocks_data["blocks"][0]["hash"], block["hash"])

    def test_audit_verify_endpoint(self):
        # Record two events
        self.audit_log.record_event(
            user="eng1",
            department="PROCESS_ENGINEERING",
            action="CALC_PUMP",
            details={"pump": "P-101"},
        )
        self.audit_log.record_event(
            user="eng2",
            department="PROCESS_ENGINEERING",
            action="CALC_HEX",
            details={"exchanger": "E-101"},
        )

        # Verification passes
        res_verify = self.client.get("/api/audit/verify")
        self.assertEqual(res_verify.status_code, 200)
        data = res_verify.json()
        self.assertTrue(data["is_valid"])
        self.assertEqual(data["total_blocks_verified"], 2)
        self.assertEqual(len(data["discrepancies"]), 0)

        # Tamper test: corrupt the first line in the audit file
        with open(self.log_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        tampered_block = json.loads(lines[0])
        tampered_block["details"]["pump"] = "P-999_CORRUPTED"
        lines[0] = json.dumps(tampered_block)
        with open(self.log_path, "w", encoding="utf-8") as f:
            for l in lines:
                f.write(l + "\n")

        # Verify detects tampering
        res_tampered = self.client.get("/api/audit/verify")
        self.assertEqual(res_tampered.status_code, 200)
        tampered_data = res_tampered.json()
        self.assertFalse(tampered_data["is_valid"])
        self.assertEqual(tampered_data["compliance_status"], "TAMPERING_DETECTED")
        self.assertGreater(len(tampered_data["discrepancies"]), 0)

    def test_audit_root_endpoint(self):
        res = self.client.get("/api/audit/root")
        self.assertEqual(res.status_code, 200)
        self.assertIn("merkle_root", res.json())
        self.assertEqual(len(res.json()["merkle_root"]), 64)

    def test_audit_export_endpoint(self):
        self.audit_log.record_event(
            user="operator_1",
            department="OPERATIONS_TAR",
            action="SYSTEM_CHECK",
            details={"status": "nominal"},
        )
        res = self.client.get("/api/audit/export")
        self.assertEqual(res.status_code, 200)
        self.assertIn("SYSTEM_CHECK", res.text)

    def test_department_update_route(self):
        # Update process_eng to HSE_SAFETY
        payload = {
            "department": "HSE_SAFETY",
            "clearance": "RESTRICTED_ENGINEERING",
        }
        res = self.client.put(
            "/api/auth/users/process_eng/department",
            json=payload,
            headers={"X-Test-User": "admin_user"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["department"], "HSE_SAFETY")
        self.assertEqual(self.auth_manager.get_user_department("process_eng"), "HSE_SAFETY")


if __name__ == "__main__":
    unittest.main()
