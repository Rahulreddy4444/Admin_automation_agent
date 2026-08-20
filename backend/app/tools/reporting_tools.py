from typing import Dict, Any, List
from app.services.data_service import data_service
from app.tools.attendance_tools import (
    calculate_session_attendance,
    get_absent_candidates,
    get_repeat_absentees
)

def generate_daily_report(session_number: int) -> str:
    session = data_service.get_session_details(session_number)
    summary = calculate_session_attendance(session_number)
    absentees = get_absent_candidates(session_number)
    repeat_df = get_repeat_absentees(2)
    repeat_ids = set(repeat_df["candidate_id"].tolist()) if not repeat_df.empty else set()

    lines = []
    lines.append("DAILY SESSION REPORT")
    lines.append("=" * 40)
    lines.append(f"Session: {session.get('session_number')}")
    lines.append(f"Date: {session.get('planned_date')}")
    lines.append(f"Module: {session.get('module')}")
    lines.append(f"Topic: {session.get('topic_title')}")
    lines.append(f"Sub-topics: {session.get('subtopics')}")
    lines.append("")
    lines.append(f"Total Candidates: {summary['total']}")
    lines.append(f"Present: {summary['present']}")
    lines.append(f"Absent: {summary['absent']}")
    lines.append(f"Attendance: {summary['attendance_percent']}%")

    if not absentees.empty:
        lines.append("")
        lines.append("Absent Candidates:")
        for _, row in absentees.iterrows():
            cid = row["candidate_id"]
            marker = " (repeat absentee)" if cid in repeat_ids else ""
            remark = f" - Remark: {row['remarks']}" if str(row.get("remarks", "-")) != "-" else ""
            lines.append(f"- Candidate {cid}: {row.get('candidate_name', 'Unknown')}{marker}{remark}")

    report_text = "\n".join(lines)
    return report_text
