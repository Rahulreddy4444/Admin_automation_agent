import sys
import os
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
from backend.app.config import settings
from backend.app.services.data_service import data_service
from backend.app.rag.knowledge_base import ensure_knowledge_base_seeded
from backend.app.tools.progress_tools import get_teaching_progress, get_current_topic, get_next_topic
from backend.app.tools.attendance_tools import load_attendance_log, calculate_session_attendance
from backend.app.tools.communication_tools import load_comm_log

# Page configuration
st.set_page_config(
    page_title="Admin Automation Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for rich UI styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4C1D95 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(76, 29, 149, 0.3);
        border: 1px solid rgba(139, 92, 246, 0.3);
    }
    
    .glass-card {
        background: #111827;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        margin-bottom: 16px;
    }
    
    .stat-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    
    .badge-success { background: #064e3b; color: #34d399; }
    .badge-warning { background: #78350f; color: #fbbf24; }
    .badge-danger { background: #7f1d1d; color: #f87171; }
    .badge-info { background: #1e3a8a; color: #60a5fa; }
    
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# Startup bootstrap
try:
    ensure_knowledge_base_seeded()
except Exception as e:
    pass

# Session State for Authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None

def login_form():
    st.markdown("""
    <div class="main-header" style="text-align: center;">
        <h1 style="margin:0; font-size: 2.2rem;">⚡ Admin Automation Agent</h1>
        <p style="margin:8px 0 0 0; color: #C4B5FD; font-size: 1.05rem;">
            Agentic AI Coordinator Workspace — AutoGen AG2, ChromaDB RAG, and Human-in-the-Loop Safeguards
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("🔐 Coordinator Login")
            st.caption("Sign in with your coordinator email to manage batch operations.")
            
            admin_df = data_service.get_admin_details()
            default_email = admin_df.iloc[0]["admin_email"] if not admin_df.empty else "admin@example.com"
            
            email = st.text_input("Email Address", value=default_email)
            password = st.text_input("Password", type="password", value=settings.ADMIN_DEFAULT_PASSWORD)
            
            if st.button("Sign In to Dashboard", type="primary", use_container_width=True):
                is_admin = False
                matched_name = "Coordinator"
                
                if not admin_df.empty:
                    m = admin_df[admin_df["admin_email"].astype(str).str.lower() == email.strip().lower()]
                    if not m.empty:
                        is_admin = True
                        matched_name = m.iloc[0]["admin_name"]
                
                if is_admin or email.strip().lower() in ["admin@example.com", "vinod@gmail.com"]:
                    if password == settings.ADMIN_DEFAULT_PASSWORD:
                        st.session_state.authenticated = True
                        st.session_state.user = {
                            "name": matched_name,
                            "email": email.strip(),
                            "role": "admin"
                        }
                        st.success(f"Welcome back, {matched_name}!")
                        st.rerun()
                    else:
                        st.error("Invalid password.")
                else:
                    st.error("Coordinator email not recognized.")
            st.markdown('</div>', unsafe_allow_html=True)

# Main Authentication Router
if not st.session_state.authenticated:
    login_form()
else:
    # Sidebar Profile & Navigation Info
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['name']}")
        st.caption(f"Role: Coordinator | {st.session_state.user['email']}")
        
        # System indicators
        if settings.DRY_RUN:
            st.markdown('<span class="stat-badge badge-warning">🛡️ DRY_RUN Active</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="stat-badge badge-success">🚀 Live Dispatch Mode</span>', unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

    # Welcome landing page
    st.markdown(f"""
    <div class="main-header">
        <h1 style="margin:0; font-size: 2rem;">Welcome, {st.session_state.user['name']} 👋</h1>
        <p style="margin:8px 0 0 0; color: #E0E7FF; font-size: 1rem;">
            Your agentic coordinator assistant is active. Use the navigation sidebar on the left to mark attendance, review AI drafts, inspect curriculum progress, or chat with the AutoGen team.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Key metrics row
    candidates_df = data_service.get_candidates()
    batches_df = data_service.get_batches()
    progress = get_teaching_progress()
    comm_log = load_comm_log()
    pending_comms = len(comm_log[comm_log["status"].astype(str).str.upper() == "PENDING_APPROVAL"]) if not comm_log.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Candidates", len(candidates_df), help="Active roster in batch b1")
    with c2:
        st.metric("Active Batches", len(batches_df), help="Current training batches")
    with c3:
        st.metric("Syllabus Progress", f"{progress['completion_percent']}%", f"{progress['completed']}/{progress['total_planned']} sessions")
    with c4:
        st.metric("Pending Approvals", pending_comms, help="AI-generated drafts awaiting your review")

    st.markdown("---")
    
    col_left, col_right = st.columns([1.6, 1])
    
    with col_left:
        st.subheader("📌 Today's Auto-Detected Session")
        today_session = data_service.get_today_session()
        curr_topic = get_current_topic()
        
        display_session = today_session if today_session else (
            data_service.get_session_details(curr_topic["session_number"]) if (curr_topic and progress["total_planned"] > 0) else None
        )
        
        if display_session:
            st.markdown(f"""
            <div class="glass-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="stat-badge badge-info">Session {display_session['session_number']}</span>
                    <span style="color:#9CA3AF; font-size:0.85rem;">Planned Date: <b>{display_session['planned_date']}</b></span>
                </div>
                <h3 style="margin:12px 0 6px 0; color:#F3F4F6;">{display_session['topic_title']}</h3>
                <p style="color:#C4B5FD; margin:0 0 10px 0; font-size:0.9rem;">{display_session['module']}</p>
                <div style="background:#1F2937; padding:10px 14px; border-radius:8px; font-size:0.85rem; color:#D1D5DB;">
                    <b>Subtopics:</b> {display_session.get('subtopics', 'N/A')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No session scheduled for today.")

    with col_right:
        st.subheader("⚡ Quick Navigation")
        st.markdown("""
        <div class="glass-card">
            <p><b>Recommended Coordinator Daily Flow:</b></p>
            <ol style="padding-left: 20px; line-height: 1.8; color: #D1D5DB;">
                <li>Open <b>2_✍️_Mark_Attendance</b> to log today's absentees</li>
                <li>System automatically generates the report and drafts</li>
                <li>Go to <b>9_💬_Communication_Center</b> to review & approve</li>
                <li>Ask any natural language questions in <b>10_🤖_AI_Assistant</b></li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
