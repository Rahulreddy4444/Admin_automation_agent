from fastapi import APIRouter, HTTPException
from app.schemas import AssistantQueryRequest, AssistantQueryResponse
from app.agents.coordinator import ask_coordinator

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])

@router.post("/query", response_model=AssistantQueryResponse)
async def query_assistant(req: AssistantQueryRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    result = await ask_coordinator(req.query.strip())

    return {
        "query": req.query,
        "response": result.get("response", "(No response)"),
        "agent_used": result.get("agent_used", "Coordinator_Team"),
        "rag_context": result.get("rag_context", [])
    }
