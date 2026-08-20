import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import streamlit as st
import pandas as pd
from app.tools.attendance_tools import load_attendance_log, calculate_session_attendance, get_absent_candidates
from app.services.data_service import data_service

st.set_page_config(page_title="Attendance History | Admin Automation Agent", page_icon="🕒", layout="wide")

if not st.session_state.get("authenticated", False):
    st.warning("Please sign in from the main page.")
    st.stop()

st.title("🕒 Attendance Logs & History")
st.caption("Inspect past session attendance records, absentee logs, and coordinator remarks")

log = load_attendance_log()

if log.empty:
    st.info("No attendance records logged yet. Go to 'Mark Attendance' to log your first session.")
    st.stop()

tp = data_service.get_teaching_plan()
unique_sessions = sorted(log["session_number"].astype(int).unique(), reverse=True)

# Build overview table
history_rows = []
for s_num in unique_sessions:
    try:
        summary = calculate_session_attendance(s_num)
        topic = "Session"
        p_date = ""
        if not tp.empty:
            match = tp[tp["session_number"] == s_num]
            if not match.empty:
                topic = match.iloc[0].get("topic_title", "Session")
                p_date = match.iloc[0].get("planned_date", "")

        first_row = log[log["session_number"].astype(int) == s_num].iloc[0]
        history_rows.append({
            "Session #": s_num,
            "Date": str(first_row.get("session_date", p_date)),
            "Topic Title": topic,
            "Total Active": summary["total"],
            "Present": summary["present"],
            "Absent": summary["absent"],
            "Attendance %": f"{summary['attendance_percent']}%",
            "Submitted By": str(first_row.get("submitted_by", "Admin")),
            "Submitted At": str(first_row.get("submitted_at", ""))
        })
    except Exception:
        continue

st.dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)

st.markdown("---")

# Drill down inspection
st.subheader("🔍 Inspect Session Attendance Details")
inspect_s_num = st.selectbox("Select Session to Inspect", options=unique_sessions)

if inspect_s_num:
    s_log = log[log["session_number"].astype(int) == int(inspect_s_num)]
    candidates = data_service.get_candidates()
    
    # Ensure candidate_id is string to prevent merge type mismatch
    s_log = s_log.copy()
    s_log["candidate_id"] = s_log["candidate_id"].astype(str)
    
    if not candidates.empty:
        candidates = candidates.copy()
        candidates["candidate_id"] = candidates["candidate_id"].astype(str)
        merged = s_log.merge(
            candidates[["candidate_id", "candidate_name", "email", "phone"]],
            on="candidate_id",
            how="left"
        )
        merged["candidate_name"] = merged["candidate_name"].fillna("Unknown")
    else:
        merged = s_log
        merged["candidate_name"] = "Unknown"
        merged["email"] = ""
        merged["phone"] = "" 

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"**Detailed Roster for Session {inspect_s_num}:**")
        st.dataframe(
            merged[["candidate_id", "candidate_name", "attendance_status", "remarks", "submitted_by", "submitted_at"]],
            use_container_width=True,
            hide_index=True
        )

    with col2:
        abs_df = get_absent_candidates(int(inspect_s_num))
        st.markdown("**Absent Candidates in this Session:**")
        if not abs_df.empty:
            for _, r in abs_df.iterrows():
                st.error(f"❌ **{r['candidate_name']}** (ID: {r['candidate_id']}) — Remark: *{r['remarks']}*")
        else:
            st.success("🎉 All candidates were Present (100% attendance).")
