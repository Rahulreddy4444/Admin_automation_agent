import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import streamlit as st
import pandas as pd
from app.services.data_service import data_service
from app.tools.attendance_tools import (
    get_active_candidates,
    record_daily_absences,
    calculate_session_attendance,
    load_attendance_log
)
from app.tools.reporting_tools import generate_daily_report
from app.tools.communication_tools import auto_generate_drafts_for_absentees

st.set_page_config(page_title="Mark Attendance | Admin Automation Agent", page_icon="✍️", layout="wide")

if not st.session_state.get("authenticated", False):
    st.warning("Please sign in from the main page.")
    st.stop()

st.title("✍️ Daily Attendance Submission")
st.caption("Human-in-the-Loop Step 1: Select only the absent candidates for today's session")

# Auto-resolve session
tp = data_service.get_teaching_plan()
if tp.empty:
    st.warning("No teaching plan found. Please upload or add sessions from the Teaching Plan page first.")
    st.stop()

batches = data_service.get_batches()
if batches.empty:
    st.warning("No batches found. Please create a batch from the Batches page first.")
    st.stop()

today_session = data_service.get_today_session()
default_session_num = today_session["session_number"] if today_session else int(tp["session_number"].min())

# Session & Batch Selectors
col_s1, col_s2, col_s3 = st.columns([1, 1, 2])

with col_s1:
    session_num = st.selectbox(
        "Select Session Number",
        options=sorted(tp["session_number"].astype(int).unique()),
        index=sorted(tp["session_number"].astype(int).unique()).index(int(default_session_num)) if int(default_session_num) in tp["session_number"].astype(int).values else 0
    )

with col_s2:
    batch_options = batches["batch_id"].tolist()
    selected_batch = st.selectbox(
        "Select Batch",
        options=batch_options,
        format_func=lambda bid: f"{bid} ({batches[batches['batch_id']==bid].iloc[0]['batch_name']})"
    )

selected_session = data_service.get_session_details(session_num)

with col_s3:
    st.markdown(f'''
    <div style="background:#111827; border:1px solid #374151; padding:16px; border-radius:10px;">
        <div style="display:flex; justify-content:space-between;">
            <b style="color:#A78BFA; font-size:1.1rem;">Session {selected_session['session_number']}: {selected_session['topic_title']}</b>
            <span style="color:#9CA3AF;">Planned Date: <b>{selected_session['planned_date']}</b></span>
        </div>
        <p style="color:#D1D5DB; margin:6px 0 0 0; font-size:0.9rem;"><b>Module:</b> {selected_session['module']}</p>
        <p style="color:#9CA3AF; margin:4px 0 0 0; font-size:0.85rem;"><b>Subtopics:</b> {selected_session.get('subtopics', 'N/A')}</p>
    </div>
    ''', unsafe_allow_html=True)

st.markdown("---")

# Active Candidates for Selected Batch
active_candidates = get_active_candidates(batch_id=selected_batch)
if active_candidates.empty:
    st.warning(f"No active candidates found in batch {selected_batch}. Please add candidates to this batch first.")
    st.stop()

st.subheader(f"👥 Select Absent Candidates (Batch {selected_batch})")
st.caption(f"Batch {selected_batch} has {len(active_candidates)} active candidates. Check the box ONLY for candidates who were absent today.")

# Check if attendance is already recorded
att_log = load_attendance_log()
already_recorded = not att_log.empty and (att_log["session_number"].astype(int) == int(session_num)).any()

if already_recorded:
    st.warning(f"⚠️ Attendance for Session {session_num} is already recorded in the system. Submitting again will update the record.")

# Candidate checkbox grid
selected_absent_ids = []
remarks_dict = {}

col_cand, col_rem = st.columns([1.5, 1.5])

with col_cand:
    st.markdown("<b>Candidate Roster:</b>", unsafe_allow_html=True)
    for _, cand in active_candidates.iterrows():
        cid = int(cand["candidate_id"])
        cname = cand["candidate_name"]
        cemail = cand["email"]
        
        is_absent = st.checkbox(
            f"**Candidate {cid}:** {cname} ({cemail})",
            key=f"absent_{cid}"
        )
        if is_absent:
            selected_absent_ids.append(cid)

with col_rem:
    if selected_absent_ids:
        st.markdown("<b>Optional Absence Remarks:</b>", unsafe_allow_html=True)
        for cid in selected_absent_ids:
            c_name = active_candidates[active_candidates["candidate_id"] == cid].iloc[0]["candidate_name"]
            remark = st.text_input(
                f"Remark for {c_name} (ID: {cid})",
                placeholder="e.g. Informed coordinator regarding medical emergency",
                key=f"remark_{cid}"
            )
            if remark.strip():
                remarks_dict[cid] = remark.strip()
    else:
        st.info("No candidates selected as absent (100% Present).")

st.markdown("---")

# Summary preview calculation
total_active = len(active_candidates)
absent_count = len(selected_absent_ids)
present_count = total_active - absent_count
attendance_pct = round(present_count / total_active * 100, 2) if total_active else 0.0

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Total Active", total_active)
with m2:
    st.metric("Calculated Present", present_count)
with m3:
    st.metric("Selected Absent", absent_count)
with m4:
    st.metric("Calculated Attendance %", f"{attendance_pct}%")

# Submit button
col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    submit_btn = st.button("🚀 Submit Attendance", type="primary", use_container_width=True)

if submit_btn:
    try:
        admin_name = st.session_state.user.get("name", "Admin")
        
        # 1. Deterministic Python attendance recording
        summary = record_daily_absences(
            session_number=int(session_num),
            session_date=str(selected_session["planned_date"]),
            batch_id=selected_batch,
            absent_ids=selected_absent_ids,
            remarks=remarks_dict,
            submitted_by=admin_name,
            force_resubmit=True
        )

        st.success(f"✅ Attendance recorded for Session {session_num}: {summary['present']} Present, {summary['absent']} Absent ({summary['attendance_percent']}%).")

        # 2. Auto-generate Daily Report
        daily_report = generate_daily_report(int(session_num))
        
        # 3. Auto-draft communication messages for absentees
        email_drafts = auto_generate_drafts_for_absentees(int(session_num), channel="Email")
        whatsapp_drafts = auto_generate_drafts_for_absentees(int(session_num), channel="WhatsApp")
        
        st.info(f"📨 Auto-generated {len(email_drafts)} email draft(s) and {len(whatsapp_drafts)} WhatsApp draft(s) for absentees awaiting your approval.")

        with st.expander("📄 View Auto-Generated Daily Report", expanded=True):
            st.code(daily_report, language="text")

    except Exception as e:
        st.error(f"Error submitting attendance: {e}")
