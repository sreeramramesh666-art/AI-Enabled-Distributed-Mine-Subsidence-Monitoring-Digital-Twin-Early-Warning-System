from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports & Export"])


@router.get("/export")
def export_report(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    node_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    ts_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    if format.lower() == "csv":
        csv_data = ReportService.export_csv(
            db=db, node_id=node_id, start_time=start_time, end_time=end_time
        )
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=mineguard_telemetry_{ts_str}.csv"}
        )
    else:
        pdf_bytes = ReportService.generate_pdf_report(
            db=db, start_time=start_time, end_time=end_time
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=mineguard_geotechnical_report_{ts_str}.pdf"}
        )
