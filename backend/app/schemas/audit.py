from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    id: int
    timestamp: datetime
    category: str
    node_id: Optional[str] = None
    alert_id: Optional[str] = None
    actor: str
    action: str
    outcome: str
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class AuditEventList(BaseModel):
    total: int
    items: List[AuditEventResponse]

