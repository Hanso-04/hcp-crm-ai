from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class InteractionDraft(BaseModel):
    """The structured record the AI assistant proposes / edits.
    This mirrors the left-hand form fields in the UI 1:1."""

    hcp_name: Optional[str] = None
    interaction_type: Optional[str] = None
    interaction_date: Optional[str] = None
    interaction_time: Optional[str] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[str] = None
    sentiment: Optional[str] = None
    compliance_flag: Optional[bool] = False
    compliance_notes: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    # The form's current state, so multi-turn edits know what already exists.
    current_draft: InteractionDraft = InteractionDraft()
    interaction_id: Optional[int] = None
    # Required for the voice-note summarizer tool (PHI/consent handling).
    voice_note_consent: bool = False


class ChatResponse(BaseModel):
    reply: str
    draft: InteractionDraft
    # Which top-level fields the agent just changed, so the UI can highlight them.
    changed_fields: List[str] = []
    tool_calls: List[str] = []
    compliance_flag: bool = False
    compliance_notes: Optional[str] = None
    hcp_history: Optional[List[Dict[str, Any]]] = None


class InteractionOut(InteractionDraft):
    id: int

    class Config:
        from_attributes = True


class ConfirmInteractionRequest(BaseModel):
    draft: InteractionDraft
    interaction_id: Optional[int] = None
