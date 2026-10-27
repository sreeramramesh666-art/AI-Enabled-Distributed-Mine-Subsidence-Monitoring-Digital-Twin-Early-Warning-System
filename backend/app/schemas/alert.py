from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class AlertAcknowledge(BaseModel):
    acknowledged_by: str = Field(..., min_length=2, max_length=128)
    note: Optional[str] = Field(None, max_length=1000)


class AlertResolve(BaseModel):
    resolved_by: str = Field(..., min_length=2, max_length=128)
    resolution_notes: str = Field(..., min_length=2, max_length=2000)


class AlertResponse(BaseModel):
    id: int
    alert_id: str
    node_id: str
    created_at: datetime
    severity: str
    category: str
    status: str
    title: str
    description: str
    evidence: Optional[Dict[str, Any]] = None
    triggering_rule: str

    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    acknowledgement_note: Optional[str] = None

    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    total: int
    active_critical: int
    active_warning: int
    items: List[AlertResponse]
