from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class RiskScoreItem(BaseModel):
    category: str  # NORMAL, WATCH, WARNING, CRITICAL, DATA_UNRELIABLE
    overall_score: float  # 0.0 to 100.0
    deformation_score: float
    rate_score: float
    tilt_score: float
    data_quality_score: float
    summary: str
    active_indicators: List[str]


class AnalyticsSummaryResponse(BaseModel):
    total_nodes: int
    online_nodes: int
    stale_nodes: int
    offline_nodes: int
    active_critical_alerts: int
    active_warning_alerts: int
    active_watch_alerts: int
    overall_risk_category: str
    last_telemetry_at: Optional[datetime] = None
    data_completeness_pct: float
    simulator_active: bool


class NodeHealthItem(BaseModel):
    node_id: str
    name: str
    connectivity_status: str
    last_seen: Optional[datetime] = None
    battery_pct: Optional[float] = None
    packet_loss_estimate_pct: float
    quality_status: str
    drift_detected: bool


class TrendSeriesPoint(BaseModel):
    timestamp: datetime
    displacement_mm: Optional[float] = None
    velocity_mm_hr: Optional[float] = None
    vector_tilt_deg: Optional[float] = None
    vibration_rms_ms2: Optional[float] = None


class TrendResponse(BaseModel):
    node_id: str
    time_window_hours: float
    series: List[TrendSeriesPoint]
    max_rate_mm_hr: Optional[float] = None
    total_net_displacement_mm: Optional[float] = None


class SpatialCorroborationItem(BaseModel):
    cluster_id: str
    node_ids: List[str]
    centroid_lat: float
    centroid_lon: float
    average_displacement_mm: float
    corroboration_status: str  # CORROBORATED_HAZARD, ISOLATED_EVENT, STABLE_CLUSTER
    description: str


class SpatialCorroborationResponse(BaseModel):
    timestamp: datetime
    active_clusters: List[SpatialCorroborationItem]
