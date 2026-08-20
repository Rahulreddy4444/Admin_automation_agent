import sys
import asyncio
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import streamlit as st
from app.agents.coordinator import ask_coordinator
from app.config import settings

st.set_page_config(page_title="AI Coordinator Assistant | Admin Automation Agent", page_icon="🤖", layout="wide")

if not st.session_state.get("authenticated", False):
    st.warning("Please sign in from the main page.")
    st.stop()

st.title("🤖 AI Coordinator Assistant")
st.caption("Powered by AutoGen AG2 multi-agent team (SelectorGroupChat) & ChromaDB RAG semantic retrieval")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 Hello! I am your Coordinator Assistant. I coordinate an AutoGen multi-agent team "
                "(Attendance, Reporting, Progress, Scheduling, and Communication agents) and connect to "
                "the ChromaDB knowledge base to answer operational and policy questions.\n\n"
                "**Try asking me:**\n"
                "- *Who was absent in session 67?*\n"
                "- *What is today's topic?*\n"
                "- *How far are we through the teaching plan?*\n"
                "- *Which candidates have poor attendance (< 75%)?*\n"
                "- *What does the attendance policy say?*\n"
                "- *Are there any schedule conflicts?*"
            ),
            "agent_used": "Coordinator_Team"
        }
    ]

# Display existing messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("agent_used") and msg["role"] == "assistant":
            st.caption(f"🤖 Resolved by: **{msg['agent_used']}**")

# Prompt input
if prompt := st.chat_input("Ask a question about candidates, attendance, progress, or policies..."):
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process query
    with st.chat_message("assistant"):
        with st.spinner("AutoGen agents analyzing tools and retrieving knowledge..."):
            try:
                # Run async coordinator query
                result = asyncio.run(ask_coordinator(prompt))
                response_text = result.get("response", "(No response)")
                agent_name = result.get("agent_used", "Coordinator_Team")
                
                st.markdown(response_text)
                st.caption(f"🤖 Resolved by: **{agent_name}**")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "agent_used": agent_name
                })
            except Exception as e:
                st.error(f"Query execution error: {e}")
