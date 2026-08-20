from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from app.services.data_service import data_service
from app.tools.progress_tools import get_current_topic, get_next_topic

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.get("/today")
async def get_today_session_endpoint():
    session = data_service.get_today_session()
    if not session:
        # If no session matching exact date, get current completed or next topic session
        curr = get_current_topic()
        if curr:
            session = data_service.get_session_details(curr["session_number"])
        else:
            tp = data_service.get_teaching_plan()
            if not tp.empty:
                session = tp.iloc[0].to_dict()

    if not session:
        raise HTTPException(status_code=404, detail="No session found in teaching plan.")

    batches = data_service.get_batches()
    active_batch = batches[batches["status"].astype(str).str.title() == "Active"]
    batch_info = active_batch.iloc[0].to_dict() if not active_batch.empty else {}

    candidates = data_service.get_candidates()
    active_cands = candidates[candidates["status"].astype(str).str.title() == "Active"]

    return {
        "session": session,
        "batch": batch_info,
        "total_active_candidates": len(active_cands)
    }

@router.get("/{session_number}")
async def get_session_by_number(session_number: int):
    try:
        session = data_service.get_session_details(session_number)
        return session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
