import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import streamlit as st
import pandas as pd
import plotly.express as px
from app.tools.progress_tools import (
    get_teaching_progress,
    get_current_topic,
    get_next_topic
)
from app.tools.scheduling_tools import compare_planned_vs_actual
from app.services.data_service import data_service

st.set_page_config(page_title="Curriculum Progress | Admin Automation Agent", page_icon="📈", layout="wide")

if not st.session_state.get("authenticated", False):
    st.warning("Please sign in from the main page.")
    st.stop()

st.title("📈 Curriculum Progress & Schedule Tracking")
st.caption("Deterministic calendar-based progress, syllabus velocity, and schedule deviations")

progress = get_teaching_progress()
curr = get_current_topic()
nxt = get_next_topic()

# Top metrics
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Planned Sessions", progress["total_planned"])
with c2:
    st.metric("Completed (Calendar)", progress["completed"])
with c3:
    st.metric("Remaining Sessions", progress["remaining"])
with c4:
    st.metric("Syllabus Completion %", f"{progress['completion_percent']}%")

st.markdown("---")

col1, col2 = st.columns([1.5, 1])

with col1:
    st.subheader("🎯 Active Topic Status")
    if curr:
        st.markdown(f"""
        <div style="background:#111827; border:1px solid #374151; padding:16px; border-radius:10px; margin-bottom:12px;">
            <span style="background:#1E3A8A; color:#60A5FA; padding:2px 8px; border-radius:9999px; font-weight:600; font-size:0.8rem;">Current Active Topic</span>
            <h3 style="margin:8px 0 4px 0; color:#F3F4F6;">Session {curr['session_number']}: {curr['topic_title']}</h3>
            <p style="color:#C4B5FD; margin:0 0 8px 0; font-size:0.9rem;">{curr['module']}</p>
            <p style="color:#9CA3AF; margin:0; font-size:0.85rem;"><b>Key Subtopics:</b> {curr.get('subtopics', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No completed sessions yet.")

    if nxt:
        st.markdown(f"""
        <div style="background:#111827; border:1px solid #374151; padding:16px; border-radius:10px;">
            <span style="background:#374151; color:#D1D5DB; padding:2px 8px; border-radius:9999px; font-weight:600; font-size:0.8rem;">Next Upcoming Session</span>
            <h4 style="margin:8px 0 4px 0; color:#F3F4F6;">Session {nxt['session_number']}: {nxt['topic_title']}</h4>
            <p style="color:#9CA3AF; margin:0; font-size:0.85rem;">{nxt['module']}</p>
        </div>
        """, unsafe_allow_html=True)

    if progress["attendance_gap"] > 0:
        st.warning(f"⚠️ **Attendance Backfill Note**: {progress['attendance_gap']} calendar sessions have no attendance logged yet ({progress['attendance_recorded_sessions']}/{progress['completed']} logged). You can backfill these via Mark Attendance.")

with col2:
    st.subheader("📊 Syllabus Velocity")
    fig = px.bar(
        x=["Completed", "Remaining"],
        y=[progress["completed"], progress["remaining"]],
        color=["Completed", "Remaining"],
        color_discrete_map={"Completed": "#8B5CF6", "Remaining": "#374151"},
        labels={"x": "Status", "y": "Number of Sessions"}
    )
    fig.update_layout(
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F3F4F6")
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("⏱️ Schedule Deviations (Planned vs. Actual Dates)")
pva = compare_planned_vs_actual()
if not pva.empty:
    st.dataframe(
        pva[["session_number", "planned_date", "session_date", "delta_days", "status", "topic_title"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No recorded sessions to compare against planned dates.")
