from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from app.schemas import GenerateDraftsRequest, CommunicationAction
from app.tools.communication_tools import (
    load_comm_log,
    auto_generate_drafts_for_absentees,
    approve_and_send_communication,
    reject_communication
)
from app.services.data_service import data_service
from app.core.dependencies import get_current_admin

router = APIRouter(prefix="/communications", tags=["Communications"])

@router.get("", response_model=List[Dict[str, Any]])
async def list_communications():
    log = load_comm_log()
    if log.empty:
        return []

    candidates = data_service.get_candidates()
    if not candidates.empty:
        merged = log.merge(
            candidates[["candidate_id", "candidate_name"]],
            on="candidate_id",
            how="left"
        )
        return merged.to_dict("records")
    return log.to_dict("records")

@router.get("/pending", response_model=List[Dict[str, Any]])
async def get_pending_communications():
    log = load_comm_log()
    if log.empty:
        return []

    pending = log[log["status"].astype(str).str.upper() == "PENDING_APPROVAL"]
    if pending.empty:
        return []

    candidates = data_service.get_candidates()
    if not candidates.empty:
        merged = pending.merge(
            candidates[["candidate_id", "candidate_name"]],
            on="candidate_id",
            how="left"
        )
        return merged.to_dict("records")
    return pending.to_dict("records")

@router.post("/generate-drafts")
async def generate_drafts_endpoint(
    req: GenerateDraftsRequest,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    try:
        drafts = auto_generate_drafts_for_absentees(req.session_number, channel=req.channel)
        return {
            "session_number": req.session_number,
            "channel": req.channel,
            "drafts_created": len(drafts),
            "drafts": drafts
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{comm_id}/approve")
async def approve_communication_endpoint(
    comm_id: str,
    action: Optional[CommunicationAction] = None,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    try:
        subj = action.subject if action else None
        msg = action.message if action else None
        res = approve_and_send_communication(comm_id, edited_subject=subj, edited_message=msg)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{comm_id}/reject")
async def reject_communication_endpoint(
    comm_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    try:
        res = reject_communication(comm_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{comm_id}/send")
async def send_communication_endpoint(
    comm_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    try:
        res = approve_and_send_communication(comm_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
