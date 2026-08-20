import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import settings
from app.services.data_service import data_service

ATTENDANCE_CSV = os.path.join(settings.DATA_DIR, "attendance.csv")
ATTENDANCE_COLUMNS = [
    "attendance_id", "session_number", "session_date", "candidate_id",
    "attendance_status", "remarks", "submitted_by", "submitted_at"
]

def get_active_candidates(candidates_df: Optional[pd.DataFrame] = None, batch_id: Optional[str] = None) -> pd.DataFrame:
    if candidates_df is None:
        candidates_df = data_service.get_candidates()
    active = candidates_df[candidates_df["status"].astype(str).str.strip().str.title() == "Active"]
    if batch_id is not None:
        active = active[active["batch_id"].astype(str) == str(batch_id)]
    return active

def validate_candidate_ids(ids: List[int], candidates_df: Optional[pd.DataFrame] = None) -> List[int]:
    """Returns the subset of ids that do NOT exist in candidates_df."""
    if candidates_df is None:
        candidates_df = data_service.get_candidates()
    valid_ids = set(candidates_df["candidate_id"].tolist())
    return [i for i in ids if i not in valid_ids]

def load_attendance_log() -> pd.DataFrame:
    if os.path.exists(ATTENDANCE_CSV):
        try:
            return pd.read_csv(ATTENDANCE_CSV, dtype={"session_number": int})
        except Exception:
            return pd.read_csv(ATTENDANCE_CSV)
    return pd.DataFrame(columns=ATTENDANCE_COLUMNS)

def _next_attendance_id(existing_log: pd.DataFrame) -> int:
    if existing_log.empty or "attendance_id" not in existing_log.columns:
        return 1
    nums = existing_log["attendance_id"].astype(str).str.extract(r"A(\d+)").dropna().astype(int)
    if nums.empty:
        return 1
    return int(nums.max().iloc[0]) + 1

def record_daily_absences(
    session_number: int,
    session_date: str,
    batch_id: str,
    absent_ids: List[int],
    remarks: Optional[Dict[int, str]] = None,
    submitted_by: str = "Admin",
    force_resubmit: bool = False
) -> Dict[str, Any]:
    """
    Admin provides ONLY absent_ids. Present candidates are derived automatically as
    (active candidates in batch) - (absentees). Writes one row per active candidate to the
    normalized attendance.csv log.
    """
    remarks = remarks or {}
    candidates = data_service.get_candidates()
    active = get_active_candidates(candidates, batch_id)

    # Cast absent_ids to int matching candidate_id
    clean_absent_ids = []
    for x in absent_ids:
        try:
            clean_absent_ids.append(int(x))
        except ValueError:
            clean_absent_ids.append(x)

    invalid = validate_candidate_ids(clean_absent_ids, candidates)
    if invalid:
        raise ValueError(f"Unknown candidate_id(s), not found in roster: {invalid}")

    not_in_batch = set(clean_absent_ids) - set(active["candidate_id"].tolist())
    if not_in_batch:
        raise ValueError(f"candidate_id(s) not active in batch {batch_id}: {sorted(not_in_batch)}")

    existing_log = load_attendance_log()
    already_recorded = existing_log[existing_log["session_number"].astype(int) == int(session_number)]

    if not already_recorded.empty and not force_resubmit:
        raise ValueError(
            f"Attendance for session {session_number} was already submitted "
            f"({len(already_recorded)} records). Pass force_resubmit=True to overwrite."
        )

    if force_resubmit and not already_recorded.empty:
        existing_log = existing_log[existing_log["session_number"].astype(int) != int(session_number)]

    next_id = _next_attendance_id(existing_log)
    now = datetime.now().isoformat(timespec="seconds")
    new_rows = []
    
    for _, cand in active.iterrows():
        cid = cand["candidate_id"]
        status = "Absent" if cid in clean_absent_ids else "Present"
        remark_val = remarks.get(cid) or remarks.get(str(cid)) or "-"
        new_rows.append({
            "attendance_id": f"A{str(next_id).zfill(3)}",
            "session_number": int(session_number),
            "session_date": str(session_date),
            "candidate_id": cid,
            "attendance_status": status,
            "remarks": remark_val,
            "submitted_by": submitted_by,
            "submitted_at": now,
        })
        next_id += 1

    new_log = pd.concat([existing_log, pd.DataFrame(new_rows)], ignore_index=True)
    new_log.to_csv(ATTENDANCE_CSV, index=False)
    
    summary = calculate_session_attendance(session_number)
    return summary

