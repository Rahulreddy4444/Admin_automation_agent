import pandas as pd
from typing import Dict, Any, Optional
from app.services.data_service import data_service
from app.tools.attendance_tools import load_attendance_log

def get_teaching_progress() -> Dict[str, Any]:
    """
    Calendar-based teaching progress matching notebook logic.
    """
    teaching_plan = data_service.get_teaching_plan()
    if teaching_plan.empty:
        return {
            "total_planned": 0,
            "completed": 0,
            "remaining": 0,
            "completion_percent": 0.0,
            "last_completed_session": None,
            "attendance_recorded_sessions": 0,
            "attendance_gap": 0
        }

    total_planned = len(teaching_plan)
    today = data_service.get_today_date()

    try:
        planned_dates = pd.to_datetime(teaching_plan["planned_date"], format="%d-%m-%Y", errors="coerce").dt.date
        due = teaching_plan[planned_dates <= today]
        n_due = len(due)
        last_due_session = int(due["session_number"].max()) if not due.empty else None
    except Exception:
        n_due = 0
        last_due_session = None

    log = load_attendance_log()
    recorded_sessions = sorted(log["session_number"].unique().tolist()) if not log.empty else []

    return {
        "total_planned": total_planned,
        "completed": n_due,
        "remaining": max(0, total_planned - n_due),
        "completion_percent": round(n_due / total_planned * 100, 2) if total_planned else 0.0,
        "last_completed_session": last_due_session,
        "attendance_recorded_sessions": len(recorded_sessions),
        "attendance_gap": max(0, n_due - len(recorded_sessions)),
    }

def get_current_topic() -> Optional[Dict[str, Any]]:
    progress = get_teaching_progress()
    tp = data_service.get_teaching_plan()
    if progress["last_completed_session"] is None or tp.empty:
        return None
    row = tp[tp["session_number"] == progress["last_completed_session"]]
    if row.empty:
        return None
    r = row.iloc[0]
    return {
        "session_number": int(r["session_number"]),
        "planned_date": str(r["planned_date"]),
        "module": str(r["module"]),
        "topic_title": str(r["topic_title"]),
        "subtopics": str(r.get("subtopics", ""))
    }

def get_next_topic() -> Optional[Dict[str, Any]]:
    progress = get_teaching_progress()
    tp = data_service.get_teaching_plan()
    if tp.empty:
        return None
    next_num = (progress["last_completed_session"] or 0) + 1
    row = tp[tp["session_number"] == next_num]
    if row.empty:
        return None
    r = row.iloc[0]
    return {
        "session_number": int(r["session_number"]),
        "planned_date": str(r["planned_date"]),
        "module": str(r["module"]),
        "topic_title": str(r["topic_title"]),
        "subtopics": str(r.get("subtopics", ""))
    }
