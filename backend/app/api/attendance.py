from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from app.schemas import AttendanceRecordSubmit, AttendanceSummary
from app.tools.attendance_tools import (
    record_daily_absences,
    calculate_session_attendance,
    get_absent_candidates,
    load_attendance_log
)
from app.tools.reporting_tools import generate_daily_report
from app.tools.communication_tools import auto_generate_drafts_for_absentees
from app.services.data_service import data_service
from app.core.dependencies import get_current_admin

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.post("", response_model=Dict[str, Any])
async def submit_attendance(
    req: AttendanceRecordSubmit,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    try:
        session = data_service.get_session_details(req.session_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    session_date = session.get("planned_date", "")
    admin_name = current_admin.get("admin_name", "Admin")

    try:
        summary = record_daily_absences(
            session_number=req.session_number,
            session_date=session_date,
            batch_id=req.batch_id or "b1",
            absent_ids=req.absent_candidate_ids,
            remarks=req.remarks or {},
            submitted_by=admin_name,
            force_resubmit=req.force_resubmit
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Auto-generate daily report
    daily_report = generate_daily_report(req.session_number)

    # Auto-generate communication drafts for absentees (Email and WhatsApp)
    email_drafts = auto_generate_drafts_for_absentees(req.session_number, channel="Email")
    whatsapp_drafts = auto_generate_drafts_for_absentees(req.session_number, channel="WhatsApp")

    return {
        "summary": summary,
        "daily_report": daily_report,
        "email_drafts": email_drafts,
        "whatsapp_drafts": whatsapp_drafts,
        "message": f"Attendance submitted successfully: {summary['present']} present, {summary['absent']} absent."
    }

@router.get("/history")
async def get_attendance_history():
    log = load_attendance_log()
    if log.empty:
        return []

    tp = data_service.get_teaching_plan()
    unique_sessions = log["session_number"].unique()
    history = []

    for s_num in sorted(unique_sessions, reverse=True):
        try:
            summary = calculate_session_attendance(int(s_num))
            topic = "Session"
            if not tp.empty:
                t_match = tp[tp["session_number"] == int(s_num)]
                if not t_match.empty:
                    topic = t_match.iloc[0].get("topic_title", "Session")

            first_row = log[log["session_number"] == s_num].iloc[0]
            history.append({
                "session_number": int(s_num),
                "session_date": str(first_row.get("session_date", "")),
                "topic_title": topic,
                "total": summary["total"],
                "present": summary["present"],
                "absent": summary["absent"],
                "attendance_percent": summary["attendance_percent"],
                "submitted_by": str(first_row.get("submitted_by", "Admin")),
                "submitted_at": str(first_row.get("submitted_at", ""))
            })
        except Exception:
            continue

    return history

@router.get("/session/{session_number}")
async def get_session_attendance_detail(session_number: int):
    log = load_attendance_log()
    session_log = log[log["session_number"].astype(int) == int(session_number)]
    if session_log.empty:
        raise HTTPException(status_code=404, detail=f"No attendance recorded for session {session_number}")

    summary = calculate_session_attendance(session_number)
    absentees_df = get_absent_candidates(session_number)
    
    candidates = data_service.get_candidates()
    all_roster = session_log.merge(
        candidates[["candidate_id", "candidate_name", "email", "phone"]],
        on="candidate_id",
        how="left"
    )

    return {
        "summary": summary,
        "absent_candidates": absentees_df.to_dict("records"),
        "roster_attendance": all_roster.to_dict("records")
    }
