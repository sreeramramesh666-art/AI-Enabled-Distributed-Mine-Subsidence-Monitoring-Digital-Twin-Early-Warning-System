from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.services.report_service import ReportService
from backend.app.core.security import parse_query_datetime

router = APIRouter(prefix="/reports", tags=["Reports & Export"])


@router.get("/export")
def export_report(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    node_id: Optional[str] = None,
    start_time: Optional[str] = Query(None, description="Start timestamp ISO 8601"),
    end_time: Optional[str] = Query(None, description="End timestamp ISO 8601"),
    db: Session = Depends(get_db)
):
    ts_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

    try:
        parsed_start = parse_query_datetime(start_time)
        parsed_end = parse_query_datetime(end_time)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_time must be earlier than or equal to end_time")

    try:
        if format.lower() == "csv":
            csv_data = ReportService.export_csv(
                db=db, node_id=node_id, start_time=parsed_start, end_time=parsed_end
            )
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=mineguard_telemetry_{ts_str}.csv"}
            )
        else:
            pdf_bytes = ReportService.generate_pdf_report(
                db=db, node_id=node_id, start_time=parsed_start, end_time=parsed_end
            )
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=mineguard_geotechnical_report_{ts_str}.pdf"}
            )
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
