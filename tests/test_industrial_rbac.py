"""
tests/test_industrial_rbac.py

Unit tests for MRPL Departmental RBAC and document classification clearance levels.
"""

import os
import tempfile
import unittest

from core.auth import AuthManager, DEPARTMENT_ROLES, CLEARANCE_LEVELS


class TestIndustrialRBAC(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.auth_file = os.path.join(self.tmp_dir.name, "auth.json")
        self.auth = AuthManager(auth_path=self.auth_file)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_department_assignment_and_tool_access(self):
        # Create admin
        self.auth.create_user("admin_user", "AdminSecret123!", is_admin=True)

        # Create Process Engineer
        self.auth.create_user(
            "process_eng",
            "EngSecret123!",
            is_admin=False,
            department="PROCESS_ENGINEERING",
            clearance="RESTRICTED_ENGINEERING",
        )

        # Create General Operator
        self.auth.create_user(
            "operator_1",
            "OpSecret123!",
            is_admin=False,
            department="GENERAL_OPERATIONS",
            clearance="UNCLASSIFIED",
        )

        # Verify department resolution
        self.assertEqual(self.auth.get_user_department("process_eng"), "PROCESS_ENGINEERING")
        self.assertEqual(self.auth.get_user_department("operator_1"), "GENERAL_OPERATIONS")

        # Process Engineer can execute hydraulics and heat exchanger tools
        self.assertTrue(self.auth.check_department_tool_access("process_eng", "calc_pump_hydraulics"))
        self.assertTrue(self.auth.check_department_tool_access("process_eng", "calc_heat_exchanger_duty"))

        # General Operator is blocked from calculating pressure vessel thickness
        self.assertFalse(self.auth.check_department_tool_access("operator_1", "calc_vessel_thickness_api510"))

        # Admin user bypasses all checks
        self.assertTrue(self.auth.check_department_tool_access("admin_user", "calc_vessel_thickness_api510"))

    def test_document_clearance_levels(self):
        self.auth.create_user(
            "exec_user",
            "ExecSecret123!",
            is_admin=False,
            department="EXECUTIVE_MANAGEMENT",
            clearance="SECRET_EXECUTIVE",
        )
        self.auth.create_user(
            "junior_tech",
            "TechSecret123!",
            is_admin=False,
            department="GENERAL_OPERATIONS",
            clearance="UNCLASSIFIED",
        )

        # Executive clearance can access SECRET, RESTRICTED, CONFIDENTIAL, UNCLASSIFIED
        self.assertTrue(self.auth.check_document_clearance("exec_user", "SECRET_EXECUTIVE"))
        self.assertTrue(self.auth.check_document_clearance("exec_user", "RESTRICTED_ENGINEERING"))
        self.assertTrue(self.auth.check_document_clearance("exec_user", "UNCLASSIFIED"))

        # Junior tech can only access UNCLASSIFIED
        self.assertTrue(self.auth.check_document_clearance("junior_tech", "UNCLASSIFIED"))
        self.assertFalse(self.auth.check_document_clearance("junior_tech", "RESTRICTED_ENGINEERING"))
        self.assertFalse(self.auth.check_document_clearance("junior_tech", "SECRET_EXECUTIVE"))


if __name__ == "__main__":
    unittest.main()