def calculate_session_attendance(session_number: int) -> Dict[str, Any]:
    """Deterministic present/absent/percentage calculation — no LLM."""
    log = load_attendance_log()
    session_log = log[log["session_number"].astype(int) == int(session_number)]
    if session_log.empty:
        raise ValueError(f"No attendance recorded yet for session {session_number}")

    total = len(session_log)
    present = int((session_log["attendance_status"] == "Present").sum())
    absent = int((session_log["attendance_status"] == "Absent").sum())
    pct = round(present / total * 100, 2) if total else 0.0

    return {
        "session_number": int(session_number),
        "total": total,
        "present": present,
        "absent": absent,
        "attendance_percent": pct,
    }

def get_absent_candidates(session_number: int) -> pd.DataFrame:
    log = load_attendance_log()
    candidates = data_service.get_candidates()
    session_log = log[(log["session_number"].astype(int) == int(session_number)) &
                       (log["attendance_status"] == "Absent")]
    if session_log.empty:
        return pd.DataFrame(columns=["candidate_id", "candidate_name", "remarks"])
    session_log = session_log.copy()
    session_log["candidate_id"] = session_log["candidate_id"].astype(str)
    candidates = candidates.copy()
    candidates["candidate_id"] = candidates["candidate_id"].astype(str)
    
    merged = session_log[["candidate_id", "remarks"]].merge(
        candidates[["candidate_id", "candidate_name"]], on="candidate_id", how="left"
    )
    merged["candidate_name"] = merged["candidate_name"].fillna("Unknown")
    return merged

def get_candidate_attendance_history(candidate_id: int) -> Dict[str, Any]:
    log = load_attendance_log()
    try:
        cid = int(candidate_id)
    except ValueError:
        cid = candidate_id
        
    hist = log[log["candidate_id"].astype(str) == str(cid)]
    total = len(hist)
    present = int((hist["attendance_status"] == "Present").sum())
    absent = total - present
    pct = round(present / total * 100, 2) if total else 0.0
    return {
        "candidate_id": cid,
        "sessions_recorded": total,
        "present": present,
        "absent": absent,
        "attendance_percent": pct,
    }

def get_repeat_absentees(threshold: int = 2) -> pd.DataFrame:
    log = load_attendance_log()
    candidates = data_service.get_candidates()
    if log.empty:
        return pd.DataFrame(columns=["candidate_id", "absences", "candidate_name"])
    counts = log[log["attendance_status"] == "Absent"].groupby("candidate_id").size()
    repeat = counts[counts >= threshold].reset_index(name="absences")
    if repeat.empty:
        return pd.DataFrame(columns=["candidate_id", "absences", "candidate_name"])
    return repeat.merge(candidates[["candidate_id", "candidate_name"]], on="candidate_id") \
                 .sort_values("absences", ascending=False)

def get_low_attendance_candidates(threshold_pct: float = 75.0) -> pd.DataFrame:
    log = load_attendance_log()
    candidates = data_service.get_candidates()
    if log.empty:
        return pd.DataFrame(columns=["candidate_id", "attendance_percent", "candidate_name"])
    stats = log.groupby("candidate_id")["attendance_status"].apply(
        lambda s: round((s == "Present").sum() / len(s) * 100, 2)
    ).reset_index(name="attendance_percent")
    low = stats[stats["attendance_percent"] < threshold_pct]
    if low.empty:
        return pd.DataFrame(columns=["candidate_id", "attendance_percent", "candidate_name"])
    return low.merge(candidates[["candidate_id", "candidate_name"]], on="candidate_id") \
              .sort_values("attendance_percent")
