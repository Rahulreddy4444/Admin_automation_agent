from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class AdminProfile(BaseModel):
    admin_id: int
    admin_name: str
    admin_email: str
    admin_phone: str
    role: str

class CandidateSchema(BaseModel):
    candidate_id: int
    candidate_name: str
    email: str
    phone: str
    batch_id: str
    status: str
    attendance_percent: Optional[float] = None
    sessions_attended: Optional[int] = None
    sessions_missed: Optional[int] = None
    repeated_absences: Optional[int] = None

class BatchSchema(BaseModel):
    batch_id: str
    batch_name: str
    program_name: str
    start_date: str
    end_date: str
    status: str
    coordinator_name: str
    candidate_count: Optional[int] = None
    attendance_percent: Optional[float] = None
    sessions_completed: Optional[int] = None
    progress_percent: Optional[float] = None

class SessionSchema(BaseModel):
    session_number: int
    planned_date: str
    module: str
    topic_title: str
    subtopics: str
    status: Optional[str] = "Upcoming"

class AttendanceRecordSubmit(BaseModel):
    session_number: int
    batch_id: Optional[str] = "b1"
    absent_candidate_ids: List[int] = []
    remarks: Optional[Dict[int, str]] = {}
    force_resubmit: bool = False

class AttendanceSummary(BaseModel):
    session_number: int
    total: int
    present: int
    absent: int
    attendance_percent: float
    absent_candidates: List[Dict[str, Any]] = []

class TeachingProgressSchema(BaseModel):
    total_planned: int
    completed: int
    remaining: int
    completion_percent: float
    last_completed_session: Optional[int] = None
    attendance_recorded_sessions: int
    attendance_gap: int
    current_topic: Optional[Dict[str, Any]] = None
    next_topic: Optional[Dict[str, Any]] = None

class CommunicationItem(BaseModel):
    communication_id: str
    candidate_id: int
    candidate_name: Optional[str] = None
    session_number: int
    channel: str
    recipient: str
    subject: Optional[str] = None
    message: str
    status: str
    created_at: str
    approved_at: Optional[str] = None
    sent_at: Optional[str] = None
    error: Optional[str] = None

class CommunicationAction(BaseModel):
    action: str  # 'approve', 'reject', 'send'
    subject: Optional[str] = None
    message: Optional[str] = None

class GenerateDraftsRequest(BaseModel):
    session_number: int
    channel: str = "Email"

class AssistantQueryRequest(BaseModel):
    query: str

class AssistantQueryResponse(BaseModel):
    query: str
    response: str
    agent_used: Optional[str] = None
    rag_context: Optional[List[str]] = None

class DashboardData(BaseModel):
    today_session: Optional[SessionSchema] = None
    batch: Optional[BatchSchema] = None
    total_candidates: int
    present_today: Optional[int] = None
    absent_today: Optional[int] = None
    attendance_percent_today: Optional[float] = None
    progress: TeachingProgressSchema
    repeat_absentees: List[Dict[str, Any]] = []
    low_attendance_candidates: List[Dict[str, Any]] = []
    pending_communications_count: int
    schedule_conflicts: List[Dict[str, Any]] = []
    dry_run: bool
