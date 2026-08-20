import sys
import os
import tempfile
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import streamlit as st
import pandas as pd
from app.services.data_service import data_service
from app.tools.attendance_tools import get_candidate_attendance_history, load_attendance_log
from app.tools.communication_tools import load_comm_log

st.set_page_config(page_title="Candidates | Admin Automation Agent", page_icon="👥", layout="wide")

if not st.session_state.get("authenticated", False):
    st.warning("Please sign in from the main page.")
    st.stop()

st.title("👥 Candidate Management")
st.caption("Master roster, individual attendance tracking, communication audit history, and data management")

# File Upload Section
with st.expander("📁 Bulk Upload / Replace Candidates (Supports .csv, .xlsx, .pdf, .docx, .txt)", expanded=False):
    st.markdown("Upload a file to parse and add multiple candidates at once.")
    uploaded_file = st.file_uploader("Choose a Candidates file", type=["csv", "xlsx", "xls", "pdf", "docx", "txt"])
    
    if uploaded_file is not None:
        if st.button("🚀 Parse File", type="primary"):
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            try:
                with st.spinner("Parsing file..."):
                    df, ok, msg = data_service.parse_candidates_file(tmp_path)
                    if ok:
                        st.session_state["parsed_candidates"] = df
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    if "parsed_candidates" in st.session_state:
        st.write("Preview:")
        st.dataframe(st.session_state["parsed_candidates"], use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Append to Existing"):
                combined = pd.concat([data_service.get_candidates(), st.session_state["parsed_candidates"]], ignore_index=True)
                data_service.save_candidates(combined)
                del st.session_state["parsed_candidates"]
                st.success("Appended successfully!")
                st.rerun()
        with col2:
            if st.button("Replace All Existing"):
                data_service.save_candidates(st.session_state["parsed_candidates"])
                del st.session_state["parsed_candidates"]
                st.success("Replaced successfully!")
                st.rerun()

st.markdown("---")

batches = data_service.get_batches()
batch_options = batches["batch_id"].tolist() if not batches.empty else []

# Manual Add Candidate Section
with st.expander("➕ Add New Candidate Manually", expanded=False):
    with st.form("add_candidate_form"):
        col1, col2 = st.columns(2)
        with col1:
            c_name = st.text_input("Candidate Name")
            c_email = st.text_input("Email")
        with col2:
            c_phone = st.text_input("Phone")
            c_batch = st.selectbox("Batch ID", options=batch_options)
        c_status = st.selectbox("Status", ["Active", "Inactive", "Dropped"])
        
        submitted = st.form_submit_button("Add Candidate")
        if submitted:
            if not c_name or not c_email:
                st.error("Name and Email are required.")
            else:
                data_service.add_candidate({
                    "candidate_name": c_name,
                    "email": c_email,
                    "phone": c_phone,
                    "batch_id": c_batch,
                    "status": c_status
                })
                st.success(f"Added {c_name}!")
                st.rerun()

st.markdown("---")

candidates = data_service.get_candidates()
if candidates.empty:
    st.info("No candidate records found.")
else:
    # Filter / Search
    search_term = st.text_input("🔍 Search Candidates by Name, ID, or Email", "")
    if search_term.strip():
        mask = (
            candidates["candidate_name"].astype(str).str.contains(search_term, case=False) |
            candidates["candidate_id"].astype(str).str.contains(search_term, case=False) |
            candidates["email"].astype(str).str.contains(search_term, case=False)
        )
        display_df = candidates[mask]
    else:
        display_df = candidates

    st.subheader("Edit / Manage Candidates")
    st.write("Edit cells directly and click 'Save Changes', or select rows to delete.")
    
    # Add a 'Delete' column
    edit_df = display_df.copy()
    select_all = st.checkbox("Select All for Deletion", key="cand_select_all")
    edit_df.insert(0, "Delete", select_all)
    
    edited_df = st.data_editor(
        edit_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "candidate_id": st.column_config.NumberColumn("ID", disabled=True),
            "batch_id": st.column_config.SelectboxColumn("Batch", options=batch_options),
            "status": st.column_config.SelectboxColumn("Status", options=["Active", "Inactive", "Dropped"]),
            "Delete": st.column_config.CheckboxColumn("Delete?", default=False)
        }
    )
    
    if st.button("💾 Save Changes", type="primary"):
        # Process deletions
        rows_to_delete = edited_df[edited_df["Delete"] == True]["candidate_id"].tolist()
        final_df = edited_df[edited_df["Delete"] == False].drop(columns=["Delete"])
        
        # Merge edits back into the main candidates dataframe
        # Since we might have filtered, we update only the matching rows
        merged_df = candidates.copy()
        for _, row in final_df.iterrows():
            cid = row["candidate_id"]
            idx = merged_df.index[merged_df["candidate_id"] == cid]
            if not idx.empty:
                for col in final_df.columns:
                    merged_df.loc[idx, col] = row[col]
                    
        # Apply deletions
        if rows_to_delete:
            # We filter it out from merged_df for immediate consistency,
            # but we use data_service.delete_candidates to perform the cascade save.
            merged_df = merged_df[~merged_df["candidate_id"].isin(rows_to_delete)]
            data_service.delete_candidates(rows_to_delete)
            
        data_service.save_candidates(merged_df)
        st.success("Changes saved successfully!")
        st.rerun()

st.markdown("---")

# Candidate Profile Drilldown
if not candidates.empty:
    st.subheader("🔍 Candidate Profile & History")
    selected_cid = st.selectbox(
        "Select Candidate to View Profile",
        options=candidates["candidate_id"].tolist(),
        format_func=lambda cid: f"Candidate {cid}: {candidates[candidates['candidate_id']==cid].iloc[0]['candidate_name']}"
    )

    if selected_cid:
        cand_info = candidates[candidates["candidate_id"] == selected_cid].iloc[0]
        stats = get_candidate_attendance_history(selected_cid)
        
        col1, col2, col3 = st.columns([1, 1.5, 1.5])
        
        with col1:
            st.markdown(f'''
            <div style="background:#111827; border:1px solid #374151; padding:16px; border-radius:10px;">
                <h4 style="margin:0; color:#A78BFA;">Candidate Profile</h4>
                <p><b>Name:</b> {cand_info['candidate_name']}</p>
                <p><b>ID:</b> {cand_info['candidate_id']}</p>
                <p><b>Email:</b> {cand_info['email']}</p>
                <p><b>Phone:</b> {cand_info['phone']}</p>
                <p><b>Batch:</b> {cand_info['batch_id']}</p>
                <p><b>Status:</b> {cand_info['status']}</p>
                <hr style="border-color:#374151;">
                <p><b>Attendance:</b> {stats['attendance_percent'] if stats['attendance_percent'] else 0}%</p>
                <p><b>Present:</b> {stats['present']} | <b>Absent:</b> {stats['absent']}</p>
            </div>
            ''', unsafe_allow_html=True)

        with col2:
            st.markdown("**Session Attendance Record:**")
            att_log = load_attendance_log()
            c_att = att_log[att_log["candidate_id"].astype(str) == str(selected_cid)]
            if not c_att.empty:
                st.dataframe(
                    c_att[["session_number", "session_date", "attendance_status", "remarks", "submitted_at"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No session attendance logged for this candidate yet.")

        with col3:
            st.markdown("**Outreach & Communication History:**")
            comm_log = load_comm_log()
            c_comm = comm_log[comm_log["candidate_id"].astype(str) == str(selected_cid)]
            if not c_comm.empty:
                st.dataframe(
                    c_comm[["session_number", "channel", "status", "created_at", "approved_at"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No communications drafted or sent for this candidate.")
