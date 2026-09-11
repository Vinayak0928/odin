"""
tests/test_industrial_calc.py

Unit tests for MRPL industrial engineering calculation engines (SIH26117).
"""

import unittest
from src.tools.industrial_calc import (
    calculate_vessel_thickness_api510,
    calculate_pipe_thickness_api570,
    calculate_pump_hydraulics,
    calculate_heat_exchanger_duty,
    optimize_crude_blend,
    plan_refinery_turnaround,
)


class TestIndustrialCalc(unittest.TestCase):

    def test_api510_vessel_thickness_acceptable(self):
        # Pressure P=300 psi, Radius R=48 in, Stress S=20000 psi, Joint E=0.85
        # Denominator = 20000 * 0.85 - 0.6 * 300 = 17000 - 180 = 16820 psi
        # t_min = (300 * 48) / 16820 = 14400 / 16820 = 0.8561 in
        res = calculate_vessel_thickness_api510(
            design_pressure_psi=300.0,
            inside_radius_in=48.0,
            allowable_stress_psi=20000.0,
            joint_efficiency=0.85,
            actual_thickness_in=1.10,
            corrosion_rate_mpy=10.0,
            vessel_tag="V-101",
        )
        self.assertEqual(res["vessel_tag"], "V-101")
        self.assertAlmostEqual(res["minimum_required_thickness_in"], 0.8561, places=3)
        self.assertGreater(res["remaining_life_years"], 20.0)
        self.assertEqual(res["next_inspection_interval_years"], 10.0)  # capped at 10 years per API 510
        self.assertEqual(res["status"], "ACCEPTABLE")

    def test_api510_vessel_thickness_critical_breach(self):
        # Actual thickness 0.80 in < t_min (~0.8561 in)
        res = calculate_vessel_thickness_api510(
            design_pressure_psi=300.0,
            inside_radius_in=48.0,
            allowable_stress_psi=20000.0,
            joint_efficiency=0.85,
            actual_thickness_in=0.80,
            corrosion_rate_mpy=15.0,
            vessel_tag="V-102",
        )
        self.assertEqual(res["status"], "CRITICAL_RETIREMENT_LIMIT_REACHED")
        self.assertEqual(res["remaining_life_years"], 0.0)
        self.assertIn("breached minimum required thickness", res["alert_message"])

    def test_api570_pipe_thickness(self):
        res = calculate_pipe_thickness_api570(
            design_pressure_psi=250.0,
            outside_diameter_in=8.625,
            allowable_stress_psi=16000.0,
            joint_efficiency=1.0,
            actual_thickness_in=0.322,
            corrosion_rate_mpy=8.0,
            pipe_class="Class 1",
            pipe_tag="8-HC-101",
        )
        self.assertEqual(res["pipe_tag"], "8-HC-101")
        self.assertGreater(res["actual_thickness_in"], res["minimum_required_thickness_in"])
        self.assertGreater(res["remaining_life_years"], 0.0)
        self.assertLessEqual(res["next_inspection_interval_years"], 5.0)  # Class 1 capped at 5 years

    def test_pump_hydraulics_safe(self):
        res = calculate_pump_hydraulics(
            flow_rate_gpm=500.0,
            pipe_diameter_in=6.0,
            pipe_length_ft=100.0,
            fluid_viscosity_cp=1.0,
            fluid_density_lb_cuft=62.4,
            suction_static_head_ft=20.0,
            vapor_pressure_psia=2.0,
            pump_npsh_required_ft=8.0,
            pump_tag="P-101A",
        )
        self.assertIn("cavitation_status", res)
        self.assertGreater(res["npsh_available_ft"], res["npsh_required_ft"])
        self.assertEqual(res["cavitation_status"], "SAFE_OPERATION")

    def test_heat_exchanger_duty_lmtd(self):
        # Hot stream 180 C -> 110 C, Cold stream 30 C -> 80 C
        # delta_T1 = 180 - 80 = 100 C, delta_T2 = 110 - 30 = 80 C
        # LMTD = (100 - 80) / ln(100/80) = 20 / 0.2231 = 89.63 C
        res = calculate_heat_exchanger_duty(
            hot_inlet_temp_c=180.0,
            hot_outlet_temp_c=110.0,
            cold_inlet_temp_c=30.0,
            cold_outlet_temp_c=80.0,
            hot_mass_flow_kg_s=20.0,
            hot_specific_heat_kj_kg_c=2.5,
            overall_u_w_m2_c=500.0,
            exchanger_tag="E-101",
        )
        self.assertEqual(res["exchanger_tag"], "E-101")
        self.assertAlmostEqual(res["thermal_duty_kw"], 3500.0, places=1)
        self.assertAlmostEqual(res["lmtd_celsius"], 89.63, places=1)
        self.assertGreater(res["required_surface_area_m2"], 0.0)

    def test_crude_blend_optimizer(self):
        crudes = [
            {"name": "Arab Light", "sulfur_wt": 1.95, "api_gravity": 33.0},
            {"name": "Bonny Light", "sulfur_wt": 0.15, "api_gravity": 36.0},
        ]
        res = optimize_crude_blend(
            crude_candidates=crudes,
            target_max_sulfur_wt=1.5,
            target_min_api_gravity=30.0,
            total_bpd=100000.0,
        )
        self.assertIn("blend_sulfur_wt", res)
        self.assertTrue(res["spec_compliant"])
        self.assertEqual(res["status"], "OPTIMAL_BLEND_FEASIBLE")
        self.assertIn("estimated_tbp_yields", res)
        self.assertIn("middle_distillates_kero_diesel_pct", res["estimated_tbp_yields"])
        self.assertIn("compatibility_index", res)
        self.assertEqual(res["compatibility_index"]["status"], "COMPATIBLE_STABLE_BLEND")

    def test_plan_refinery_turnaround(self):
        res = plan_refinery_turnaround(
            unit_name="CDU-1",
            turnaround_type="MAJOR_REVAMP",
            target_duration_days=35,
            include_blind_list=True,
        )
        self.assertEqual(res["unit_name"], "CDU-1")
        self.assertEqual(res["total_duration_days"], 35)
        self.assertEqual(len(res["critical_path_phases"]), 7)
        self.assertGreater(res["blind_isolation_summary"]["total_blinds_required"], 0)
        self.assertEqual(res["status"], "TURNAROUND_PLAN_GENERATED")
        # Check first and last phase
        self.assertEqual(res["critical_path_phases"][0]["phase"], 1)
        self.assertIn("Shutdown", res["critical_path_phases"][0]["name"])
        self.assertEqual(res["critical_path_phases"][-1]["phase"], 7)
        self.assertIn("Air Tightness", res["critical_path_phases"][-1]["name"])


if __name__ == "__main__":
    unittest.main()

