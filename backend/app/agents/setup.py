import os
from typing import Optional, List, Dict, Any
from app.config import settings

# Import tool implementations
from app.tools.attendance_tools import (
    calculate_session_attendance,
    get_absent_candidates,
    get_candidate_attendance_history,
    get_repeat_absentees,
    get_low_attendance_candidates,
)
from app.tools.reporting_tools import generate_daily_report
from app.tools.progress_tools import (
    get_teaching_progress,
    get_current_topic,
    get_next_topic,
)
from app.tools.scheduling_tools import (
    compare_planned_vs_actual,
    check_schedule_conflicts,
)
from app.tools.communication_tools import (
    generate_email_draft,
    generate_whatsapp_draft,
)
from app.services.data_service import data_service
from app.rag.retriever import query_knowledge_base

# Tool wrappers matching notebook signatures exactly
def tool_get_session_details(session_number: int) -> dict:
    """Get the module/topic/subtopics for a specific session number from the teaching plan."""
    row = data_service.get_session_details(int(session_number))
    return {
        "session_number": int(row["session_number"]),
        "planned_date": str(row.get("planned_date", "")),
        "module": str(row.get("module", "")),
        "topic_title": str(row.get("topic_title", "")),
        "subtopics": str(row.get("subtopics", ""))
    }

def tool_calculate_session_attendance(session_number: int) -> dict:
    """Get present/absent counts and attendance percentage for a session. Numbers are computed, never estimated."""
    return calculate_session_attendance(int(session_number))

def tool_get_absent_candidates(session_number: int) -> list:
    """Get the list of absent candidates (id, name, remarks) for a session number."""
    return get_absent_candidates(int(session_number)).to_dict("records")

def tool_get_candidate_attendance_history(candidate_id: str) -> dict:
    """Get a specific candidate's full attendance history and percentage."""
    return get_candidate_attendance_history(candidate_id)

def tool_get_repeat_absentees(threshold: int = 2) -> list:
    """Get candidates absent `threshold` times or more."""
    return get_repeat_absentees(threshold).to_dict("records")

def tool_get_low_attendance_candidates(threshold_pct: float = 75.0) -> list:
    """Get candidates whose attendance percentage is below `threshold_pct`."""
    return get_low_attendance_candidates(threshold_pct).to_dict("records")

def tool_generate_daily_report(session_number: int) -> str:
    """Generate the full formatted daily session report as text."""
    return generate_daily_report(int(session_number))

def tool_get_teaching_progress() -> dict:
    """Get overall training progress: completed/remaining sessions and completion percentage."""
    return get_teaching_progress()

def tool_get_current_topic() -> dict:
    """Get the module/topic of the most recently completed session."""
    return get_current_topic() or {"message": "No sessions completed yet."}

def tool_get_next_topic() -> dict:
    """Get the module/topic of the next upcoming session."""
    return get_next_topic() or {"message": "No further sessions in the plan, or plan complete."}

def tool_compare_planned_vs_actual() -> list:
    """Compare planned vs actual session dates to flag delayed/on-time/early sessions."""
    return compare_planned_vs_actual().to_dict("records")

def tool_check_schedule_conflicts() -> list:
    """Check for coordinator scheduling conflicts across batches on the same date."""
    return check_schedule_conflicts().to_dict("records")

def tool_generate_email_draft(candidate_id: str, session_number: int) -> dict:
    """Generate an email draft for an absent candidate. Does NOT send it."""
    return generate_email_draft(candidate_id, int(session_number))

def tool_generate_whatsapp_draft(candidate_id: str, session_number: int) -> dict:
    """Generate a WhatsApp draft for an absent candidate. Does NOT send it."""
    return generate_whatsapp_draft(candidate_id, int(session_number))

def tool_query_knowledge_base(query: str) -> list:
    """Query the program documentation, policies, and curriculum using semantic RAG."""
    return query_knowledge_base(query, n_results=3)

COMMON_RULE = (
    "You NEVER perform attendance, percentage, or date-arithmetic calculations yourself. "
    "You always call your tool functions for any number, and report exactly what they return -- "
    "never estimate, round differently, or recompute a figure. "
    "When you have fully answered the request, end your message with the word TERMINATE."
)

