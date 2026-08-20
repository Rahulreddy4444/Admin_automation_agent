import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import streamlit as st
import pandas as pd
import plotly.express as px
from app.config import settings
from app.services.data_service import data_service, CANDIDATE_COLUMNS
from app.tools.progress_tools import get_teaching_progress, get_current_topic, get_next_topic
from app.tools.attendance_tools import (
    calculate_session_attendance,
    get_repeat_absentees,
    get_low_attendance_candidates,
    load_attendance_log
)
from app.tools.scheduling_tools import check_schedule_conflicts
from app.tools.communication_tools import load_comm_log

st.set_page_config(page_title="Dashboard | Admin Automation Agent", page_icon="📊", layout="wide")

if not st.session_state.get("authenticated", False):
    st.warning("Please sign in from the main page.")
    st.stop()

st.title("📊 Coordinator Operations Dashboard")
st.caption("Real-time operational health, curriculum tracking, and absentee alerts")

# Top metrics
progress = get_teaching_progress()
candidates = data_service.get_candidates()
active_cands = candidates[candidates["status"].astype(str).str.title() == "Active"] if not candidates.empty else pd.DataFrame(columns=CANDIDATE_COLUMNS)
log = load_attendance_log()

latest_session_num = None
summary = None
if not log.empty and not active_cands.empty:
    try:
        latest_session_num = int(log["session_number"].astype(int).max())
        summary = calculate_session_attendance(latest_session_num)
    except Exception:
        summary = None

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Active Candidates", len(active_cands))
with c2:
    if summary:
        st.metric(
            f"Latest Attendance (Session {latest_session_num})",
            f"{summary['attendance_percent']}%",
            f"{summary['present']} Present / {summary['absent']} Absent"
        )
    else:
        st.metric("Latest Attendance", "No records yet")
with c3:
    if progress["total_planned"] > 0:
        st.metric("Syllabus Completion", f"{progress['completion_percent']}%", f"{progress['remaining']} sessions remaining")
    else:
        st.metric("Syllabus Completion", "0.0%", "0 sessions loaded")
with c4:
    comm_log = load_comm_log()
    pending = len(comm_log[comm_log["status"].astype(str).str.upper() == "PENDING_APPROVAL"]) if not comm_log.empty else 0
    st.metric("Pending Approvals", pending, delta="Action required" if pending > 0 else "All cleared", delta_color="inverse")

st.markdown("---")

# Middle row: Today's Session & Progress Chart
col1, col2 = st.columns([1.2, 1])

with col1:
    st.subheader("📍 Active Session Information")
    curr_topic = get_current_topic()
    nxt_topic = get_next_topic()
    
    if curr_topic and progress["total_planned"] > 0:
        st.success(f"**Current Topic (Session {curr_topic['session_number']}):** {curr_topic['topic_title']}")
        st.write(f"**Module:** {curr_topic['module']}")
        if curr_topic.get("subtopics"):
            st.caption(f"**Key Concepts:** {curr_topic['subtopics']}")
    else:
        st.info("No active curriculum sessions. Upload a teaching plan to track sessions.")

    if nxt_topic and progress["total_planned"] > 0:
        st.info(f"**Next Upcoming (Session {nxt_topic['session_number']}):** {nxt_topic['topic_title']}")
    
    batches = data_service.get_batches()
    if not batches.empty:
        b = batches.iloc[0]
        st.write(f"**Active Batch:** {b['batch_name']} | **Coordinator:** {b['coordinator_name']} | **Status:** {b['status']}")
    else:
        st.caption("No batches registered yet.")

with col2:
    st.subheader("📈 Curriculum Completion")
    if progress["total_planned"] > 0:
        fig = px.pie(
            names=["Completed Sessions", "Remaining Sessions"],
            values=[progress["completed"], progress["remaining"]],
            color_discrete_sequence=["#8B5CF6", "#1F2937"],
            hole=0.6
        )
        fig.update_layout(
            showlegend=True,
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#F3F4F6")
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No curriculum sessions loaded to visualize completion.")

st.markdown("---")

# Bottom row: Repeat Absentees, Low Attendance & Conflicts
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("⚠️ Repeated Absentees (2+ missed)")
    if not active_cands.empty:
        repeats_df = get_repeat_absentees(threshold=2)
        if not repeats_df.empty:
            st.dataframe(
                repeats_df[["candidate_id", "candidate_name", "absences"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ No repeated absentees detected across recorded sessions.")
    else:
        st.info("No active candidates in system.")

    st.subheader("📉 Low Attendance (< 75%)")
    if not active_cands.empty:
        low_df = get_low_attendance_candidates(threshold_pct=75.0)
        if not low_df.empty:
            st.dataframe(
                low_df[["candidate_id", "candidate_name", "attendance_percent"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ All active candidates have attendance ≥ 75%.")
    else:
        st.info("No active candidates in system.")

with col_b:
    st.subheader("🗓️ Scheduling Conflict Detection")
    conflicts_df = check_schedule_conflicts()
    if not conflicts_df.empty:
        st.error("⚠️ Scheduling conflicts detected for coordinator across batches:")
        st.dataframe(conflicts_df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No coordinator or batch scheduling conflicts detected.")

    st.subheader("🛡️ Safety & Execution Mode")
    if settings.DRY_RUN:
        st.warning("⚠️ **DRY_RUN is ENABLED**: Outbound emails and WhatsApp dispatches are safely simulated. No external messages will be sent.")
    else:
        st.info("🚀 **LIVE DISPATCH ENABLED**: Approved communications will be dispatched through Gmail SMTP and Twilio WhatsApp.")
