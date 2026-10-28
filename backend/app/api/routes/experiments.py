from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.schemas.experiment import (
    TestRunStartRequest, TestRunReferenceUpdateRequest, TestRunCompleteRequest,
    TestRunResponse, TestRunListResponse
)
from backend.app.services.experiment_service import ExperimentService

router = APIRouter(prefix="/test-runs", tags=["Test-Rig Experiments"])


@router.post("", response_model=TestRunResponse, status_code=status.HTTP_201_CREATED)
def start_test_run(request: TestRunStartRequest, db: Session = Depends(get_db)):
    """Start a new laboratory test-rig benchmark experiment run."""
    try:
        return ExperimentService.start_test_run(db=db, request=request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=TestRunListResponse)
def list_test_runs(
    status: Optional[str] = Query(None, description="Filter by status: RUNNING, COMPLETED, ABORTED"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List benchmark experiment runs."""
    items, total = ExperimentService.list_test_runs(db=db, status=status, skip=skip, limit=limit)
    return TestRunListResponse(total=total, items=items)


@router.get("/{test_run_id}", response_model=TestRunResponse)
def get_test_run(test_run_id: str, db: Session = Depends(get_db)):
    """Retrieve details and Table 12 metrics for a specific test run."""
    run = ExperimentService.get_test_run(db=db, test_run_id=test_run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Test run '{test_run_id}' not found")
    return run


@router.post("/{test_run_id}/reference", response_model=TestRunResponse)
def record_reference_movement(
    test_run_id: str,
    request: TestRunReferenceUpdateRequest,
    db: Session = Depends(get_db)
):
    """Log ground-truth displacement measured independently via dial indicator or micrometer."""
    run = ExperimentService.record_reference_movement(db=db, test_run_id=test_run_id, request=request)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Test run '{test_run_id}' not found")
    return run


@router.post("/{test_run_id}/complete", response_model=TestRunResponse)
def complete_test_run(
    test_run_id: str,
    request: Optional[TestRunCompleteRequest] = None,
    db: Session = Depends(get_db)
):
    """Conclude test run and calculate Table 12 evaluation metrics."""
    run = ExperimentService.complete_test_run(db=db, test_run_id=test_run_id, request=request)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Test run '{test_run_id}' not found")
    return run


@router.get("/{test_run_id}/export/csv")
def export_test_run_csv(test_run_id: str, db: Session = Depends(get_db)):
    """Export test run evaluation metrics and telemetry time series in CSV format."""
    try:
        csv_data = ExperimentService.export_test_run_csv(db=db, test_run_id=test_run_id)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=test_run_{test_run_id}.csv"}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{test_run_id}/export/pdf")
def export_test_run_pdf(test_run_id: str, db: Session = Depends(get_db)):
    """Export formatted PDF report containing Table 12 laboratory benchmark metrics."""
    try:
        pdf_bytes = ExperimentService.export_test_run_pdf(db=db, test_run_id=test_run_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=test_run_{test_run_id}.pdf"}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

