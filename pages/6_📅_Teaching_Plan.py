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
from app.services.data_service import data_service, TEACHING_PLAN_COLUMNS
from app.tools.progress_tools import get_teaching_progress
from app.rag.knowledge_base import ingest_teaching_plan_into_rag

st.set_page_config(page_title="Teaching Plan | Admin Automation Agent", page_icon="📖", layout="wide")

if not st.session_state.get("authenticated", False):
    st.warning("Please sign in from the main page.")
    st.stop()

st.title("📖 Master Curriculum & Teaching Plan")
st.caption("Structured syllabus sessions, topics, subtopics, and dynamic file parser ingestion")

# File Upload Section
with st.expander("📁 Upload / Replace Teaching Plan (Supports .pdf, .xlsx, .csv, .docx, .txt)", expanded=False):
    st.markdown('''
    You can upload a new syllabus or teaching plan file anytime. The system will parse tables or PDF module layouts 
    automatically and synchronize the knowledge base for ChromaDB RAG.
    ''')
    uploaded_file = st.file_uploader(
        "Choose a Teaching Plan file",
        type=["pdf", "xlsx", "xls", "csv", "docx", "txt"]
    )
    
    if uploaded_file is not None:
        if st.button("🚀 Parse and Ingest Plan", type="primary"):
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            try:
                with st.spinner("Parsing teaching plan and indexing vector embeddings..."):
                    df, ok, msg = data_service.parse_and_save_teaching_plan_file(tmp_path)
                    if ok:
                        ingest_teaching_plan_into_rag()
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

st.markdown("---")

# Manual Add Session Section
with st.expander("➕ Add New Session Manually", expanded=False):
    with st.form("add_session_form"):
        col1, col2 = st.columns(2)
        with col1:
            s_num = st.number_input("Session Number", min_value=1, step=1)
            s_date = st.text_input("Planned Date (DD-MM-YYYY)")
            s_mod = st.text_input("Module Name")
        with col2:
            s_title = st.text_input("Topic Title")
            s_sub = st.text_area("Subtopics")
            
        submitted = st.form_submit_button("Add Session")
        if submitted:
            data_service.add_session({
                "session_number": int(s_num),
                "planned_date": s_date,
                "module": s_mod,
                "topic_title": s_title,
                "subtopics": s_sub
            })
            st.success(f"Added Session {s_num}!")
            ingest_teaching_plan_into_rag()
            st.rerun()

st.markdown("---")

tp = data_service.get_teaching_plan()
if tp.empty:
    st.info("No teaching plan loaded. Upload a file above or add a session manually.")
else:
    st.subheader("Edit / Manage Sessions")
    st.write("Edit cells directly and click 'Save Changes', or select rows to delete.")
    
    edit_df = tp.copy()
    select_all = st.checkbox("Select All for Deletion", key="tp_select_all")
    edit_df.insert(0, "Delete", select_all)
    
    edited_df = st.data_editor(
        edit_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "session_number": st.column_config.NumberColumn("Session No.", disabled=True),
            "Delete": st.column_config.CheckboxColumn("Delete?", default=False)
        }
    )
    
    if st.button("💾 Save Changes", type="primary"):
        rows_to_delete = edited_df[edited_df["Delete"] == True]["session_number"].tolist()
        final_df = edited_df[edited_df["Delete"] == False].drop(columns=["Delete"])
        
        if final_df.empty or len(rows_to_delete) == len(tp):
            data_service.save_teaching_plan(pd.DataFrame(columns=TEACHING_PLAN_COLUMNS))
            data_service.clean_orphan_logs()
            ingest_teaching_plan_into_rag()
            st.success("All sessions deleted from Teaching Plan successfully!")
            st.rerun()
            
        merged_df = tp.copy()
        for _, row in final_df.iterrows():
            s_num = row["session_number"]
            idx = merged_df.index[merged_df["session_number"] == s_num]
            if not idx.empty:
                for col in final_df.columns:
                    merged_df.loc[idx, col] = row[col]
                    
        if rows_to_delete:
            merged_df = merged_df[~merged_df["session_number"].isin(rows_to_delete)]
            data_service.delete_sessions(rows_to_delete)
            
        data_service.save_teaching_plan(merged_df)
        st.success("Teaching Plan saved successfully!")
        ingest_teaching_plan_into_rag()
        st.rerun()

st.markdown("---")

st.subheader("Session Status View")
if tp.empty:
    st.info("No curriculum sessions available.")
else:
    progress = get_teaching_progress()
    last_completed = progress.get("last_completed_session")
    today_session = data_service.get_today_session()
    today_num = today_session.get("session_number") if today_session else None

    # Filter and search
    search_query = st.text_input("🔍 Search Topic, Module, or Subtopics", "")
    status_filter = st.selectbox("Filter by Status", ["All", "Completed", "Today's Session", "Upcoming"])

    display_rows = []
    for _, row in tp.iterrows():
        s_num = int(row["session_number"])
        status = "Upcoming"
        if today_num and s_num == today_num:
            status = "Today's Session"
        elif last_completed and s_num <= last_completed:
            status = "Completed"

        if status_filter != "All" and status != status_filter:
            continue

        if search_query.strip():
            q = search_query.lower()
            if (q not in str(row["topic_title"]).lower() and 
                q not in str(row["module"]).lower() and 
                q not in str(row["subtopics"]).lower() and
                q not in str(s_num)):
                continue

        r_dict = row.to_dict()
        r_dict["status"] = status
        display_rows.append(r_dict)

    st.write(f"Showing **{len(display_rows)}** of **{len(tp)}** sessions:")

    if display_rows:
        df_display = pd.DataFrame(display_rows)
        st.dataframe(
            df_display[["session_number", "planned_date", "status", "module", "topic_title", "subtopics"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No sessions match the current search filter.")
