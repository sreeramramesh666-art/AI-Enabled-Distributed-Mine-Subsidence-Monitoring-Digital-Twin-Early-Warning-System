from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class AlertAcknowledge(BaseModel):
    acknowledged_by: str = Field(..., min_length=2, max_length=128)
    note: Optional[str] = Field(None, max_length=1000)


class AlertInvestigate(BaseModel):
    investigated_by: str = Field(..., min_length=2, max_length=128)
    investigation_notes: Optional[str] = Field(None, max_length=2000)


class AlertResolve(BaseModel):
    resolved_by: str = Field(..., min_length=2, max_length=128)
    resolution_notes: str = Field(..., min_length=2, max_length=2000)


class AlertReopen(BaseModel):
    reopened_by: str = Field(..., min_length=2, max_length=128)
    reopen_notes: str = Field(..., min_length=2, max_length=2000)


class AlertResponse(BaseModel):
    id: int
    alert_id: str
    node_id: str
    test_run_id: Optional[str] = None
    mine_panel: Optional[str] = None
    sensor_type: Optional[str] = None
    created_at: datetime
    severity: str
    category: str
    status: str
    title: str
    description: str
    recommended_action: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    trend_evidence: Optional[Dict[str, Any]] = None
    triggering_rule: str

    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    acknowledgement_note: Optional[str] = None

    investigated_by: Optional[str] = None
    investigated_at: Optional[datetime] = None
    investigation_notes: Optional[str] = None

    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    reopened_by: Optional[str] = None
    reopened_at: Optional[datetime] = None
    reopen_notes: Optional[str] = None

    lifecycle_history: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    total: int
    active_critical: int
    active_warning: int
    active_under_investigation: int = 0
    items: List[AlertResponse]
