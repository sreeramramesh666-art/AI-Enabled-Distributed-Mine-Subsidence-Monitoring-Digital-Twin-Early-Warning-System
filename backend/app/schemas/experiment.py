from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class TestRunStartRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    scenario: str = Field(
        ...,
        description="testrig_baseline, testrig_gradual, testrig_differential, testrig_vibration_only, testrig_disconnect_reconnect, testrig_comm_loss, testrig_return_stable"
    )
    test_conditions: str = Field(
        ...,
        min_length=2,
        max_length=256,
        description="e.g. Controlled granular testbed, micrometer lead screw plate"
    )
    target_node_id: Optional[str] = Field(None, max_length=64)
    intended_movement_mm: Optional[float] = Field(None, ge=-500.0, le=500.0)
    notes: Optional[str] = Field(None, max_length=1000)


class TestRunReferenceUpdateRequest(BaseModel):
    reference_movement_mm: float = Field(..., ge=-500.0, le=500.0, description="Independently measured reference movement")
    notes: Optional[str] = Field(None, max_length=1000)


class TestRunCompleteRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000)


class TestRunResponse(BaseModel):
    id: int
    test_run_id: str
    name: str
    scenario: str
    test_conditions: str
    target_node_id: Optional[str] = None
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None

    intended_movement_mm: Optional[float] = None
    reference_movement_mm: Optional[float] = None
    sensor_reported_movement_mm: Optional[float] = None
    measurement_error_mm: Optional[float] = None
    detection_latency_sec: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestRunListResponse(BaseModel):
    total: int
    items: List[TestRunResponse]

