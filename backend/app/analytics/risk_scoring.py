from typing import Optional, Dict, Any, List
from backend.app.core.config import settings
from backend.app.schemas.analytics import RiskScoreItem


def calculate_risk_profile(
    displacement_mm: Optional[float],
    velocity_mm_hr: Optional[float],
    acceleration_mm_hr2: Optional[float],
    vector_tilt_deg: Optional[float],
    quality: Dict[str, Any],
    connectivity_status: str
) -> RiskScoreItem:
    """
    Calculate transparent, multi-factor geotechnical risk indicators.
    Separates physical deformation hazard from data quality / connectivity uncertainty.
    """
    active_indicators: List[str] = []

    # 1. Deformation Score (0 to 100)
    deformation_score = 0.0
    if displacement_mm is not None:
        abs_d = abs(displacement_mm)
        ratio = abs_d / settings.DISPLACEMENT_CRITICAL_MM
        deformation_score = min(100.0, round(ratio * 100.0, 1))
        if abs_d >= settings.DISPLACEMENT_CRITICAL_MM:
            active_indicators.append("CRITICAL_DISPLACEMENT")
        elif abs_d >= settings.DISPLACEMENT_WARNING_MM:
            active_indicators.append("WARNING_DISPLACEMENT")

    # 2. Rate & Acceleration Score (0 to 100)
    rate_score = 0.0
    if velocity_mm_hr is not None:
        abs_v = abs(velocity_mm_hr)
        v_ratio = abs_v / settings.RATE_CRITICAL_MM_HR
        rate_score = min(70.0, round(v_ratio * 70.0, 1))
        if abs_v >= settings.RATE_CRITICAL_MM_HR:
            active_indicators.append("CRITICAL_VELOCITY")
        elif abs_v >= settings.RATE_WARNING_MM_HR:
            active_indicators.append("WARNING_VELOCITY")

    if acceleration_mm_hr2 is not None and acceleration_mm_hr2 > 0:
        a_ratio = acceleration_mm_hr2 / settings.ACCEL_WARNING_MM_HR2
        accel_bonus = min(30.0, round(a_ratio * 30.0, 1))
        rate_score = min(100.0, rate_score + accel_bonus)
        if acceleration_mm_hr2 >= settings.ACCEL_WARNING_MM_HR2:
            active_indicators.append("CRITICAL_ACCELERATION")

    # 3. Tilt Score (0 to 100)
    tilt_score = 0.0
    if vector_tilt_deg is not None:
        tilt_ratio = vector_tilt_deg / settings.TILT_CRITICAL_DEG
        tilt_score = min(100.0, round(tilt_ratio * 100.0, 1))
        if vector_tilt_deg >= settings.TILT_CRITICAL_DEG:
            active_indicators.append("CRITICAL_TILT")
        elif vector_tilt_deg >= settings.TILT_WARNING_DEG:
            active_indicators.append("WARNING_TILT")

    # 4. Data Quality Score (0 to 100, where 100 = perfect fidelity, 0 = broken/missing)
    data_quality_score = 100.0
    if connectivity_status == "OFFLINE":
        data_quality_score = 10.0
        active_indicators.append("NODE_OFFLINE")
    elif connectivity_status == "STALE":
        data_quality_score = 40.0
        active_indicators.append("STALE_DATA_HEARTBEAT")

    if quality.get("has_missing_data", False):
        data_quality_score = max(0.0, data_quality_score - 25.0)

    # Compute overall physical risk score
    physical_score = max(deformation_score, rate_score, tilt_score)
    # Blend with average of active physical hazards
    hazard_components = [c for c in [deformation_score, rate_score, tilt_score] if c > 0]
    if hazard_components:
        overall_score = round(0.7 * physical_score + 0.3 * (sum(hazard_components) / len(hazard_components)), 1)
    else:
        overall_score = 0.0

    # Categorization logic
    if data_quality_score <= 40.0 and overall_score < 50.0:
        category = "DATA_UNRELIABLE"
        summary = "Monitoring data is stale or incomplete. Physical safety status cannot be reliably verified."
    elif overall_score >= 75.0 or "CRITICAL_ACCELERATION" in active_indicators or "CRITICAL_DISPLACEMENT" in active_indicators or "CRITICAL_TILT" in active_indicators:
        category = "CRITICAL"
        summary = "Critical geotechnical instability detected. Accelerating subsidence or high cumulative movement."
    elif overall_score >= 45.0 or "WARNING_DISPLACEMENT" in active_indicators or "WARNING_VELOCITY" in active_indicators or "WARNING_TILT" in active_indicators:
        category = "WARNING"
        summary = "Elevated ground movement or tilt observed exceeding operational warning thresholds."
    elif overall_score >= 20.0:
        category = "WATCH"
        summary = "Low-level baseline movement detected. Continue routine automated monitoring."
    else:
        category = "NORMAL"
        summary = "Ground movement within baseline equilibrium. Nominal stability indicators."

    return RiskScoreItem(
        category=category,
        overall_score=overall_score,
        deformation_score=deformation_score,
        rate_score=rate_score,
        tilt_score=tilt_score,
        data_quality_score=data_quality_score,
        summary=summary,
        active_indicators=active_indicators
    )
