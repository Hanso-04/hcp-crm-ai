from fastapi import APIRouter
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.graph import AGENT_GRAPH
from app.schemas import ChatRequest, ChatResponse, InteractionDraft

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    initial_state = {
        "messages": [HumanMessage(content=req.message)],
        "draft": req.current_draft.model_dump(),
        "interaction_id": req.interaction_id,
        "voice_note_consent": req.voice_note_consent,
        "changed_fields": [],
        "tool_calls_used": [],
        "hcp_history": None,
    }

    final_state = AGENT_GRAPH.invoke(initial_state)

    # Last AI message with no further tool calls is the assistant's reply to show.
    reply = ""
    for msg in reversed(final_state["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            reply = msg.content
            break

    draft_dict = {k: v for k, v in final_state["draft"].items() if k != "change_log"}

    return ChatResponse(
        reply=reply or "Done.",
        draft=InteractionDraft(**draft_dict),
        changed_fields=final_state.get("changed_fields", []),
        tool_calls=final_state.get("tool_calls_used", []),
        compliance_flag=final_state["draft"].get("compliance_flag", False),
        compliance_notes=final_state["draft"].get("compliance_notes"),
        hcp_history=final_state.get("hcp_history"),
    )
