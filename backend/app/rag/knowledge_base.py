import os
from typing import List, Dict, Any
from app.rag.chroma_client import get_knowledge_collection
from app.services.data_service import data_service

POLICY_DOCUMENTS = [
    {
        "id": "policy_attendance",
        "title": "Attendance and Punctuality Policy",
        "content": (
            "Attendance Policy: Candidates must maintain a minimum attendance rate of 75% to be eligible "
            "for graduation and placement assistance. Candidates absent for 2 or more consecutive sessions "
            "will be flagged as repeat absentees and receive automated coordinator outreach. "
            "If absent due to medical or unavoidable personal reasons, candidates must notify their coordinator "
            "prior to the session to register an excused absence."
        ),
        "source": "HR & Program Guidelines"
    },
    {
        "id": "policy_evaluations",
        "title": "Curriculum Evaluation and Capstone Guidelines",
        "content": (
            "Program Evaluation Guidelines: The Agentic AI curriculum consists of 97 rigorous sessions spanning "
            "Prompt Engineering, Multi-Agent Architectures, Tool Calling, and Deployment. Periodic evaluations occur "
            "at the end of each module. A final Capstone Project is required where candidates demonstrate "
            "production multi-agent workflows."
        ),
        "source": "Curriculum Handbook"
    },
    {
        "id": "policy_pwd_support",
        "title": "PWD Coordinator Accessibility Support",
        "content": (
            "Accessibility & Support Framework: The Admin Automation Agent is designed to reduce coordinator toil "
            "by automating routine reporting, absentee tracking, and conflict detection. Coordinators retain full "
            "human-in-the-loop control for attendance entry and final message approval before sending emails or WhatsApp notifications."
        ),
        "source": "Accessibility Standards"
    }
]

def ingest_teaching_plan_into_rag():
    collection = get_knowledge_collection()
    tp = data_service.get_teaching_plan()
    if tp.empty:
        try:
            # Delete any existing session docs if teaching plan is empty
            all_ids = collection.get()["ids"]
            session_ids = [i for i in all_ids if i.startswith("session_")]
            if session_ids:
                collection.delete(ids=session_ids)
        except Exception:
            pass
        return

    documents = []
    metadatas = []
    ids = []

    for _, row in tp.iterrows():
        s_num = int(row["session_number"])
        doc_id = f"session_{s_num}"
        content = (
            f"Session {s_num} (Planned Date: {row.get('planned_date')})\n"
            f"Module: {row.get('module')}\n"
            f"Topic: {row.get('topic_title')}\n"
            f"Sub-topics: {row.get('subtopics')}"
        )
        documents.append(content)
        metadatas.append({
            "type": "teaching_plan",
            "session_number": s_num,
            "topic": str(row.get("topic_title")),
            "module": str(row.get("module"))
        })
        ids.append(doc_id)

    # Also add standard policies
    for p in POLICY_DOCUMENTS:
        documents.append(f"{p['title']}\n{p['content']}")
        metadatas.append({
            "type": "policy",
            "title": p["title"],
            "source": p["source"]
        })
        ids.append(p["id"])

    # Upsert into ChromaDB
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"Ingested {len(documents)} documents into ChromaDB knowledge base.")

def ensure_knowledge_base_seeded():
    collection = get_knowledge_collection()
    if collection.count() == 0:
        ingest_teaching_plan_into_rag()
