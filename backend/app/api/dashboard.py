from fastapi import APIRouter
from typing import Dict, Any
from app.services.data_service import data_service
from app.tools.progress_tools import (
    get_teaching_progress,
    get_current_topic,
    get_next_topic
)
from app.tools.attendance_tools import (
    calculate_session_attendance,
    get_repeat_absentees,
    get_low_attendance_candidates,
    load_attendance_log
)
from app.tools.scheduling_tools import check_schedule_conflicts
from app.tools.communication_tools import load_comm_log
from app.config import settings

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("", response_model=Dict[str, Any])
async def get_dashboard_summary():
    # 1. Today's session
    session = data_service.get_today_session()
    curr = get_current_topic()
    nxt = get_next_topic()
    if not session and curr:
        session = data_service.get_session_details(curr["session_number"])
    elif not session:
        tp = data_service.get_teaching_plan()
        if not tp.empty:
            session = tp.iloc[0].to_dict()

    # 2. Batch info
    batches = data_service.get_batches()
    active_batch = batches[batches["status"].astype(str).str.title() == "Active"]
    batch_info = active_batch.iloc[0].to_dict() if not active_batch.empty else {}

    # 3. Candidates
    candidates = data_service.get_candidates()
    active_cands = candidates[candidates["status"].astype(str).str.title() == "Active"]
    total_candidates = len(active_cands)

    # 4. Today / latest attendance
    log = load_attendance_log()
    present_today = None
    absent_today = None
    attendance_pct_today = None
    latest_session_num = None

    if not log.empty and session:
        s_num = int(session.get("session_number", 0))
        s_log = log[log["session_number"].astype(int) == s_num]
        if not s_log.empty:
            summary = calculate_session_attendance(s_num)
            present_today = summary["present"]
            absent_today = summary["absent"]
            attendance_pct_today = summary["attendance_percent"]
        else:
            latest_s = log["session_number"].astype(int).max()
            latest_session_num = int(latest_s)
            summary = calculate_session_attendance(latest_s)
            present_today = summary["present"]
            absent_today = summary["absent"]
            attendance_pct_today = summary["attendance_percent"]

    # 5. Progress
    progress = get_teaching_progress()
    progress["current_topic"] = curr
    progress["next_topic"] = nxt

    # 6. Repeats & Low attendance
    repeats_df = get_repeat_absentees(2)
    low_df = get_low_attendance_candidates(75.0)

    # 7. Pending comms
    comm_log = load_comm_log()
    pending_count = 0
    if not comm_log.empty:
        pending_count = len(comm_log[comm_log["status"].astype(str).str.upper() == "PENDING_APPROVAL"])

    # 8. Schedule conflicts
    conflicts_df = check_schedule_conflicts()

    return {
        "today_session": session,
        "batch": batch_info,
        "total_candidates": total_candidates,
        "present_today": present_today,
        "absent_today": absent_today,
        "attendance_percent_today": attendance_pct_today,
        "latest_recorded_session": latest_session_num,
        "progress": progress,
        "repeat_absentees": repeats_df.to_dict("records") if not repeats_df.empty else [],
        "low_attendance_candidates": low_df.to_dict("records") if not low_df.empty else [],
        "pending_communications_count": pending_count,
        "schedule_conflicts": conflicts_df.to_dict("records") if not conflicts_df.empty else [],
        "dry_run": settings.DRY_RUN
    }
