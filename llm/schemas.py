from typing import Optional
from pydantic import BaseModel


class IncidentAnalysis(BaseModel):
    root_cause: str
    evidence: str
    confidence: int  # 0-100
    severity: str    # P1-P4
    fix_steps: list[str]
    auto_fixable: bool
    auto_fix_action: Optional[str] = None
    estimated_fix_minutes: int
    safety_notes: str
    escalate_if: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []
    follow_up_suggestions: list[str] = []
