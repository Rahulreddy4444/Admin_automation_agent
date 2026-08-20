from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.services.data_service import data_service
from app.tools.attendance_tools import get_candidate_attendance_history, load_attendance_log
from app.tools.communication_tools import load_comm_log

router = APIRouter(prefix="/candidates", tags=["Candidates"])

@router.get("", response_model=List[Dict[str, Any]])
async def list_candidates():
    candidates = data_service.get_candidates()
    if candidates.empty:
        return []

    result = []
    for _, row in candidates.iterrows():
        cid = row["candidate_id"]
        stats = get_candidate_attendance_history(cid)
        c_dict = row.to_dict()
        c_dict["attendance_percent"] = stats.get("attendance_percent", 0.0)
        c_dict["sessions_attended"] = stats.get("present", 0)
        c_dict["sessions_missed"] = stats.get("absent", 0)
        result.append(c_dict)

    return result

@router.get("/{candidate_id}")
async def get_candidate_detail(candidate_id: int):
    candidates = data_service.get_candidates()
    match = candidates[candidates["candidate_id"].astype(str) == str(candidate_id)]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")

    cand = match.iloc[0].to_dict()
    stats = get_candidate_attendance_history(candidate_id)
    cand.update(stats)

    # Attendance logs for this candidate
    att_log = load_attendance_log()
    c_att = att_log[att_log["candidate_id"].astype(str) == str(candidate_id)]

    # Communication logs for this candidate
    comm_log = load_comm_log()
    c_comm = comm_log[comm_log["candidate_id"].astype(str) == str(candidate_id)]

    return {
        "candidate": cand,
        "attendance_history": c_att.to_dict("records") if not c_att.empty else [],
        "communication_history": c_comm.to_dict("records") if not c_comm.empty else []
    }
