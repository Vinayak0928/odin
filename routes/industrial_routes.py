"""
routes/industrial_routes.py

REST API endpoints for MRPL Refinery Industrial Engineering & P&ID Intelligence (SIH26117).
Provides direct access to API 510/570 calculations, pump hydraulics, heat exchangers,
crude assay distillation optimizer, turnaround planning, and P&ID inspection.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

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
)
from core.audit_merkle import get_audit_log

logger = logging.getLogger(__name__)


class API510Request(BaseModel):
    design_pressure_psi: float
    inside_radius_in: float
    allowable_stress_psi: float
    joint_efficiency: float = 1.0
    actual_thickness_in: float = 0.5
    corrosion_rate_mpy: float = 5.0
    vessel_tag: str = "V-101"


class API570Request(BaseModel):
    design_pressure_psi: float
    outside_diameter_in: float
    allowable_stress_psi: float
    joint_efficiency: float = 1.0
    actual_thickness_in: float = 0.375
    corrosion_rate_mpy: float = 6.0
    pipe_class: str = "Class 1"
    pipe_tag: str = "LINE-P-201"


class PumpHydraulicsRequest(BaseModel):
    flow_rate_gpm: float
    pipe_diameter_in: float
    pipe_length_ft: float
    fluid_viscosity_cp: float = 1.0
    fluid_density_lb_cuft: float = 54.0
    suction_static_head_ft: float = 10.0
    vapor_pressure_psia: float = 2.5
    atmospheric_pressure_psia: float = 14.696
    pump_npsh_required_ft: float = 8.0
    pump_tag: str = "P-101A"


class HeatExchangerRequest(BaseModel):
    hot_inlet_temp_c: float
    hot_outlet_temp_c: float
    cold_inlet_temp_c: float
    cold_outlet_temp_c: float
    hot_mass_flow_kg_s: float
    hot_specific_heat_kj_kg_c: float
    overall_u_w_m2_c: float = 450.0
    exchanger_tag: str = "E-201"


class CrudeBlendRequest(BaseModel):
    crude_feedstocks: List[Dict[str, Any]]
    target_api: Optional[float] = None
    max_sulfur_wt_pct: Optional[float] = None
    total_feed_kbd: float = 100.0


class TurnaroundRequest(BaseModel):
    unit_name: str
    turnaround_type: str = "MAJOR_REVAMP"
    planned_duration_days: Optional[int] = 21
    critical_path_equipments: Optional[List[str]] = None


class PIDParseRequest(BaseModel):
    drawing_text: str
    drawing_id: Optional[str] = "P&ID-MRPL-VDU-101"


def setup_industrial_routes() -> APIRouter:
    router = APIRouter(prefix="/api/industrial", tags=["industrial"])

    @router.get("/status")
    async def industrial_status() -> Dict[str, Any]:
        """Status of ODIN air-gapped industrial calculations engine."""
        return {
            "sovereign_workbench": "ODIN (SIH26117)",
            "airgap_enforced": True,
            "egress_status": "0-WAN_VERIFIED_INTERNAL",
            "modules": [
                "API-510 Vessel Integrity",
                "API-570 Piping Retirement",
                "API-610 Pump Hydraulics & Cavitation",
                "TEMA Heat Exchanger Rating",
                "Crude Assay & Distillation Yield Optimization",
                "OISD-105 Refinery Turnaround Shutdown Planner",
                "ISA-5.1 P&ID Drawing Discrepancy Inspector",
                "Merkle DAG Tamper-Evident Audit Trail",
            ],
        }

    @router.post("/calc/api510")
    async def run_api510(req: API510Request) -> Dict[str, Any]:
        try:
            res = calculate_vessel_thickness_api510(
                design_pressure_psi=req.design_pressure_psi,
                inside_radius_in=req.inside_radius_in,
                allowable_stress_psi=req.allowable_stress_psi,
                joint_efficiency=req.joint_efficiency,
                actual_thickness_in=req.actual_thickness_in,
                corrosion_rate_mpy=req.corrosion_rate_mpy,
                vessel_tag=req.vessel_tag,
            )
            get_audit_log().record_action(
                action="CALC_VESSEL_THICKNESS_API510",
                user="industrial_api",
                department="RELIABILITY_INSPECTION",
                details={"vessel_tag": req.vessel_tag, "status": res.get("status")},
            )
            return res
        except Exception as e:
            logger.error(f"Error in API510 calculation: {e}")
            raise HTTPException(400, str(e))

    @router.post("/calc/api570")
    async def run_api570(req: API570Request) -> Dict[str, Any]:
        try:
            res = calculate_pipe_thickness_api570(
                design_pressure_psi=req.design_pressure_psi,
                outside_diameter_in=req.outside_diameter_in,
                allowable_stress_psi=req.allowable_stress_psi,
                joint_efficiency=req.joint_efficiency,
                actual_thickness_in=req.actual_thickness_in,
                corrosion_rate_mpy=req.corrosion_rate_mpy,
                pipe_class=req.pipe_class,
                pipe_tag=req.pipe_tag,
            )
            get_audit_log().record_action(
                action="CALC_PIPE_THICKNESS_API570",
                user="industrial_api",
                department="RELIABILITY_INSPECTION",
                details={"pipe_tag": req.pipe_tag, "status": res.get("status")},
            )
            return res
        except Exception as e:
            logger.error(f"Error in API570 calculation: {e}")
            raise HTTPException(400, str(e))

    @router.post("/calc/pump")
    async def run_pump(req: PumpHydraulicsRequest) -> Dict[str, Any]:
        try:
            res = calculate_pump_hydraulics(
                flow_rate_gpm=req.flow_rate_gpm,
                pipe_diameter_in=req.pipe_diameter_in,
                pipe_length_ft=req.pipe_length_ft,
                fluid_viscosity_cp=req.fluid_viscosity_cp,
                fluid_density_lb_cuft=req.fluid_density_lb_cuft,
                suction_static_head_ft=req.suction_static_head_ft,
                vapor_pressure_psia=req.vapor_pressure_psia,
                atmospheric_pressure_psia=req.atmospheric_pressure_psia,
                pump_npsh_required_ft=req.pump_npsh_required_ft,
                pump_tag=req.pump_tag,
            )
            return res
        except Exception as e:
            logger.error(f"Error in pump calculation: {e}")
            raise HTTPException(400, str(e))

    @router.post("/calc/heat_exchanger")
    async def run_heat_exchanger(req: HeatExchangerRequest) -> Dict[str, Any]:
        try:
            res = calculate_heat_exchanger_duty(
                hot_inlet_temp_c=req.hot_inlet_temp_c,
                hot_outlet_temp_c=req.hot_outlet_temp_c,
                cold_inlet_temp_c=req.cold_inlet_temp_c,
                cold_outlet_temp_c=req.cold_outlet_temp_c,
                hot_mass_flow_kg_s=req.hot_mass_flow_kg_s,
                hot_specific_heat_kj_kg_c=req.hot_specific_heat_kj_kg_c,
                overall_u_w_m2_c=req.overall_u_w_m2_c,
                exchanger_tag=req.exchanger_tag,
            )
            return res
        except Exception as e:
            logger.error(f"Error in heat exchanger calculation: {e}")
            raise HTTPException(400, str(e))

    @router.post("/calc/crude_blend")
    async def run_crude_blend(req: CrudeBlendRequest) -> Dict[str, Any]:
        try:
            res = optimize_crude_blend(
                crude_feedstocks=req.crude_feedstocks,
                target_api=req.target_api,
                max_sulfur_wt_pct=req.max_sulfur_wt_pct,
                total_feed_kbd=req.total_feed_kbd,
            )
            get_audit_log().record_action(
                action="OPTIMIZE_CRUDE_BLEND",
                user="industrial_api",
                department="PROCESS_ENGINEERING",
                details={"target_api": req.target_api, "feed_kbd": req.total_feed_kbd},
            )
            return res
        except Exception as e:
            logger.error(f"Error in crude blend optimization: {e}")
            raise HTTPException(400, str(e))

    @router.post("/calc/turnaround")
    async def run_turnaround(req: TurnaroundRequest) -> Dict[str, Any]:
        try:
            res = plan_refinery_turnaround(
                unit_name=req.unit_name,
                turnaround_type=req.turnaround_type,
                planned_duration_days=req.planned_duration_days,
                critical_path_equipments=req.critical_path_equipments,
            )
            get_audit_log().record_action(
                action="PLAN_REFINERY_TURNAROUND",
                user="industrial_api",
                department="OPERATIONS_TAR",
                details={"unit_name": req.unit_name, "type": req.turnaround_type},
            )
            return res
        except Exception as e:
            logger.error(f"Error in turnaround planning: {e}")
            raise HTTPException(400, str(e))

    @router.post("/pid/parse_text")
    async def run_pid_parse(req: PIDParseRequest) -> Dict[str, Any]:
        try:
            entities = parse_pid_entities_from_text(req.drawing_text)
            discrepancies = audit_pid_safety_discrepancies(entities)
            get_audit_log().record_action(
                action="INSPECT_PID_DRAWING",
                user="industrial_api",
                department="HSE_SAFETY",
                details={
                    "drawing_id": req.drawing_id,
                    "discrepancies_count": len(discrepancies),
                },
            )
            return {
                "drawing_id": req.drawing_id,
                "entities": entities,
                "discrepancies": discrepancies,
                "audit_logged": True,
            }
        except Exception as e:
            logger.error(f"Error in P&ID parse: {e}")
            raise HTTPException(400, str(e))

    return router
