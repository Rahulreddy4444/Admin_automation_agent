from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.services.data_service import data_service
from app.tools.progress_tools import get_teaching_progress

router = APIRouter(prefix="/batches", tags=["Batches"])

@router.get("", response_model=List[Dict[str, Any]])
async def list_batches():
    batches = data_service.get_batches()
    candidates = data_service.get_candidates()
    progress = get_teaching_progress()

    result = []
    for _, row in batches.iterrows():
        b_dict = row.to_dict()
        bid = str(row["batch_id"])
        c_in_batch = candidates[candidates["batch_id"].astype(str) == bid]
        b_dict["candidate_count"] = len(c_in_batch)
        b_dict["sessions_completed"] = progress.get("completed", 0)
        b_dict["progress_percent"] = progress.get("completion_percent", 0.0)
        result.append(b_dict)

    return result

@router.get("/{batch_id}")
async def get_batch_detail(batch_id: str):
    batches = data_service.get_batches()
    match = batches[batches["batch_id"].astype(str) == str(batch_id)]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found.")

    b_dict = match.iloc[0].to_dict()
    candidates = data_service.get_candidates()
    c_in_batch = candidates[candidates["batch_id"].astype(str) == str(batch_id)]

    progress = get_teaching_progress()
    b_dict["candidate_count"] = len(c_in_batch)
    b_dict["progress"] = progress

    return {
        "batch": b_dict,
        "candidates": c_in_batch.to_dict("records")
    }
