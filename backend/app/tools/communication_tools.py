import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.config import settings
from app.services.data_service import data_service
from app.services.email_service import send_email_direct
from app.services.whatsapp_service import send_whatsapp_via_twilio
from app.tools.attendance_tools import get_absent_candidates

COMM_LOG_CSV = os.path.join(settings.DATA_DIR, "communication_log.csv")
COMM_LOG_COLUMNS = [
    "communication_id", "candidate_id", "session_number", "channel", "recipient",
    "subject", "message", "status", "created_at", "approved_at", "sent_at", "error"
]

def load_comm_log() -> pd.DataFrame:
    if os.path.exists(COMM_LOG_CSV):
        try:
            df = pd.read_csv(COMM_LOG_CSV)
            # Ensure timestamp/text columns are object dtype so string
            # assignment never clashes with a pandas-inferred float64 column.
            for col in ("approved_at", "sent_at", "error"):
                if col in df.columns:
                    df[col] = df[col].astype(object)
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=COMM_LOG_COLUMNS)

def _next_comm_id() -> int:
    log = load_comm_log()
    if log.empty or "communication_id" not in log.columns:
        return 1
    nums = log["communication_id"].astype(str).str.extract(r"MSG(\d+)").dropna().astype(int)
    if nums.empty:
        return 1
    return int(nums.max().iloc[0]) + 1

def log_communication(
    candidate_id: int,
    session_number: int,
    channel: str,
    recipient: str,
    subject: Optional[str],
    message: str,
    status: str = "DRAFT",
    error: Optional[str] = None
) -> str:
    log = load_comm_log()
    now = datetime.now().isoformat(timespec="seconds")
    comm_id = f"MSG{str(_next_comm_id()).zfill(3)}"
    
    row = {
        "communication_id": comm_id,
        "candidate_id": int(candidate_id),
        "session_number": int(session_number),
        "channel": channel,
        "recipient": recipient,
        "subject": subject or "",
        "message": message,
        "status": status,
        "created_at": now,
        "approved_at": now if status in ("APPROVED", "SENT") else "",
        "sent_at": now if status == "SENT" else "",
        "error": error or "",
    }
    
    new_log = pd.concat([log, pd.DataFrame([row])], ignore_index=True)
    new_log.to_csv(COMM_LOG_CSV, index=False)
    return comm_id

def generate_email_draft(candidate_id: int, session_number: int) -> Dict[str, Any]:
    candidates = data_service.get_candidates()
    match = candidates[candidates["candidate_id"].astype(str) == str(candidate_id)]
    if match.empty:
        raise ValueError(f"Candidate {candidate_id} not found in master records.")
    cand = match.iloc[0]

    session = data_service.get_session_details(session_number)
    module_title = session.get("module") or "training"
    topic_title = session.get("topic_title") or "Session"
    
    subject = "Absence from Today's Training Session"
    body = (
        f"Dear {cand['candidate_name']},\n\n"
        f"We noticed that you were absent from today's {module_title} session "
        f"(\"{topic_title}\").\n\n"
        f"Please contact the coordinator if you faced any difficulty attending the session.\n\n"
        f"Regards,\nTraining Coordination Team"
    )
    return {
        "candidate_id": int(cand["candidate_id"]),
        "candidate_name": str(cand["candidate_name"]),
        "recipient": str(cand["email"]),
        "subject": subject,
        "message": body,
        "channel": "Email"
    }

def generate_whatsapp_draft(candidate_id: int, session_number: int) -> Dict[str, Any]:
    candidates = data_service.get_candidates()
    match = candidates[candidates["candidate_id"].astype(str) == str(candidate_id)]
    if match.empty:
        raise ValueError(f"Candidate {candidate_id} not found in master records.")
    cand = match.iloc[0]

    session = data_service.get_session_details(session_number)
    module_title = session.get("module") or "training"
    topic_title = session.get("topic_title") or "Session"

    message = (
        f"Hi {cand['candidate_name']}, we noticed you were absent from today's "
        f"{module_title} session ({topic_title}). "
        f"Please reach out if you need any help catching up."
    )
    return {
        "candidate_id": int(cand["candidate_id"]),
        "candidate_name": str(cand["candidate_name"]),
        "recipient": str(cand["phone"]),
        "subject": None,
        "message": message,
        "channel": "WhatsApp"
    }

