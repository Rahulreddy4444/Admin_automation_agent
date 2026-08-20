import re
from typing import Dict, Any, Optional
from app.agents.setup import build_agents_and_team
from app.tools.attendance_tools import (
    calculate_session_attendance,
    get_absent_candidates,
    get_repeat_absentees,
    get_low_attendance_candidates
)
from app.tools.progress_tools import (
    get_teaching_progress,
    get_current_topic,
    get_next_topic
)
from app.tools.reporting_tools import generate_daily_report
from app.tools.scheduling_tools import check_schedule_conflicts
from app.rag.retriever import query_knowledge_base
from app.services.data_service import data_service

_team = None
_model_client = None

def get_team():
    global _team, _model_client
    if _team is None:
        _team, _model_client = build_agents_and_team()
    return _team

def fallback_answer_query(question: str) -> Dict[str, Any]:
    """
    Deterministic query router fallback when LLM API is unavailable or rate limited.
    Uses exact same tool and RAG operations.
    """
    q = question.lower().strip()
    
    # 1. Who was absent in session X?
    m_absent = re.search(r"absent.*(?:session|in)\s*(\d+)", q) or re.search(r"session\s*(\d+).*absent", q)
    if m_absent:
        s_num = int(m_absent.group(1))
        try:
            abs_df = get_absent_candidates(s_num)
            if abs_df.empty:
                return {
                    "response": f"No candidates were recorded absent in Session {s_num}.",
                    "agent_used": "Attendance_Agent (Deterministic)",
                    "rag_context": []
                }
            names = [f"{row['candidate_name']} (ID: {row['candidate_id']})" for _, row in abs_df.iterrows()]
            return {
                "response": f"The following candidate(s) were absent in Session {s_num}: {', '.join(names)}.",
                "agent_used": "Attendance_Agent (Deterministic)",
                "rag_context": []
            }
        except Exception as e:
            return {"response": str(e), "agent_used": "Attendance_Agent", "rag_context": []}

    # 2. What is today's topic?
    if "today's topic" in q or "current topic" in q or "topic today" in q:
        curr = get_current_topic()
        if curr:
            return {
                "response": f"Today's current topic is **{curr['topic_title']}** (Session {curr['session_number']}, {curr['module']}).",
                "agent_used": "Progress_Agent (Deterministic)",
                "rag_context": []
            }
        return {"response": "No current topic found in teaching plan.", "agent_used": "Progress_Agent", "rag_context": []}

    # 3. What is the next topic?
    if "next topic" in q or "upcoming topic" in q:
        nxt = get_next_topic()
        if nxt:
            return {
                "response": f"The next upcoming topic is **{nxt['topic_title']}** (Session {nxt['session_number']}, {nxt['module']}).",
                "agent_used": "Progress_Agent (Deterministic)",
                "rag_context": []
            }
        return {"response": "No next topic scheduled.", "agent_used": "Progress_Agent", "rag_context": []}

    # 4. Teaching plan progress
    if "progress" in q or "how far" in q or "completion" in q:
        prog = get_teaching_progress()
        return {
            "response": (
                f"**Teaching Plan Progress:**\n"
                f"- Total planned sessions: {prog['total_planned']}\n"
                f"- Completed sessions: {prog['completed']}\n"
                f"- Remaining sessions: {prog['remaining']}\n"
                f"- Syllabus Completion: {prog['completion_percent']}%\n"
                f"- Recorded attendance sessions: {prog['attendance_recorded_sessions']} (Gap: {prog['attendance_gap']} sessions)"
            ),
            "agent_used": "Progress_Agent (Deterministic)",
            "rag_context": []
        }

    # 5. Repeat absentees / poor attendance
    if "repeat" in q or "poor" in q or "low attendance" in q or "below 75" in q:
        repeats = get_repeat_absentees(2)
        lows = get_low_attendance_candidates(75.0)
        resp = []
        if not repeats.empty:
            r_str = ", ".join([f"{r['candidate_name']} ({r['absences']} absences)" for _, r in repeats.iterrows()])
            resp.append(f"**Repeat Absentees (2+ missed sessions):** {r_str}")
        else:
            resp.append("No repeat absentees detected.")

        if not lows.empty:
            l_str = ", ".join([f"{l['candidate_name']} ({l['attendance_percent']}%)" for _, l in lows.iterrows()])
            resp.append(f"**Low Attendance (< 75%):** {l_str}")
        else:
            resp.append("No candidates with low attendance (< 75%).")

        return {
            "response": "\n\n".join(resp),
            "agent_used": "Attendance_Agent (Deterministic)",
            "rag_context": []
        }

    # 6. Generate report for session X
    m_rep = re.search(r"report.*(?:session|for)\s*(\d+)", q) or re.search(r"session\s*(\d+).*report", q)
    if m_rep or "generate report" in q or "daily report" in q:
        s_num = int(m_rep.group(1)) if m_rep else 67
        try:
            rep = generate_daily_report(s_num)
            return {
                "response": f"```\n{rep}\n```",
                "agent_used": "Reporting_Agent (Deterministic)",
                "rag_context": []
            }
        except Exception as e:
            return {"response": str(e), "agent_used": "Reporting_Agent", "rag_context": []}

    # 7. Semantic RAG fallback for policy / guidelines
    rag_docs = query_knowledge_base(question, n_results=2)
    if rag_docs:
        context_str = "\n\n".join([f"**From Knowledge Base:**\n{d['content']}" for d in rag_docs])
        return {
            "response": context_str,
            "agent_used": "HR_Query_Agent (RAG + ChromaDB)",
            "rag_context": [d['content'] for d in rag_docs]
        }

    return {
        "response": "I can help with attendance statistics, report generation, progress tracking, scheduling conflicts, and curriculum questions.",
        "agent_used": "HR_Query_Agent",
        "rag_context": []
    }

async def ask_coordinator(question: str) -> Dict[str, Any]:
    team = get_team()
    if team is None:
        return fallback_answer_query(question)

    try:
        await team.reset()
        result = await team.run(task=question)
        for msg in reversed(result.messages):
            content = getattr(msg, "content", None)
            source = getattr(msg, "source", "Coordinator_Team")
            if content and content.strip() != "TERMINATE":
                clean_text = content.replace("TERMINATE", "").strip()
                return {
                    "response": clean_text,
                    "agent_used": source,
                    "rag_context": []
                }
        return {"response": "(no response from agent team)", "agent_used": "Coordinator_Team", "rag_context": []}
    except Exception as e:
        print(f"AutoGen team query failed ({e}), using deterministic RAG fallback.")
        return fallback_answer_query(question)
