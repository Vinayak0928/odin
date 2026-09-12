"""
src/agent_tools/industrial_tools.py

Industrial Tool Adapters for MRPL Refinery Operations (SIH26117).
Provides tool execution classes for:
  - calc_vessel_thickness_api510
  - calc_pipe_thickness_api570
  - calc_pump_hydraulics
  - calc_heat_exchanger_duty
  - optimize_crude_blend
  - inspect_pid_drawing
  - verify_audit_log
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from core.audit_merkle import get_audit_log
from src.tools.industrial_calc import (
    calculate_vessel_thickness_api510,
    calculate_pipe_thickness_api570,
    calculate_pump_hydraulics,
    calculate_heat_exchanger_duty,
    optimize_crude_blend,
    plan_refinery_turnaround,
)
from src.tools.pid_inspector import (
    parse_pid_entities_from_text,
    audit_pid_safety_discrepancies,
    decompose_pid_tiles,
)

logger = logging.getLogger(__name__)


def _parse_params(content: str) -> Dict[str, Any]:
    """Parse JSON or key-value parameters from tool content block."""
    content = content.strip()
    if not content:
        return {}
    if content.startswith("{") and content.endswith("}"):
        try:
            return json.loads(content)
        except Exception:
            pass

    # Fallback to key=value lines
    res = {}
    for line in content.split("\n"):
        line = line.strip()
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            try:
                if "." in v:
                    res[k] = float(v)
                else:
                    res[k] = int(v)
            except ValueError:
                res[k] = v
    return res


class CalcVesselThicknessApi510Tool:
    """API 510 Pressure Vessel Minimum Thickness & Remaining Life Tool."""

    async def execute(self, content: str, ctx: dict) -> dict:
        params = _parse_params(content)
        owner = ctx.get("owner", "anonymous")
        try:
            res = calculate_vessel_thickness_api510(
                design_pressure_psi=params.get("design_pressure_psi", 300.0),
                inside_radius_in=params.get("inside_radius_in", 48.0),
                allowable_stress_psi=params.get("allowable_stress_psi", 20000.0),
                joint_efficiency=params.get("joint_efficiency", 0.85),
                actual_thickness_in=params.get("actual_thickness_in", 1.25),
                corrosion_rate_mpy=params.get("corrosion_rate_mpy", 10.0),
                vessel_tag=params.get("vessel_tag", "V-101"),
            )
            # Record in cryptographic audit chain
            get_audit_log().record_event(
                user=owner,
                department="MECHANICAL_INTEGRITY_NDT",
                action="CALC_API510_VESSEL_THICKNESS",
                details={"vessel_tag": res["vessel_tag"], "status": res["status"], "remaining_life": res["remaining_life_years"]},
            )
            return {"output": json.dumps(res, indent=2), "result": res}
        except Exception as e:
            return {"error": f"API 510 calculation failed: {str(e)}", "exit_code": 1}


class CalcPipeThicknessApi570Tool:
    """API 570 Process Piping Thickness Tool."""

    async def execute(self, content: str, ctx: dict) -> dict:
        params = _parse_params(content)
        owner = ctx.get("owner", "anonymous")
        try:
            res = calculate_pipe_thickness_api570(
                design_pressure_psi=params.get("design_pressure_psi", 250.0),
                outside_diameter_in=params.get("outside_diameter_in", 8.625),
                allowable_stress_psi=params.get("allowable_stress_psi", 16000.0),
                joint_efficiency=params.get("joint_efficiency", 1.0),
                actual_thickness_in=params.get("actual_thickness_in", 0.322),
                corrosion_rate_mpy=params.get("corrosion_rate_mpy", 8.0),
                pipe_class=params.get("pipe_class", "Class 1"),
                pipe_tag=params.get("pipe_tag", "8-HC-101-A1A"),
            )
            get_audit_log().record_event(
                user=owner,
                department="MECHANICAL_INTEGRITY_NDT",
                action="CALC_API570_PIPE_THICKNESS",
                details={"pipe_tag": res["pipe_tag"], "status": res["status"], "remaining_life": res["remaining_life_years"]},
            )
            return {"output": json.dumps(res, indent=2), "result": res}
        except Exception as e:
            return {"error": f"API 570 calculation failed: {str(e)}", "exit_code": 1}


class CalcPumpHydraulicsTool:
    """Refinery Pump Hydraulics & NPSH Cavitation Check Tool."""

    async def execute(self, content: str, ctx: dict) -> dict:
        params = _parse_params(content)
        owner = ctx.get("owner", "anonymous")
        try:
            res = calculate_pump_hydraulics(
                flow_rate_gpm=params.get("flow_rate_gpm", 500.0),
                pipe_diameter_in=params.get("pipe_diameter_in", 6.0),
                pipe_length_ft=params.get("pipe_length_ft", 150.0),
                fluid_viscosity_cp=params.get("fluid_viscosity_cp", 1.2),
                fluid_density_lb_cuft=params.get("fluid_density_lb_cuft", 55.0),
                suction_static_head_ft=params.get("suction_static_head_ft", 15.0),
                vapor_pressure_psia=params.get("vapor_pressure_psia", 4.5),
                pump_npsh_required_ft=params.get("pump_npsh_required_ft", 9.0),
                pump_tag=params.get("pump_tag", "P-102A"),
            )
            get_audit_log().record_event(
                user=owner,
                department="PROCESS_ENGINEERING",
                action="CALC_PUMP_HYDRAULICS",
                details={"pump_tag": res["pump_tag"], "cavitation_status": res["cavitation_status"]},
            )
            return {"output": json.dumps(res, indent=2), "result": res}
        except Exception as e:
            return {"error": f"Pump hydraulics calculation failed: {str(e)}", "exit_code": 1}


class CalcHeatExchangerDutyTool:
    """Shell & Tube Heat Exchanger Duty & LMTD Tool."""

    async def execute(self, content: str, ctx: dict) -> dict:
        params = _parse_params(content)
        owner = ctx.get("owner", "anonymous")
        try:
            res = calculate_heat_exchanger_duty(
                hot_inlet_temp_c=params.get("hot_inlet_temp_c", 180.0),
                hot_outlet_temp_c=params.get("hot_outlet_temp_c", 110.0),
                cold_inlet_temp_c=params.get("cold_inlet_temp_c", 35.0),
                cold_outlet_temp_c=params.get("cold_outlet_temp_c", 85.0),
                hot_mass_flow_kg_s=params.get("hot_mass_flow_kg_s", 25.0),
                hot_specific_heat_kj_kg_c=params.get("hot_specific_heat_kj_kg_c", 2.4),
                overall_u_w_m2_c=params.get("overall_u_w_m2_c", 450.0),
                exchanger_tag=params.get("exchanger_tag", "E-101"),
            )
            get_audit_log().record_event(
                user=owner,
                department="PROCESS_ENGINEERING",
                action="CALC_HEAT_EXCHANGER_DUTY",
                details={"exchanger_tag": res["exchanger_tag"], "duty_kw": res["thermal_duty_kw"]},
            )
            return {"output": json.dumps(res, indent=2), "result": res}
        except Exception as e:
            return {"error": f"Heat exchanger calculation failed: {str(e)}", "exit_code": 1}


class OptimizeCrudeBlendTool:
    """Refinery Crude Assay Distillation Blend Optimizer Tool."""

    async def execute(self, content: str, ctx: dict) -> dict:
        params = _parse_params(content)
        owner = ctx.get("owner", "anonymous")
        try:
            candidates = params.get("crude_candidates", [
                {"name": "Arab Light", "sulfur_wt": 1.97, "api_gravity": 32.8},
                {"name": "Bonny Light", "sulfur_wt": 0.14, "api_gravity": 35.3},
                {"name": "Maya", "sulfur_wt": 3.40, "api_gravity": 21.8},
            ])
            res = optimize_crude_blend(
                crude_candidates=candidates,
                target_max_sulfur_wt=params.get("target_max_sulfur_wt", 1.8),
                target_min_api_gravity=params.get("target_min_api_gravity", 30.0),
                total_bpd=params.get("total_bpd", 120000.0),
            )
            get_audit_log().record_event(
                user=owner,
                department="PROCESS_ENGINEERING",
                action="OPTIMIZE_CRUDE_BLEND",
                details={"spec_compliant": res.get("spec_compliant")},
            )
            return {"output": json.dumps(res, indent=2), "result": res}
        except Exception as e:
            return {"error": f"Crude blend optimization failed: {str(e)}", "exit_code": 1}


class InspectPidDrawingTool:
    """P&ID Drawing Visual & Text Inspector Tool."""

    async def execute(self, content: str, ctx: dict) -> dict:
        params = _parse_params(content)
        owner = ctx.get("owner", "anonymous")
        drawing_text = params.get("drawing_text", "")
        image_path = params.get("image_path", "")

        try:
            tiles_info = []
            if image_path:
                try:
                    tiles = decompose_pid_tiles(image_path)
                    tiles_info = [{"tile": t["tile_index"], "coords": t["coordinates"]} for t in tiles[:8]]
                except Exception as ex:
                    logger.warning(f"Tile decomposition skipped: {ex}")

            entities = parse_pid_entities_from_text(drawing_text or content)
            discrepancies = audit_pid_safety_discrepancies(entities)

            result = {
                "entities": entities,
                "safety_discrepancies": discrepancies,
                "tiles_generated": len(tiles_info),
                "status": "INSPECTION_COMPLETE",
            }
            get_audit_log().record_event(
                user=owner,
                department="PROCESS_ENGINEERING",
                action="INSPECT_PID_DRAWING",
                details={"total_instruments": entities["summary"]["total_instruments"], "discrepancies": len(discrepancies)},
            )
            return {"output": json.dumps(result, indent=2), "result": result}
        except Exception as e:
            return {"error": f"P&ID inspection failed: {str(e)}", "exit_code": 1}


class VerifyAuditLogTool:
    """Verify cryptographic Merkle audit trail integrity."""

    async def execute(self, content: str, ctx: dict) -> dict:
        try:
            is_valid, issues = get_audit_log().verify_audit_chain()
            root_hash = get_audit_log().compute_merkle_root()
            res = {
                "audit_chain_valid": is_valid,
                "merkle_root_hash": root_hash,
                "discrepancies_detected": issues,
                "compliance_status": "CERTIFIED_TAMPER_EVIDENT" if is_valid else "TAMPERING_DETECTED",
            }
            return {"output": json.dumps(res, indent=2), "result": res}
        except Exception as e:
            return {"error": f"Audit verification failed: {str(e)}", "exit_code": 1}


class PlanRefineryTurnaroundTool:
    """Refinery Turnaround & Shutdown Work Package Planning Tool."""

    async def execute(self, content: str, ctx: dict) -> dict:
        params = _parse_params(content)
        owner = ctx.get("owner", "anonymous")
        unit_name = params.get("unit_name", "CDU-1")
        turnaround_type = params.get("turnaround_type", "MAJOR_REVAMP")
        duration = params.get("target_duration_days", 35)
        include_blind_list = params.get("include_blind_list", True)

        try:
            res = plan_refinery_turnaround(
                unit_name=unit_name,
                turnaround_type=turnaround_type,
                target_duration_days=int(duration),
                include_blind_list=bool(include_blind_list),
            )
            # Record in cryptographic audit DAG
            get_audit_log().record_event(
                user=owner,
                department="OPERATIONS_TAR",
                action="PLAN_REFINERY_TURNAROUND",
                details={
                    "unit_name": res["unit_name"],
                    "total_duration_days": res["total_duration_days"],
                    "blinds_count": res["blind_isolation_summary"]["total_blinds_required"],
                },
            )
            return {"output": json.dumps(res, indent=2), "result": res}
        except Exception as e:
            return {"error": f"Turnaround planning failed: {str(e)}", "exit_code": 1}


async def do_plan_refinery_turnaround(content: str, owner: str = "anonymous") -> str:
    tool = PlanRefineryTurnaroundTool()
    res = await tool.execute(content, {"owner": owner})
    return res.get("output") or res.get("error") or ""