def build_agents_and_team():
    groq_api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if not groq_api_key or groq_api_key.startswith("gsk_your"):
        return None, None

    try:
        from autogen_core.models import ModelFamily
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.teams import SelectorGroupChat
        from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination

        model_client = OpenAIChatCompletionClient(
            model=settings.GROQ_MODEL,
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_api_key,
            model_info={
                "vision": False,
                "function_calling": True,
                "json_output": True,
                "family": ModelFamily.UNKNOWN,
                "structured_output": False,
            },
        )

        Attendance_Agent = AssistantAgent(
            name="Attendance_Agent",
            model_client=model_client,
            tools=[
                tool_calculate_session_attendance,
                tool_get_absent_candidates,
                tool_get_candidate_attendance_history,
                tool_get_repeat_absentees,
                tool_get_low_attendance_candidates
            ],
            description="Answers questions about attendance: present/absent counts, percentages, "
                        "repeat absentees, low-attendance candidates, individual candidate history.",
            system_message="You analyze attendance data using your tools. " + COMMON_RULE,
        )

        Reporting_Agent = AssistantAgent(
            name="Reporting_Agent",
            model_client=model_client,
            tools=[tool_generate_daily_report, tool_get_session_details],
            description="Generates the full daily session report and session details (module/topic).",
            system_message="You generate daily session reports using your tools. " + COMMON_RULE,
        )

        Progress_Agent = AssistantAgent(
            name="Progress_Agent",
            model_client=model_client,
            tools=[tool_get_teaching_progress, tool_get_current_topic, tool_get_next_topic],
            description="Answers questions about teaching-plan progress: completed/remaining sessions, "
                        "current topic, next topic, completion percentage.",
            system_message="You track teaching-plan progress using your tools. " + COMMON_RULE,
        )

        Scheduling_Agent = AssistantAgent(
            name="Scheduling_Agent",
            model_client=model_client,
            tools=[tool_compare_planned_vs_actual, tool_check_schedule_conflicts],
            description="Answers questions about schedule deviations (delayed/on-time sessions) and "
                        "coordinator scheduling conflicts across batches.",
            system_message="You detect schedule deviations and conflicts using your tools. " + COMMON_RULE,
        )

        HR_Query_Agent = AssistantAgent(
            name="HR_Query_Agent",
            model_client=model_client,
            tools=[
                tool_calculate_session_attendance,
                tool_get_absent_candidates,
                tool_get_repeat_absentees,
                tool_get_low_attendance_candidates,
                tool_get_teaching_progress,
                tool_get_current_topic,
                tool_get_next_topic,
                tool_compare_planned_vs_actual,
                tool_check_schedule_conflicts,
                tool_generate_daily_report,
                tool_query_knowledge_base
            ],
            description="General-purpose fallback for broad natural-language coordinator questions, "
                        "policy queries, and curriculum documentation.",
            system_message="You answer general coordinator questions by calling the appropriate tools "
                            "and synthesizing a clear answer. " + COMMON_RULE,
        )

        Communication_Agent = AssistantAgent(
            name="Communication_Agent",
            model_client=model_client,
            tools=[tool_generate_email_draft, tool_generate_whatsapp_draft],
            description="Drafts absence-notification messages for candidates. Never sends messages.",
            system_message=(
                "You draft absence-notification messages using your tools. You NEVER send a message "
                "yourself -- drafting and sending are separate steps, and sending only happens after "
                "explicit human approval outside this chat. " + COMMON_RULE
            ),
        )

        termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(10)
        team = SelectorGroupChat(
            participants=[
                Attendance_Agent,
                Reporting_Agent,
                Progress_Agent,
                Scheduling_Agent,
                HR_Query_Agent,
                Communication_Agent
            ],
            model_client=model_client,
            termination_condition=termination,
        )

        return team, model_client
    except Exception as e:
        print(f"Failed to initialize AutoGen team: {e}")
        return None, None
