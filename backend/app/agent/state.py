from typing import Annotated, Optional, List
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # Full chat history for this turn (system + human + AI + tool messages).
    # `add_messages` reducer appends rather than overwrites on each graph step.
    messages: Annotated[list, add_messages]

    # The structured record currently on screen. Tools read/write this dict
    # directly — it's the single source of truth the form is bound to.
    draft: dict

    interaction_id: Optional[int]
    voice_note_consent: bool

    # Populated by tools so the API layer can tell the frontend what to
    # highlight / show, without re-parsing the message history.
    changed_fields: List[str]
    tool_calls_used: List[str]
    hcp_history: Optional[list]
