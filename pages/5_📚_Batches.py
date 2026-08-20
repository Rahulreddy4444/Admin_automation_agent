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
from app.tools.progress_tools import get_teaching_progress

st.set_page_config(page_title="Batches | Admin Automation Agent", page_icon="🏫", layout="wide")

if not st.session_state.get("authenticated", False):
    st.warning("Please sign in from the main page.")
    st.stop()

st.title("🏫 Batch Management")
st.caption("Manage batches, coordinator allocations, and roster enrollment")

# File Upload Section
with st.expander("📁 Bulk Upload / Replace Batches (Supports .csv, .xlsx, .pdf, .docx, .txt)", expanded=False):
    st.markdown("Upload a file to parse and add multiple batches at once.")
    uploaded_file = st.file_uploader("Choose a Batches file", type=["csv", "xlsx", "xls", "pdf", "docx", "txt"])
    
    if uploaded_file is not None:
        if st.button("🚀 Parse Batches File", type="primary"):
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            try:
                with st.spinner("Parsing file..."):
                    df, ok, msg = data_service.parse_batches_file(tmp_path)
                    if ok:
                        st.session_state["parsed_batches"] = df
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    if "parsed_batches" in st.session_state:
        st.write("Preview:")
        st.dataframe(st.session_state["parsed_batches"], use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Append Batches"):
                combined = pd.concat([data_service.get_batches(), st.session_state["parsed_batches"]], ignore_index=True)
                data_service.save_batches(combined)
                del st.session_state["parsed_batches"]
                st.success("Appended successfully!")
                st.rerun()
        with col2:
            if st.button("Replace All Batches"):
                data_service.save_batches(st.session_state["parsed_batches"])
                del st.session_state["parsed_batches"]
                st.success("Replaced successfully!")
                st.rerun()

st.markdown("---")

# Manual Add Batch Section
with st.expander("➕ Add New Batch Manually", expanded=False):
    with st.form("add_batch_form"):
        col1, col2 = st.columns(2)
        with col1:
            b_id = st.text_input("Batch ID (e.g., b2)")
            b_name = st.text_input("Batch Name")
            b_prog = st.text_input("Program Name")
        with col2:
            b_coord = st.text_input("Coordinator Name")
            b_start = st.date_input("Start Date")
            b_end = st.date_input("End Date")
            b_status = st.selectbox("Status", ["Active", "Completed", "Upcoming"])
            
        submitted = st.form_submit_button("Add Batch")
        if submitted:
            if not b_id or not b_name:
                st.error("Batch ID and Name are required.")
            else:
                data_service.add_batch({
                    "batch_id": b_id,
                    "batch_name": b_name,
                    "program_name": b_prog,
                    "start_date": b_start.strftime("%Y-%m-%d"),
                    "end_date": b_end.strftime("%Y-%m-%d"),
                    "status": b_status,
                    "coordinator_name": b_coord
                })
                st.success(f"Added batch {b_name}!")
                st.rerun()

st.markdown("---")

batches = data_service.get_batches()
if batches.empty:
    st.info("No batch records found.")
else:
    st.subheader("Edit / Manage Batches")
    st.write("Edit cells directly and click 'Save Changes', or select rows to delete.")
    
    edit_df = batches.copy()
    select_all = st.checkbox("Select All for Deletion", key="batch_select_all")
    edit_df.insert(0, "Delete", select_all)
    
    edited_df = st.data_editor(
        edit_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "status": st.column_config.SelectboxColumn("Status", options=["Active", "Completed", "Upcoming"]),
            "Delete": st.column_config.CheckboxColumn("Delete?", default=False)
        }
    )
    
    if st.button("💾 Save Changes", type="primary"):
        rows_to_delete = edited_df[edited_df["Delete"] == True]["batch_id"].tolist()
        final_df = edited_df[edited_df["Delete"] == False].drop(columns=["Delete"])
        
        merged_df = batches.copy()
        for _, row in final_df.iterrows():
            bid = row["batch_id"]
            idx = merged_df.index[merged_df["batch_id"] == bid]
            if not idx.empty:
                for col in final_df.columns:
                    merged_df.loc[idx, col] = row[col]
                    
        if rows_to_delete:
            merged_df = merged_df[~merged_df["batch_id"].isin(rows_to_delete)]
            data_service.delete_batches(rows_to_delete)
            
        data_service.save_batches(merged_df)
        st.success("Batch changes saved successfully!")
        st.rerun()

st.markdown("---")

# Batch Overviews
st.subheader("🏫 Batch Dashboards")
candidates = data_service.get_candidates()
progress = get_teaching_progress()

for _, batch in batches.iterrows():
    bid = str(batch["batch_id"])
    c_in_batch = candidates[candidates["batch_id"].astype(str) == bid]
    
    st.markdown(f'''
    <div style="background:#111827; border:1px solid #374151; padding:20px; border-radius:12px; margin-bottom:16px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3 style="margin:0; color:#A78BFA;">{batch['batch_name']} <span style="font-size:0.85rem; color:#9CA3AF;">(ID: {batch['batch_id']})</span></h3>
            <span style="background:#064E3B; color:#34D399; padding:4px 10px; border-radius:9999px; font-weight:600; font-size:0.85rem;">{batch['status']}</span>
        </div>
        <p style="color:#D1D5DB; margin:8px 0;"><b>Program:</b> {batch['program_name']} | <b>Coordinator:</b> {batch['coordinator_name']}</p>
        <p style="color:#9CA3AF; margin:0 0 12px 0;"><b>Dates:</b> {batch['start_date']} &rarr; {batch['end_date']}</p>
    </div>
    ''', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Enrolled Candidates", len(c_in_batch))
    with c2:
        # Simplistic assumption: progress applies to all batches, ideally it should be per batch
        st.metric("Sessions Completed", f"{progress['completed']} / {progress['total_planned']}")
    with c3:
        st.metric("Curriculum Completion", f"{progress['completion_percent']}%")
        
    with st.expander(f"👥 Enrolled Candidates in {batch['batch_name']}", expanded=False):
        if not c_in_batch.empty:
            st.dataframe(
                c_in_batch[["candidate_id", "candidate_name", "email", "phone", "status"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No candidates assigned to this batch.")
