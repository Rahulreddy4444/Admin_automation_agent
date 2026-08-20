from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from app.tools.reporting_tools import generate_daily_report
from app.tools.attendance_tools import load_attendance_log
from app.services.data_service import data_service

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("", response_model=List[Dict[str, Any]])
async def list_reports():
    log = load_attendance_log()
    if log.empty:
        return []

    unique_sessions = sorted(log["session_number"].astype(int).unique(), reverse=True)
    reports = []

    for s_num in unique_sessions:
        try:
            report_text = generate_daily_report(s_num)
            session = data_service.get_session_details(s_num)
            reports.append({
                "session_number": s_num,
                "session_date": str(session.get("planned_date", "")),
                "topic_title": str(session.get("topic_title", "")),
                "module": str(session.get("module", "")),
                "report_text": report_text
            })
        except Exception:
            continue

    return reports

@router.post("/generate")
async def generate_report_endpoint(session_number: int = Query(...)):
    try:
        report_text = generate_daily_report(session_number)
        session = data_service.get_session_details(session_number)
        return {
            "session_number": session_number,
            "session_date": str(session.get("planned_date", "")),
            "topic_title": str(session.get("topic_title", "")),
            "report_text": report_text
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
