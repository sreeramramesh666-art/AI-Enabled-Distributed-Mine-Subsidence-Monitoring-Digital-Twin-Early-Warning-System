from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.schemas.telemetry import (
    TelemetryIngest, TelemetryResponse, TelemetryBatchIngest, TelemetryBatchResponse
)
from backend.app.services.telemetry_service import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["Telemetry Ingestion"])


@router.post("", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED)
async def ingest_telemetry(telemetry_in: TelemetryIngest, db: Session = Depends(get_db)):
    record, error, is_dup = await TelemetryService.process_single_telemetry(db=db, telemetry=telemetry_in)
    if is_dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate observation with event_id '{telemetry_in.event_id}' or sequence '{telemetry_in.sequence_number}' already ingested."
        )
    if error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)
    return record


@router.post("/batch", response_model=TelemetryBatchResponse, status_code=status.HTTP_200_OK)
async def ingest_telemetry_batch(batch_in: TelemetryBatchIngest, db: Session = Depends(get_db)):
    return await TelemetryService.process_batch_telemetry(db=db, batch=batch_in)
