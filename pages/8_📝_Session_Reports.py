import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import streamlit as st
import pandas as pd
from app.tools.reporting_tools import generate_daily_report
from app.tools.attendance_tools import load_attendance_log
from app.services.data_service import data_service

st.set_page_config(page_title="Session Reports | Admin Automation Agent", page_icon="📝", layout="wide")

if not st.session_state.get("authenticated", False):
    st.warning("Please sign in from the main page.")
    st.stop()

st.title("📝 Automated Session Reports")
st.caption("Daily session reports auto-generated from attendance logs, topic schedules, and absentee analytics")

log = load_attendance_log()
if log.empty:
    st.info("No attendance sessions recorded yet. Please submit attendance for a session first.")
    st.stop()

unique_sessions = sorted(log["session_number"].astype(int).unique(), reverse=True)

col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("Select Session")
    selected_s_num = st.selectbox("Session Number", options=unique_sessions)
    session = data_service.get_session_details(selected_s_num)
    
    st.write(f"**Date:** {session.get('planned_date')}")
    st.write(f"**Topic:** {session.get('topic_title')}")
    st.write(f"**Module:** {session.get('module')}")

with col2:
    st.subheader(f"📄 Report for Session {selected_s_num}")
    report_text = generate_daily_report(selected_s_num)
    
    st.code(report_text, language="text")
    
    # Download report button
    st.download_button(
        label="💾 Download Session Report (.txt)",
        data=report_text,
        file_name=f"Session_{selected_s_num}_Daily_Report.txt",
        mime="text/plain"
    )
