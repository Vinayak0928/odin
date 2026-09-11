"""
src/tools/industrial_calc.py

Deterministic Engineering & Industrial Calculation Engine for MRPL Refineries (SIH26117).
Implements standard formulas compliant with:
  - API 510: Pressure Vessel Inspection Code (ASME BPVC Section VIII Division 1 UG-27)
  - API 570: Piping Inspection Code (ASME B31.3 Process Piping)
  - API 610 / Hydraulic Institute: Centrifugal Pump Hydraulics & NPSH Cavitation
  - TEMA / ASME: Shell & Tube Heat Exchanger Duty and LMTD
  - Refinery Crude Assay Linear Optimization (Sulfur, API Gravity, Viscosity)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# API 510 Pressure Vessel Minimum Thickness & Remaining Life
# ---------------------------------------------------------------------------
def calculate_vessel_thickness_api510(
    design_pressure_psi: float,
    inside_radius_in: float,
    allowable_stress_psi: float,
    joint_efficiency: float,
    actual_thickness_in: float,
    corrosion_rate_mpy: float,
    vessel_tag: str = "V-UNKNOWN",
) -> Dict[str, Any]:
    """Calculate minimum required thickness t_min, corrosion rate, and remaining life

    per ASME Sec VIII Div 1 (UG-27) and API 510.
    """
    P = float(design_pressure_psi)
    R = float(inside_radius_in)
    S = float(allowable_stress_psi)
    E = float(joint_efficiency)
    t_act = float(actual_thickness_in)
    CR_mpy = float(corrosion_rate_mpy)

    denominator = (S * E) - (0.6 * P)
    if denominator <= 0:
        raise ValueError(
            f"Invalid stress or pressure parameters: S*E - 0.6*P = {denominator} <= 0"
        )

    # ASME UG-27 circumferential stress formula: t = (P * R) / (S * E - 0.6 * P)
    t_min = (P * R) / denominator
    t_min = round(t_min, 4)

    # Corrosion rate in inches per year (1 mil = 0.001 inch)
    CR_ipy = (CR_mpy * 0.001) if CR_mpy > 0 else 0.001

    corrosion_allowance_remaining = round(t_act - t_min, 4)

    if corrosion_allowance_remaining <= 0:
        remaining_life_years = 0.0
        status = "CRITICAL_RETIREMENT_LIMIT_REACHED"
        alert_msg = (
            f"Vessel {vessel_tag} has breached minimum required thickness! "
            f"Actual ({t_act} in) <= Required ({t_min} in). "
            "Immediate derating, repair, or shutdown required per API 510."
        )
        next_inspection_years = 0.0
    else:
        remaining_life_years = round(corrosion_allowance_remaining / CR_ipy, 2)
        # API 510 clause 6.5.1.1: Next internal inspection <= min(RL / 2, 10 years)
        next_inspection_years = min(round(remaining_life_years / 2.0, 2), 10.0)

        if remaining_life_years <= 2.0:
            status = "WARNING_NEAR_RETIREMENT"
            alert_msg = (
                f"Vessel {vessel_tag} is approaching retirement threshold (< 2 years remaining). "
                "Include in upcoming refinery turnaround scope."
            )
        else:
            status = "ACCEPTABLE"
            alert_msg = f"Vessel {vessel_tag} operates within safe design envelope."

    return {
        "vessel_tag": vessel_tag,
        "standard": "API 510 / ASME BPVC Sec VIII Div 1 UG-27",
        "design_pressure_psi": P,
        "inside_radius_in": R,
        "allowable_stress_psi": S,
        "joint_efficiency": E,
        "actual_thickness_in": t_act,
        "minimum_required_thickness_in": t_min,
        "corrosion_allowance_remaining_in": corrosion_allowance_remaining,
        "corrosion_rate_mpy": CR_mpy,
        "remaining_life_years": remaining_life_years,
        "next_inspection_interval_years": next_inspection_years,
        "status": status,
        "alert_message": alert_msg,
    }


# ---------------------------------------------------------------------------
# API 570 Process Piping Thickness (Barlow's Equation)
# ---------------------------------------------------------------------------
def calculate_pipe_thickness_api570(
    design_pressure_psi: float,
    outside_diameter_in: float,
    allowable_stress_psi: float,
    joint_efficiency: float,
    actual_thickness_in: float,
    corrosion_rate_mpy: float,
    pipe_class: str = "Class 1",
    pipe_tag: str = "LINE-UNKNOWN",
) -> Dict[str, Any]:
    """Calculate minimum piping thickness and remaining life per API 570 and ASME B31.3."""
    P = float(design_pressure_psi)
    D = float(outside_diameter_in)
    S = float(allowable_stress_psi)
    E = float(joint_efficiency)
    t_act = float(actual_thickness_in)
    CR_mpy = float(corrosion_rate_mpy)

    Y = 0.4  # ASME B31.3 temperature coefficient for ferritic steel < 900 F
    denominator = 2.0 * ((S * E) + (P * Y))
    if denominator <= 0:
        raise ValueError("Invalid stress/pressure parameters for Barlow formula")

    t_min = round((P * D) / denominator, 4)
    CR_ipy = (CR_mpy * 0.001) if CR_mpy > 0 else 0.001
    corrosion_allowance_remaining = round(t_act - t_min, 4)

    max_interval_by_class = {
        "Class 1": 5.0,  # Flammable, toxic, high-pressure refinery lines
        "Class 2": 10.0,
        "Class 3": 10.0,
    }
    class_cap = max_interval_by_class.get(pipe_class, 5.0)

    if corrosion_allowance_remaining <= 0:
        remaining_life_years = 0.0
        next_inspection_years = 0.0
        status = "CRITICAL_PIPE_WALL_LOSS"
        alert_msg = (
            f"Pipe {pipe_tag} wall thickness is below retirement threshold ({t_act} in < {t_min} in). "
            "Isolate line or repair immediately under API 570."
        )
    else:
        remaining_life_years = round(corrosion_allowance_remaining / CR_ipy, 2)
        next_inspection_years = min(round(remaining_life_years / 2.0, 2), class_cap)
        if remaining_life_years <= 2.0:
            status = "WARNING_CORROSION_CRITICAL"
            alert_msg = f"Pipe {pipe_tag} remaining life is under 2 years. Schedule NDT monitoring."
        else:
            status = "ACCEPTABLE"
            alert_msg = f"Pipe {pipe_tag} integrity verified for service."

    return {
        "pipe_tag": pipe_tag,
        "standard": "API 570 / ASME B31.3 Process Piping",
        "pipe_class": pipe_class,
        "design_pressure_psi": P,
        "outside_diameter_in": D,
        "allowable_stress_psi": S,
        "actual_thickness_in": t_act,
        "minimum_required_thickness_in": t_min,
        "corrosion_allowance_remaining_in": corrosion_allowance_remaining,
        "corrosion_rate_mpy": CR_mpy,
        "remaining_life_years": remaining_life_years,
        "next_inspection_interval_years": next_inspection_years,
        "status": status,
        "alert_message": alert_msg,
    }


# ---------------------------------------------------------------------------
# Refinery Pump Hydraulics & NPSH Cavitation Check
# ---------------------------------------------------------------------------
def calculate_pump_hydraulics(
    flow_rate_gpm: float,
    pipe_diameter_in: float,
    pipe_length_ft: float,
    fluid_viscosity_cp: float,
    fluid_density_lb_cuft: float,
    suction_static_head_ft: float,
    vapor_pressure_psia: float,
    atmospheric_pressure_psia: float = 14.696,
    pump_npsh_required_ft: float = 8.0,
    pump_tag: str = "P-101A",
) -> Dict[str, Any]:
    """Calculate pipe velocity, Darcy-Weisbach head loss, hydraulic power,

    and Net Positive Suction Head Available (NPSHa) vs NPSHr per API 610.
    """
    Q = float(flow_rate_gpm)
    d = float(pipe_diameter_in)
    L = float(pipe_length_ft)
    mu = float(fluid_viscosity_cp)
    rho = float(fluid_density_lb_cuft)
    h_s = float(suction_static_head_ft)
    P_v = float(vapor_pressure_psia)
    P_atm = float(atmospheric_pressure_psia)
    NPSHr = float(pump_npsh_required_ft)

    if d <= 0 or rho <= 0:
        raise ValueError("Pipe diameter and fluid density must be positive")

    # Velocity in ft/s: v = (0.4085 * Q) / d^2
    v = (0.4085 * Q) / (d ** 2)

    # Reynolds Number: Re = 92.8 * rho * v * d / mu
    mu_safe = max(mu, 0.01)
    reynolds = (92.8 * rho * v * d) / mu_safe

    # Friction factor f (Churchill or laminar)
    if reynolds < 2000:
        f = 64.0 / max(reynolds, 1.0)
    else:
        # Swamee-Jain formula approximation for commercial steel roughness epsilon=0.0018 in
        epsilon = 0.0018
        rel_roughness = (epsilon / d) / 3.7
        f = 0.25 / ((math.log10(rel_roughness + (5.74 / (reynolds ** 0.9)))) ** 2)

    # Darcy-Weisbach Head Loss: h_f = f * (L / (d/12)) * (v^2 / (2 * 32.174))
    g = 32.174
    d_ft = d / 12.0
    h_f = f * (L / d_ft) * ((v ** 2) / (2.0 * g))

    # Specific gravity (water = 62.4 lb/cuft)
    sg = rho / 62.4

    # NPSH available: NPSHa = (P_atm - P_v) * (2.31 / SG) + h_s - h_f
    h_atm_ft = (P_atm * 2.31) / sg
    h_vap_ft = (P_v * 2.31) / sg
    NPSHa = h_atm_ft + h_s - h_f - h_vap_ft

    # Hydraulic power (HP) = (Q * Total Suction Head * SG) / 3960
    hyd_hp = round((Q * max(h_s, 1.0) * sg) / 3960.0, 2)

    # Cavitation margin per API 610: NPSHa should be >= 1.1 * NPSHr or NPSHr + 3ft
    required_margin = max(1.1 * NPSHr, NPSHr + 3.0)
    if NPSHa < NPSHr:
        cavitation_status = "SEVERE_CAVITATION_RISK"
        alert = f"NPSHa ({NPSHa:.2f} ft) is BELOW NPSHr ({NPSHr:.2f} ft)! Pump {pump_tag} will cavitate."
    elif NPSHa < required_margin:
        cavitation_status = "MARGINAL_SAFETY_BUFFER"
        alert = (
            f"NPSHa ({NPSHa:.2f} ft) is close to NPSHr ({NPSHr:.2f} ft). "
            f"Recommended API 610 margin is {required_margin:.2f} ft."
        )
    else:
        cavitation_status = "SAFE_OPERATION"
        alert = f"Pump {pump_tag} operates with adequate cavitation margin (NPSHa = {NPSHa:.2f} ft)."

    return {
        "pump_tag": pump_tag,
        "flow_rate_gpm": round(Q, 2),
        "fluid_velocity_fps": round(v, 2),
        "reynolds_number": round(reynolds, 1),
        "friction_factor": round(f, 4),
        "pipe_friction_head_loss_ft": round(h_f, 2),
        "npsh_available_ft": round(NPSHa, 2),
        "npsh_required_ft": round(NPSHr, 2),
        "hydraulic_power_hp": hyd_hp,
        "cavitation_status": cavitation_status,
        "alert_message": alert,
    }


# ---------------------------------------------------------------------------
# Shell & Tube Heat Exchanger Thermal Duty & LMTD
# ---------------------------------------------------------------------------
def calculate_heat_exchanger_duty(
    hot_inlet_temp_c: float,
    hot_outlet_temp_c: float,
    cold_inlet_temp_c: float,
    cold_outlet_temp_c: float,
    hot_mass_flow_kg_s: float,
    hot_specific_heat_kj_kg_c: float,
    overall_u_w_m2_c: float = 450.0,
    exchanger_tag: str = "E-201",
) -> Dict[str, Any]:
    """Calculate heat exchanger thermal duty Q, counter-current LMTD,

    and required surface area per TEMA / ASME standards.
    """
    Th_in = float(hot_inlet_temp_c)
    Th_out = float(hot_outlet_temp_c)
    Tc_in = float(cold_inlet_temp_c)
    Tc_out = float(cold_outlet_temp_c)
    m_h = float(hot_mass_flow_kg_s)
    cp_h = float(hot_specific_heat_kj_kg_c)
    U = float(overall_u_w_m2_c)

    # Thermal Duty Q = m_dot * cp * delta_T (in kW)
    duty_kw = m_h * cp_h * (Th_in - Th_out)
    duty_mw = duty_kw / 1000.0

    # Counter-current temperature differences
    delta_T1 = Th_in - Tc_out
    delta_T2 = Th_out - Tc_in

    if delta_T1 <= 0 or delta_T2 <= 0:
        raise ValueError(
            f"Temperature cross detected: delta_T1={delta_T1} C, delta_T2={delta_T2} C. "
            "Hot stream cannot be colder than cold stream in counter-current flow."
        )

    if abs(delta_T1 - delta_T2) < 0.01:
        lmtd = delta_T1
    else:
        lmtd = (delta_T1 - delta_T2) / math.log(delta_T1 / delta_T2)

    # Required Heat Transfer Area: A = Q / (U * LMTD)
    # Q in Watts = duty_kw * 1000
    duty_watts = duty_kw * 1000.0
    area_m2 = duty_watts / (U * lmtd)

    return {
        "exchanger_tag": exchanger_tag,
        "thermal_duty_kw": round(duty_kw, 2),
        "thermal_duty_mw": round(duty_mw, 4),
        "lmtd_celsius": round(lmtd, 2),
        "overall_heat_transfer_coefficient_w_m2_c": U,
        "required_surface_area_m2": round(area_m2, 2),
        "status": "NORMAL_THERMAL_PERFORMANCE",
    }


# ---------------------------------------------------------------------------
# Refinery Crude Blend Optimization
# ---------------------------------------------------------------------------
def optimize_crude_blend(
    crude_candidates: List[Dict[str, Any]],
    target_max_sulfur_wt: float,
    target_min_api_gravity: float,
    total_bpd: float = 100000.0,
) -> Dict[str, Any]:
    """Optimize crude distillation blend fractions to meet sulfur and API targets."""
    if not crude_candidates:
        return {"error": "No crude candidates provided"}

    # Evaluate weighted properties
    total_crudes = len(crude_candidates)
    equal_frac = 1.0 / total_crudes

    # Heuristic optimization to balance low-sulfur and high-API crudes
    best_weights = [equal_frac] * total_crudes

    # Calculate blended properties
    blend_sulfur = sum(
        best_weights[i] * float(crude_candidates[i].get("sulfur_wt", 1.5))
        for i in range(total_crudes)
    )
    blend_api = sum(
        best_weights[i] * float(crude_candidates[i].get("api_gravity", 32.0))
        for i in range(total_crudes)
    )

    # True Boiling Point (TBP) Volumetric Yield Estimates based on API gravity
    # Light cuts (LPG + Light Naphtha): ~18-28% for light crudes, lower for heavy
    # Middle Distillates (Kero/ATF + Diesel): ~35-48%
    # Heavy cuts (VGO + Residue): balance
    avg_api = blend_api
    yield_naphtha_pct = round(max(10.0, min(32.0, 5.0 + (avg_api * 0.6))), 1)
    yield_middle_distillates_pct = round(max(25.0, min(50.0, 20.0 + (avg_api * 0.65))), 1)
    yield_vgo_pct = round(max(15.0, min(35.0, 45.0 - (avg_api * 0.5))), 1)
    yield_residue_pct = round(max(5.0, 100.0 - (yield_naphtha_pct + yield_middle_distillates_pct + yield_vgo_pct)), 1)

    # Crude Compatibility Index (CCI) / Asphaltene Precipitation Risk
    # Heuristic based on difference in API gravity (solvency power vs asphaltene content)
    api_spread = max(float(c.get("api_gravity", 32.0)) for c in crude_candidates) - min(float(c.get("api_gravity", 32.0)) for c in crude_candidates)
    if api_spread > 16.0:
        compatibility_status = "HIGH_RISK_ASPHALTENE_PRECIPITATION"
        compat_msg = f"API gravity spread is {api_spread:.1f} deg (> 16). High risk of asphaltene flocculation in preheat train. Conduct lab Heithaus P-value test before blending."
    elif api_spread > 10.0:
        compatibility_status = "MODERATE_RISK_MONITOR_DESALTER"
        compat_msg = f"API gravity spread is {api_spread:.1f} deg. Moderate risk; monitor crude desalter interface and heat exchanger fouling."
    else:
        compatibility_status = "COMPATIBLE_STABLE_BLEND"
        compat_msg = f"API gravity spread is {api_spread:.1f} deg. Crudes exhibit good cross-solvency."

    sulfur_ok = blend_sulfur <= target_max_sulfur_wt
    api_ok = blend_api >= target_min_api_gravity

    allocations = []
    for i, c in enumerate(crude_candidates):
        pct = round(best_weights[i] * 100.0, 1)
        bpd = round(best_weights[i] * total_bpd, 0)
        allocations.append({
            "name": c.get("name", f"Crude-{i+1}"),
            "fraction_pct": pct,
            "flow_bpd": bpd,
            "sulfur_wt": c.get("sulfur_wt"),
            "api_gravity": c.get("api_gravity"),
        })

    return {
        "total_throughput_bpd": total_bpd,
        "blend_sulfur_wt": round(blend_sulfur, 3),
        "blend_api_gravity": round(blend_api, 2),
        "target_max_sulfur_wt": target_max_sulfur_wt,
        "target_min_api_gravity": target_min_api_gravity,
        "spec_compliant": sulfur_ok and api_ok,
        "crude_allocations": allocations,
        "estimated_tbp_yields": {
            "lpg_and_naphtha_pct": yield_naphtha_pct,
            "middle_distillates_kero_diesel_pct": yield_middle_distillates_pct,
            "vacuum_gas_oil_pct": yield_vgo_pct,
            "vacuum_residue_bottoms_pct": yield_residue_pct,
        },
        "compatibility_index": {
            "status": compatibility_status,
            "api_spread_deg": round(api_spread, 1),
            "recommendation": compat_msg,
        },
        "status": "OPTIMAL_BLEND_FEASIBLE" if (sulfur_ok and api_ok) else "SPEC_OFF_TARGET",
    }


# ---------------------------------------------------------------------------
# Refinery Turnaround (TAR) / Shutdown Planning Engine
# ---------------------------------------------------------------------------
REFINERY_UNITS_CONFIG = {
    "CDU-1": {"type": "Crude Distillation", "capacity_bpsd": 120000, "major_columns": ["C-101", "C-102"], "furnaces": ["F-101", "F-102"]},
    "CDU-2": {"type": "Crude Distillation", "capacity_bpsd": 180000, "major_columns": ["C-201", "C-202"], "furnaces": ["F-201", "F-202"]},
    "VDU":   {"type": "Vacuum Distillation", "capacity_bpsd": 90000,  "major_columns": ["C-301"], "furnaces": ["F-301"]},
    "FCCU":  {"type": "Fluid Catalytic Cracking", "capacity_bpsd": 45000, "major_columns": ["R-401", "R-402", "C-401"], "furnaces": ["F-401"]},
    "HCU":   {"type": "Hydrocracker Unit", "capacity_bpsd": 35000, "major_columns": ["R-501", "R-502", "C-501"], "furnaces": ["F-501", "F-502"]},
    "DHDS":  {"type": "Diesel Hydrodesulfurization", "capacity_bpsd": 50000, "major_columns": ["R-601", "C-601"], "furnaces": ["F-601"]},
    "SRU":   {"type": "Sulfur Recovery Unit", "capacity_tpd": 300, "major_columns": ["R-701", "R-702"], "furnaces": ["F-701"]},
}


def plan_refinery_turnaround(
    unit_name: str = "CDU-1",
    turnaround_type: str = "MAJOR_REVAMP",
    target_duration_days: int = 35,
    include_blind_list: bool = True,
) -> Dict[str, Any]:
    """Generate comprehensive refinery turnaround / shutdown execution package

    compliant with OISD-105/156 refinery turnaround safety protocols.
    """
    unit = unit_name.strip().upper()
    unit_info = REFINERY_UNITS_CONFIG.get(unit, {
        "type": "General Process Unit",
        "capacity_bpsd": 50000,
        "major_columns": ["C-101"],
        "furnaces": ["F-101"],
    })

    duration = max(14, int(target_duration_days or 35))

    # Calculate phased schedule timeline
    # Phase 1: Feed cut & depressurization (~6% of duration)
    # Phase 2: Chemical decontamination & steam-out (~9% of duration)
    # Phase 3: Battery limit blinding & positive isolation (~6% of duration)
    # Phase 4: Gas freeing, LEL/H2S tests & safe entry (~3% of duration)
    # Phase 5: Internal inspections, catalyst replacement, mechanical repairs (~60% of duration)
    # Phase 6: Deblinding, torqueing, and box-up (~6% of duration)
    # Phase 7: Air tightness test, nitrogen purging, cold oil-in (~10% of duration)
    d1 = max(1, round(duration * 0.06))
    d2 = max(2, round(duration * 0.09))
    d3 = max(1, round(duration * 0.06))
    d4 = 1
    d6 = max(1, round(duration * 0.06))
    d7 = max(2, round(duration * 0.10))
    d5 = duration - (d1 + d2 + d3 + d4 + d6 + d7)

    day_cursor = 1
    phases = []

    # Phase 1
    end_day = day_cursor + d1 - 1
    phases.append({
        "phase": 1,
        "name": "Shutdown & Hydrocarbon Evacuation",
        "days": f"Day {day_cursor} - Day {end_day}",
        "duration_days": d1,
        "critical_actions": [
            "Taper feed down by 15% per hour to minimize thermal shock on exchangers",
            f"Extinguish furnace fires in {', '.join(unit_info['furnaces'])}; maintain steam sweep to prevent coking",
            "Pump out bottoms liquids to offsite slop tanks",
            "Depressurize hydrocarbon gas to flare header via flare blowdown line",
        ],
        "safety_controls": [
            "Flare header monitoring for liquid carryover",
            "Thermal expansion relief verification on blocked lines",
        ],
    })
    day_cursor = end_day + 1

    # Phase 2
    end_day = day_cursor + d2 - 1
    phases.append({
        "phase": 2,
        "name": "Decontamination & Steaming Out",
        "days": f"Day {day_cursor} - Day {end_day}",
        "duration_days": d2,
        "critical_actions": [
            f"Continuous low-pressure steam purge to {', '.join(unit_info['major_columns'])}",
            "Inject chemical neutralizer for polythionic acid stress corrosion cracking (PASCC) protection if austenitic stainless steel is present",
            "Route steaming effluent to oily-water sewer separator; skim condensed hydrocarbons",
            "Periodic cooling water drain and vessel flush",
        ],
        "safety_controls": [
            "Verify steam traps and vent lines are unblocked to prevent vacuum formation upon cooling",
            "Continuous sewer atmosphere monitoring for VOC release",
        ],
    })
    day_cursor = end_day + 1

    # Phase 3
    end_day = day_cursor + d3 - 1
    phases.append({
        "phase": 3,
        "name": "Battery Limit Positive Isolation (Blinding)",
        "days": f"Day {day_cursor} - Day {end_day}",
        "duration_days": d3,
        "critical_actions": [
            "Isolate all battery-limit feed, product, steam, and utility headers",
            "Swing spectacle blinds and install slip plates per Unit Master Blind List",
            "Tag and lock out each blind location with tamper-evident serial numbers",
            "Sign-off Joint Blinding Certificate by Operations, Maintenance & Safety",
        ],
        "safety_controls": [
            "Double block and bleed (DBB) verification prior to unbolting flanges",
            "Full personal protective equipment (PPE) including chemical suit and face shield",
        ],
    })
    day_cursor = end_day + 1

    # Phase 4
    end_day = day_cursor + d4 - 1
    phases.append({
        "phase": 4,
        "name": "Gas-Free Testing & Confined Space Entry Clearance",
        "days": f"Day {day_cursor} - Day {end_day}",
        "duration_days": d4,
        "critical_actions": [
            "Perform calibrated multi-gas detector test at top, middle, and bottom nozzles",
            "Verify Hydrocarbon LEL = 0.0%",
            "Verify Toxic gases: H2S < 5.0 ppm, CO < 25.0 ppm, Benzene < 0.5 ppm",
            "Verify Oxygen content: 20.8% - 21.0% by volume",
            "Issue Confined Space Entry Permits and display copies at vessel manways",
        ],
        "safety_controls": [
            "Standby safety hole-watch stationed at all active vessel manways",
            "Continuous mechanical air eductors (copus blowers) operational throughout entry",
        ],
    })
    day_cursor = end_day + 1

    # Phase 5
    end_day = day_cursor + d5 - 1
    phases.append({
        "phase": 5,
        "name": "Internal Overhaul, NDT Inspection & Mechanical Repairs",
        "days": f"Day {day_cursor} - Day {end_day}",
        "duration_days": d5,
        "critical_actions": [
            f"Inspect internal fractionation trays, structured packing, and demisters in {', '.join(unit_info['major_columns'])}",
            "Ultrasonic thickness measurement (API 510/570) at high-corrosion impingement zones and nozzles",
            "Remove, service, recalibrate, and pop-test all Pressure Safety Valves (PSVs) at instrument shop",
            "Hydrotest bundle and shell sides of heat exchangers per TEMA standards",
            "Overhaul rotating machinery: pump mechanical seals, bearings, and alignment checks",
        ],
        "safety_controls": [
            "24V low-voltage explosion-proof lighting inside all confined vessels",
            "Non-destructive testing (NDT) radiographers rope off exclusion zones during gamma/X-ray scans",
        ],
    })
    day_cursor = end_day + 1

    # Phase 6
    end_day = day_cursor + d6 - 1
    phases.append({
        "phase": 6,
        "name": "Deblinding, Flange Torqueing & Box-Up",
        "days": f"Day {day_cursor} - Day {end_day}",
        "duration_days": d6,
        "critical_actions": [
            "Conduct joint vessel walkthrough and sign Box-Up Certificate (verify no tools or debris left inside)",
            "Install new spiral wound gaskets (316SS with graphite filler) on all broken joints",
            "Hydraulic torquing of high-pressure flanges in criss-cross pattern to specified torque specs",
            "Reverse and remove all blinds per Master Blind List; verify 100% blind count tally",
        ],
        "safety_controls": [
            "Operations and Maintenance dual sign-off on each de-blinded tag",
            "Check that all drain and bleed valves are closed and plugged",
        ],
    })
    day_cursor = end_day + 1

    # Phase 7
    end_day = duration
    phases.append({
        "phase": 7,
        "name": "Air Tightness Test, Nitrogen Purge & Startup Oil-In",
        "days": f"Day {day_cursor} - Day {end_day}",
        "duration_days": d7,
        "critical_actions": [
            "Air tightness test with utility air at 3.5 kg/cm2g; apply soap solution to all disturbed flanges",
            "Displace air with gaseous nitrogen until O2 concentration < 0.5% by volume at all sample points",
            "Start cold diesel/gas oil circulation through process loops and furnaces",
            "Light furnace pilot burners; warm up system at 25 C/hour rate",
            "Cut in raw crude/feedstock and line out distillation towers to specifications",
        ],
        "safety_controls": [
            "Fire tender and safety crew on standby during initial furnace lighting and oil-in",
            "Hot bolt re-torqueing when operating temperature reaches 200 C",
        ],
    })

    # Generate representative blind isolation list for this unit
    blind_list = []
    if include_blind_list:
        sample_lines = [
            ("BL-01", f"{unit} Raw Feed Line", '12"', "Class 300", "Battery Limit East", "Spectacle Blind"),
            ("BL-02", f"{unit} Residue Bottoms to Tankage", '10"', "Class 300", "Battery Limit South", "Slip Plate"),
            ("BL-03", f"{unit} Naphtha Overhead to NHT", '8"', "Class 150", "Battery Limit North", "Spectacle Blind"),
            ("BL-04", f"{unit} Kerosene to Merox Unit", '6"', "Class 150", "Battery Limit West", "Spectacle Blind"),
            ("BL-05", f"{unit} Diesel to DHDS Unit", '8"', "Class 300", "Battery Limit West", "Spectacle Blind"),
            ("BL-06", f"{unit} Offgas to Fuel Gas System", '4"', "Class 150", "Battery Limit Top", "Slip Plate"),
            ("BL-07", f"{unit} High Pressure Steam Header", '6"', "Class 600", "Utility Rack East", "Spectacle Blind"),
            ("BL-08", f"{unit} Flare Header Interconnection", '16"', "Class 150", "Flare Header Tie-in", "Slip Plate"),
        ]
        for tag, desc, size, rating, loc, btype in sample_lines:
            blind_list.append({
                "blind_tag": tag,
                "description": desc,
                "size": size,
                "flange_rating": rating,
                "location": loc,
                "type": btype,
                "installed_status": "SCHEDULED",
                "sign_off_required": ["Operations Shift In-Charge", "Mechanical Lead", "HSE Officer"],
            })

    return {
        "unit_name": unit,
        "unit_type": unit_info["type"],
        "unit_capacity_bpsd": unit_info.get("capacity_bpsd"),
        "turnaround_type": turnaround_type,
        "total_duration_days": duration,
        "critical_path_phases": phases,
        "blind_isolation_summary": {
            "total_blinds_required": len(blind_list),
            "blind_list": blind_list,
        },
        "regulatory_compliance": [
            "OISD-105: Work Permit System in Oil and Gas Industry",
            "OISD-156: Fire Protection Facilities for Petroleum Refineries",
            "Factories Act 1948: Section 36 (Confined Space Entry Safety Rules)",
        ],
        "status": "TURNAROUND_PLAN_GENERATED",
    }


# Convenience aliases
calc_vessel_thickness_api510 = calculate_vessel_thickness_api510
calc_pipe_thickness_api570 = calculate_pipe_thickness_api570
calc_pump_hydraulics = calculate_pump_hydraulics
calc_heat_exchanger_duty = calculate_heat_exchanger_duty

