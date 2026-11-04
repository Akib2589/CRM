# app/validators/stage_validator.py
from enum import Enum
from typing import List, Dict, Any, Tuple

class LeadStage(str, Enum):
    NEW = "New"
    CONTACTED = "Contacted"
    MEETING = "Meeting"
    PROPOSAL = "Proposal"
    INVOICE_SENT = "Invoice sent"
    PAID = "Paid"
    LOST = "Lost"

VALID_STAGES = [stage.value for stage in LeadStage]
ACTIVE_STAGES = [
    LeadStage.NEW.value,
    LeadStage.CONTACTED.value,
    LeadStage.MEETING.value,
    LeadStage.PROPOSAL.value,
    LeadStage.INVOICE_SENT.value,
]
TERMINAL_STAGES = [
    LeadStage.PAID.value,
    LeadStage.LOST.value,
]

STAGE_ORDER = {
    LeadStage.NEW.value: 1,
    LeadStage.CONTACTED.value: 2,
    LeadStage.MEETING.value: 3,
    LeadStage.PROPOSAL.value: 4,
    LeadStage.INVOICE_SENT.value: 5,
    LeadStage.PAID.value: 6,
    LeadStage.LOST.value: 99,
}

def validate_stage_and_value(stage: str, deal_value: int | float | None) -> List[Dict[str, Any]]:
    issues = []
    
    if stage not in VALID_STAGES:
        issues.append({
            "issue_type": "INVALID_STAGE",
            "severity": "CRITICAL",
            "description": f"Stage '{stage}' is not a recognized pipeline stage."
        })
        
    if deal_value is not None:
        try:
            val = int(deal_value)
            if val < 0:
                issues.append({
                    "issue_type": "INVALID_DEAL_VALUE",
                    "severity": "CRITICAL",
                    "description": f"Deal value {deal_value} cannot be negative."
                })
        except (ValueError, TypeError):
            issues.append({
                "issue_type": "INVALID_DEAL_VALUE",
                "severity": "CRITICAL",
                "description": f"Deal value '{deal_value}' is not a valid number."
            })
            
    return issues

def validate_stage_transition(
    current_stage: str,
    target_stage: str,
    reason: str | None = None
) -> Tuple[bool, str | None]:
    if target_stage not in VALID_STAGES:
        return False, f"Target stage '{target_stage}' is invalid."
        
    if current_stage == target_stage:
        return True, None
        
    # Reopening from terminal stage
    if current_stage in TERMINAL_STAGES and target_stage not in TERMINAL_STAGES:
        if not reason or not reason.strip():
            return False, f"Reopening a lead from '{current_stage}' stage requires an explicit reason."
            
    return True, None
