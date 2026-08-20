import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import streamlit as st
import pandas as pd
from app.config import settings
from app.tools.communication_tools import (
    load_comm_log,
    approve_and_send_communication,
    reject_communication,
    auto_generate_drafts_for_absentees
)
from app.services.data_service import data_service
from app.tools.attendance_tools import load_attendance_log

st.set_page_config(page_title="Communication Center | Admin Automation Agent", page_icon="💬", layout="wide")

if not st.session_state.get("authenticated", False):
    st.warning("Please sign in from the main page.")
    st.stop()

st.title("💬 Communication Center & Approval Gate")
st.caption("Human-in-the-Loop Step 2: Review, edit, and authorize outbound emails and WhatsApp notifications")

if settings.DRY_RUN:
    st.warning("🛡️ **DRY_RUN Mode Active**: Messages will be logged and approved safely without sending real outbound emails/WhatsApp messages.")
else:
    st.info("🚀 **Live Dispatch Mode**: Approving a draft will trigger immediate delivery via Gmail SMTP / Twilio.")

comm_log = load_comm_log()

# Section 1: Pending Approvals
st.subheader("📬 Messages Awaiting Your Approval")

pending_df = comm_log[comm_log["status"].astype(str).str.upper() == "PENDING_APPROVAL"] if not comm_log.empty else pd.DataFrame()

if not pending_df.empty:
    candidates = data_service.get_candidates()
    if not candidates.empty:
        pending_df = pending_df.merge(candidates[["candidate_id", "candidate_name"]], on="candidate_id", how="left")

    for _, row in pending_df.iterrows():
        comm_id = row["communication_id"]
        cid = row["candidate_id"]
        cname = row.get("candidate_name", f"Candidate {cid}")
        channel = row["channel"]
        recipient = row["recipient"]
        subject = row.get("subject", "")
        body = row["message"]
        s_num = row["session_number"]

        with st.container():
            st.markdown(f"""
            <div style="background:#111827; border:1px solid #4B5563; padding:18px; border-radius:12px; margin-bottom:16px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="color:#A78BFA; font-weight:700; font-size:1.1rem;">Draft for {cname} (ID: {cid})</span>
                    <span style="background:#374151; color:#F3F4F6; padding:3px 10px; border-radius:9999px; font-size:0.8rem;">
                        Channel: <b>{channel}</b> | Session: <b>{s_num}</b>
                    </span>
                </div>
                <p style="color:#9CA3AF; margin:6px 0 0 0; font-size:0.85rem;">Recipient: <b>{recipient}</b></p>
            </div>
            """, unsafe_allow_html=True)

            # Editable subject & body
            with st.expander(f"📝 Preview / Edit Draft ({comm_id})", expanded=True):
                new_subject = subject
                if channel == "Email":
                    new_subject = st.text_input("Subject Line", value=subject, key=f"subj_{comm_id}")
                new_body = st.text_area("Message Content", value=body, height=140, key=f"body_{comm_id}")

                col_act1, col_act2, col_act3 = st.columns([1, 1, 4])
                
                with col_act1:
                    if st.button(f"✅ Approve & Send", key=f"app_{comm_id}", type="primary"):
                        res = approve_and_send_communication(comm_id, edited_subject=new_subject, edited_message=new_body)
                        st.success(f"Message {comm_id} approved and processed: {res['status']}.")
                        st.rerun()

                with col_act2:
                    if st.button(f"❌ Reject", key=f"rej_{comm_id}"):
                        res = reject_communication(comm_id)
                        st.info(f"Message {comm_id} marked as REJECTED.")
                        st.rerun()

else:
    st.success("🎉 No pending drafts. All outbound communications have been reviewed.")

# Section 2: Generate Drafts Manually for a session
st.markdown("---")
with st.expander("➕ Generate Absence Outreach Drafts for a Specific Session"):
    att_log = load_attendance_log()
    if not att_log.empty:
        recorded_sessions = sorted(att_log["session_number"].astype(int).unique(), reverse=True)
        gen_s_num = st.selectbox("Select Session Number", options=recorded_sessions, key="gen_s_num")
        gen_channel = st.radio("Channel", ["Email", "WhatsApp"], horizontal=True, key="gen_chan")
        
        if st.button("Generate Absentee Drafts"):
            drafts = auto_generate_drafts_for_absentees(int(gen_s_num), channel=gen_channel)
            if drafts:
                st.success(f"Generated {len(drafts)} draft(s) for Session {gen_s_num}.")
                st.rerun()
            else:
                st.info("No new absentees to draft messages for (or already drafted).")

# Section 3: Audit Trail Log
st.markdown("---")
st.subheader("📜 Communication Audit Trail Log")
if not comm_log.empty:
    st.dataframe(
        comm_log[["communication_id", "candidate_id", "session_number", "channel", "recipient", "status", "created_at", "approved_at", "error"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No communication attempts logged yet.")
