from fastapi import APIRouter
from typing import Dict, Any
from app.tools.progress_tools import (
    get_teaching_progress,
    get_current_topic,
    get_next_topic
)
from app.tools.scheduling_tools import compare_planned_vs_actual, check_schedule_conflicts

router = APIRouter(prefix="/progress", tags=["Progress"])

@router.get("", response_model=Dict[str, Any])
async def get_progress_overview():
    progress = get_teaching_progress()
    curr = get_current_topic()
    nxt = get_next_topic()
    pva = compare_planned_vs_actual()
    conflicts = check_schedule_conflicts()

    return {
        "progress": progress,
        "current_topic": curr,
        "next_topic": nxt,
        "schedule_deviations": pva.to_dict("records") if not pva.empty else [],
        "schedule_conflicts": conflicts.to_dict("records") if not conflicts.empty else []
    }
