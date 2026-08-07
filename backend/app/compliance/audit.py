import logging
import datetime
from typing import Optional

logger = logging.getLogger("compliance_audit")

def log_pii_access(
    user_id: str,
    action: str,
    resource: str,
    status: str,
    details: Optional[str] = None
) -> None:
    """
    Logs access to Personally Identifiable Information (PII) or sensitive actions.
    This helps demonstrate compliance with the Indian DPDP Act.
    """
    timestamp = datetime.datetime.utcnow().isoformat()
    log_msg = (
        f"[AUDIT] [{timestamp}] User: {user_id} | Action: {action} | "
        f"Resource: {resource} | Status: {status}"
    )
    if details:
        log_msg += f" | Details: {details}"
    
    # In production, this can also write to a dedicated audit_logs database table
    logger.info(log_msg)
