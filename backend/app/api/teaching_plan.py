import os
import shutil
import tempfile
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import List, Dict, Any
from app.services.data_service import data_service
from app.tools.progress_tools import get_teaching_progress
from app.rag.knowledge_base import ingest_teaching_plan_into_rag
from app.core.dependencies import get_current_admin

router = APIRouter(prefix="/teaching-plan", tags=["Teaching Plan"])

@router.get("", response_model=List[Dict[str, Any]])
async def get_teaching_plan_endpoint():
    tp = data_service.get_teaching_plan()
    if tp.empty:
        return []

    progress = get_teaching_progress()
    last_completed = progress.get("last_completed_session")
    today_session = data_service.get_today_session()
    today_num = today_session.get("session_number") if today_session else None

    result = []
    for _, row in tp.iterrows():
        s_num = int(row["session_number"])
        status = "Upcoming"
        if today_num and s_num == today_num:
            status = "Today's Session"
        elif last_completed and s_num <= last_completed:
            status = "Completed"

        r_dict = row.to_dict()
        r_dict["status"] = status
        result.append(r_dict)

    return result

@router.post("/upload")
async def upload_teaching_plan(
    file: UploadFile = File(...),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Accepts any file type (.pdf, .xlsx, .xls, .csv, .docx, .txt) and parses it
    into the master teaching plan, updating ChromaDB knowledge base automatically.
    """
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    allowed = [".pdf", ".xlsx", ".xls", ".csv", ".docx", ".txt"]
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed formats: {', '.join(allowed)}"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        df, ok, msg = data_service.parse_and_save_teaching_plan_file(tmp_path)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)

        # Ingest parsed teaching plan into ChromaDB for semantic RAG
        try:
            ingest_teaching_plan_into_rag()
        except Exception as e:
            print(f"RAG ingestion warning after plan upload: {e}")

        return {
            "success": True,
            "message": msg,
            "total_sessions": len(df)
        }
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
