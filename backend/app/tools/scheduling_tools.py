import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from app.services.data_service import data_service
from app.tools.attendance_tools import load_attendance_log

def compare_planned_vs_actual() -> pd.DataFrame:
    log = load_attendance_log()
    teaching_plan = data_service.get_teaching_plan()
    if log.empty or teaching_plan.empty:
        return pd.DataFrame(columns=["session_number", "planned_date", "session_date", "delta_days", "status"])

    actual = log[["session_number", "session_date"]].drop_duplicates()
    merged = actual.merge(
        teaching_plan[["session_number", "planned_date", "module", "topic_title"]], on="session_number"
    )

    def delta(row):
        try:
            p = datetime.strptime(str(row["planned_date"]), "%d-%m-%Y")
            a = datetime.strptime(str(row["session_date"]), "%d-%m-%Y")
            return (a - p).days
        except Exception:
            return 0

    merged["delta_days"] = merged.apply(delta, axis=1)
    merged["status"] = merged["delta_days"].apply(
        lambda d: "On Time" if d == 0 else ("Delayed" if d > 0 else "Early")
    )
    return merged.sort_values("session_number")

def check_schedule_conflicts() -> pd.DataFrame:
    log = load_attendance_log()
    candidates = data_service.get_candidates()
    batches = data_service.get_batches()

    if log.empty or candidates.empty or batches.empty:
        return pd.DataFrame(columns=["session_date", "coordinator_name", "batch_count", "batches"])

    merged = log[["session_number", "session_date", "candidate_id"]].merge(
        candidates[["candidate_id", "batch_id"]], on="candidate_id"
    )[["session_number", "session_date", "batch_id"]].drop_duplicates()
    
    merged = merged.merge(batches[["batch_id", "coordinator_name"]], on="batch_id")

    grouped = merged.groupby(["session_date", "coordinator_name"]).agg(
        batch_count=("batch_id", "nunique"),
        batches=("batch_id", lambda x: sorted(set(x))),
    ).reset_index()

    return grouped[grouped["batch_count"] > 1]
