import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.rag.knowledge_base import ensure_knowledge_base_seeded

# API Routers
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.sessions import router as sessions_router
from app.api.attendance import router as attendance_router
from app.api.candidates import router as candidates_router
from app.api.batches import router as batches_router
from app.api.teaching_plan import router as teaching_plan_router
from app.api.progress import router as progress_router
from app.api.reports import router as reports_router
from app.api.communications import router as communications_router
from app.api.assistant import router as assistant_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_knowledge_base_seeded()
    except Exception as e:
        print(f"Knowledge base seed warning: {e}")

    yield
    # Shutdown logic if needed

app = FastAPI(
    title="Admin Automation Agent API",
    description="Agentic AI Coordinator Assistant Backend powered by AutoGen AG2, ChromaDB RAG, and FastAPI",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend (Vite default port 5173 and others)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(attendance_router, prefix="/api")
app.include_router(candidates_router, prefix="/api")
app.include_router(batches_router, prefix="/api")
app.include_router(teaching_plan_router, prefix="/api")
app.include_router(progress_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(communications_router, prefix="/api")
app.include_router(assistant_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Admin Automation Agent API",
        "autogen_enabled": True,
        "dry_run": settings.DRY_RUN
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
