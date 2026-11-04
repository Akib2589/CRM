# app/services/pipeline_service.py
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.lead import Lead
from app.models.stage_history import StageHistory
from app.models.audit_log import AuditLog
from app.validators.stage_validator import validate_stage_transition, VALID_STAGES
from app.repositories.lead_repository import LeadRepository
from app.services.data_quality_service import DataQualityService

class PipelineService:
    def __init__(self, db: Session):
        self.db = db
        self.lead_repo = LeadRepository(db)
        self.dq_service = DataQualityService(db)

    def change_stage(self, lead_id: int, target_stage: str, reason: Optional[str] = None) -> Dict[str, Any]:
        lead = self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise ValueError(f"Lead with ID {lead_id} not found.")

        current_stage = lead.stage
        is_valid, err_msg = validate_stage_transition(current_stage, target_stage, reason)
        if not is_valid:
            raise ValueError(err_msg)

        now = datetime.now(timezone.utc)

        # Update lead stage
        lead.stage = target_stage
        lead.updated_at = now

        # Add StageHistory
        history = StageHistory(
            lead_id=lead.id,
            from_stage=current_stage,
            to_stage=target_stage,
            reason=reason or f"Transition from {current_stage} to {target_stage}",
            changed_at=now
        )
        self.db.add(history)

        # Audit log
        audit = AuditLog(
            lead_id=lead.id,
            company_id=lead.company_id,
            action="STAGE_CHANGE",
            old_value=current_stage,
            new_value=target_stage,
            created_at=now
        )
        self.db.add(audit)

        self.db.commit()
        self.db.refresh(lead)

        # Trigger quality scan
        self.dq_service.scan_all_leads()

        return {
            "lead_id": lead.id,
            "previous_stage": current_stage,
            "current_stage": lead.stage,
            "changed_at": now.isoformat(),
            "reason": reason
        }

    def get_stage_history(self, lead_id: int) -> List[Dict[str, Any]]:
        history_records = list(
            self.db.execute(
                select(StageHistory)
                .where(StageHistory.lead_id == lead_id)
                .order_by(StageHistory.changed_at.desc())
            ).scalars().all()
        )
        return [
            {
                "id": h.id,
                "lead_id": h.lead_id,
                "from_stage": h.from_stage,
                "to_stage": h.to_stage,
                "reason": h.reason,
                "changed_at": h.changed_at.isoformat()
            }
            for h in history_records
        ]
