from sqlalchemy.orm import Session
from backend.app.db.models import TelemetryRecord


class DeduplicationChecker:
    @staticmethod
    def is_duplicate(db: Session, event_id: str, node_id: str, sequence_number: int | None) -> bool:
        """
        Check if an event with this event_id or (node_id, sequence_number) has already been ingested.
        """
        # Primary check: unique event_id
        if event_id:
            exists = db.query(TelemetryRecord.id).filter(TelemetryRecord.event_id == event_id).first()
            if exists:
                return True

        # Secondary check: monotonic node sequence number
        if sequence_number is not None:
            seq_exists = db.query(TelemetryRecord.id).filter(
                TelemetryRecord.node_id == node_id,
                TelemetryRecord.sequence_number == sequence_number
            ).first()
            if seq_exists:
                return True

        return False