def auto_generate_drafts_for_absentees(session_number: int, channel: str = "Email") -> List[Dict[str, Any]]:
    absentees = get_absent_candidates(session_number)
    if absentees.empty:
        return []

    created_drafts = []
    log = load_comm_log()

    for _, row in absentees.iterrows():
        cid = int(row["candidate_id"])
        # Check if already logged for this session and channel
        existing = log[
            (log["candidate_id"].astype(str) == str(cid)) &
            (log["session_number"].astype(int) == int(session_number)) &
            (log["channel"].astype(str).str.lower() == channel.lower())
        ]
        
        if existing.empty:
            if channel.lower() == "whatsapp":
                draft = generate_whatsapp_draft(cid, session_number)
            else:
                draft = generate_email_draft(cid, session_number)

            comm_id = log_communication(
                candidate_id=cid,
                session_number=session_number,
                channel=channel,
                recipient=draft["recipient"],
                subject=draft.get("subject"),
                message=draft["message"],
                status="PENDING_APPROVAL"
            )
            draft["communication_id"] = comm_id
            draft["status"] = "PENDING_APPROVAL"
            created_drafts.append(draft)

    return created_drafts

def approve_and_send_communication(comm_id: str, edited_subject: Optional[str] = None, edited_message: Optional[str] = None) -> Dict[str, Any]:
    log = load_comm_log()
    idx = log[log["communication_id"] == comm_id].index
    if idx.empty:
        raise ValueError(f"Communication ID {comm_id} not found.")

    row = log.loc[idx[0]].to_dict()
    subject = edited_subject if edited_subject is not None else row.get("subject", "")
    message = edited_message if edited_message is not None else row.get("message", "")
    channel = str(row.get("channel", "Email")).strip()
    recipient = str(row.get("recipient", "")).strip()

    # Mark as APPROVED in log
    now = datetime.now().isoformat(timespec="seconds")
    # Cast columns that may have been inferred as float64 (all-NaN) to object
    for col in ("status", "approved_at", "sent_at", "error", "subject", "message"):
        if col in log.columns:
            log[col] = log[col].astype(object)
    log.loc[idx, "status"] = "APPROVED"
    log.loc[idx, "approved_at"] = now
    if edited_subject:
        log.loc[idx, "subject"] = edited_subject
    if edited_message:
        log.loc[idx, "message"] = edited_message

    # Execute send via direct SMTP or Twilio
    if channel.lower() == "email":
        result = send_email_direct(recipient, subject, message)
    else:
        result = send_whatsapp_via_twilio(recipient, message)

    if result.get("success"):
        log.loc[idx, "status"] = "SENT"
        log.loc[idx, "sent_at"] = now
        log.loc[idx, "error"] = ""
    else:
        log.loc[idx, "status"] = "FAILED"
        log.loc[idx, "error"] = str(result.get("error", "Send failed"))

    log.to_csv(COMM_LOG_CSV, index=False)
    return {
        "communication_id": comm_id,
        "status": log.loc[idx[0], "status"],
        "result": result
    }

def reject_communication(comm_id: str) -> Dict[str, Any]:
    log = load_comm_log()
    idx = log[log["communication_id"] == comm_id].index
    if idx.empty:
        raise ValueError(f"Communication ID {comm_id} not found.")

    now = datetime.now().isoformat(timespec="seconds")
    log.loc[idx, "status"] = "REJECTED"
    log.loc[idx, "approved_at"] = now
    log.to_csv(COMM_LOG_CSV, index=False)
    return {"communication_id": comm_id, "status": "REJECTED"}
