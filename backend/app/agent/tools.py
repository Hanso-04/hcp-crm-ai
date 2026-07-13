"""
Five LangGraph tools for the Log HCP Interaction agent.

  1. log_interaction              (required by brief)
  2. edit_interaction             (required by brief — targeted patch, not a re-log)
  3. fetch_hcp_history            (chosen: makes the agent context-aware, not single-turn)
  4. compliance_sentiment_flag    (chosen: pharma-compliance domain relevance)
  5. summarize_voice_note         (chosen: consent-gated, mirrors the reference UI mock)

Design rule the whole file follows: **the AI is the only writer of the draft.**
Every tool that changes the record returns a `Command(update=...)` that patches
LangGraph state directly — there is no code path where the FastAPI layer or the
React form can mutate `draft` without going through one of these tools first.
"""

import json
import re
from typing import Annotated, Optional

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from app.agent.llm import get_llm
from app.agent.state import AgentState
from app.database import SessionLocal
from app.models import Interaction

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _call_llm_json(prompt: str) -> dict:
    """Call the Groq model and coerce its reply into a dict.

    gemma2-9b-it doesn't reliably support strict JSON-mode, so we ask for JSON
    in the prompt and defensively extract the first {...} block from the
    response rather than trusting response_format.
    """
    llm = get_llm(temperature=0.0)
    resp = llm.invoke(prompt)
    text = resp.content if hasattr(resp, "content") else str(resp)
    match = _JSON_BLOCK.search(text)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


FIELD_LIST = (
    "hcp_name, interaction_type (Meeting/Call/Email/Conference), "
    "interaction_date (YYYY-MM-DD), interaction_time (HH:MM AM/PM), "
    "attendees, topics_discussed, materials_shared"
)


# ---------------------------------------------------------------------------
# Tool 1 — Log Interaction (required)
# ---------------------------------------------------------------------------

@tool
def log_interaction(
    user_text: str,
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Parse a field rep's free-text (or transcribed) description of an HCP
    interaction and fill the structured logging form from it. Use this the
    FIRST time an interaction is described — for corrections to an already
    logged interaction, use edit_interaction instead."""

    prompt = f"""You are a life-sciences CRM assistant. A pharma field rep
described an interaction with a healthcare professional (HCP). Extract these
fields as strict JSON, using null for anything not mentioned: {FIELD_LIST}.

Rep's description: "{user_text}"

Respond with ONLY the JSON object, no commentary."""

    extracted = _call_llm_json(prompt)
    extracted = {k: v for k, v in extracted.items() if v not in (None, "", [])}

    current_draft = state.get("draft", {})
    new_draft = {**current_draft, **extracted}
    changed = [k for k in extracted if extracted[k] != current_draft.get(k)]

    log_entry = {"source": "log_interaction", "input": user_text, "fields_set": changed}
    new_draft["change_log"] = current_draft.get("change_log", []) + [log_entry]

    summary = ", ".join(f"{k}: {extracted[k]}" for k in changed) or "no new fields recognized"

    return Command(
        update={
            "draft": new_draft,
            "changed_fields": list(set(state.get("changed_fields", []) + changed)),
            "tool_calls_used": state.get("tool_calls_used", []) + ["log_interaction"],
            "messages": [
                ToolMessage(content=f"Logged: {summary}", tool_call_id=tool_call_id)
            ],
        }
    )


# ---------------------------------------------------------------------------
# Tool 2 — Edit Interaction (required) — TARGETED patch, not a full re-log
# ---------------------------------------------------------------------------

@tool
def edit_interaction(
    correction_text: str,
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Correct ONE OR MORE specific fields of an interaction that has already
    been logged (e.g. "actually it was Dr. Mehta, not Dr. Shah", or "change
    the sentiment to neutral"). Only the field(s) the user mentions are
    touched — every other field on the form is left exactly as-is."""

    current_draft = state.get("draft", {})

    prompt = f"""The rep already logged this HCP interaction:
{json.dumps({k: v for k, v in current_draft.items() if k != "change_log"}, indent=2)}

They just gave this correction: "{correction_text}"

Return STRICT JSON containing ONLY the field(s) that need to change and their
NEW corrected values. Do not include fields that are not being corrected.
Valid field names: {FIELD_LIST}, sentiment, compliance_flag, compliance_notes.

Respond with ONLY the JSON object."""

    patch = _call_llm_json(prompt)
    patch = {k: v for k, v in patch.items() if k in current_draft or k in (
        "hcp_name", "interaction_type", "interaction_date", "interaction_time",
        "attendees", "topics_discussed", "materials_shared", "sentiment",
        "compliance_flag", "compliance_notes",
    )}

    new_draft = {**current_draft, **patch}
    changed = list(patch.keys())

    log_entry = {"source": "edit_interaction", "input": correction_text, "fields_set": changed}
    new_draft["change_log"] = current_draft.get("change_log", []) + [log_entry]

    if not changed:
        message = "I couldn't identify which field to correct — could you name the field explicitly?"
    else:
        message = "Corrected " + ", ".join(f"{k} → {patch[k]}" for k in changed)

    return Command(
        update={
            "draft": new_draft,
            "changed_fields": list(set(state.get("changed_fields", []) + changed)),
            "tool_calls_used": state.get("tool_calls_used", []) + ["edit_interaction"],
            "messages": [ToolMessage(content=message, tool_call_id=tool_call_id)],
        }
    )


# ---------------------------------------------------------------------------
# Tool 3 — Fetch HCP History (context-aware agent, not single-turn extraction)
# ---------------------------------------------------------------------------

@tool
def fetch_hcp_history(
    hcp_name: str,
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Look up this HCP's past logged interactions before logging a new one,
    so the agent can recall prior topics/materials instead of asking the rep
    to repeat context. Call this when the rep names an HCP and history would
    help (e.g. "log another visit to Dr. Mehta")."""

    db = SessionLocal()
    try:
        rows = (
            db.query(Interaction)
            .filter(Interaction.hcp_name.ilike(f"%{hcp_name}%"))
            .order_by(Interaction.created_at.desc())
            .limit(5)
            .all()
        )
        history = [
            {
                "date": r.interaction_date,
                "type": r.interaction_type,
                "topics": r.topics_discussed,
                "materials": r.materials_shared,
                "sentiment": r.sentiment,
            }
            for r in rows
        ]
    finally:
        db.close()

    if history:
        message = f"Found {len(history)} prior interaction(s) with {hcp_name}."
    else:
        message = f"No prior interactions on file for {hcp_name} — this will be the first."

    return Command(
        update={
            "hcp_history": history,
            "tool_calls_used": state.get("tool_calls_used", []) + ["fetch_hcp_history"],
            "messages": [ToolMessage(content=message, tool_call_id=tool_call_id)],
        }
    )


# ---------------------------------------------------------------------------
# Tool 4 — Compliance / Sentiment Flag (pharma domain relevance)
# ---------------------------------------------------------------------------

@tool
def compliance_sentiment_flag(
    interaction_text: str,
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Analyze the interaction text for HCP sentiment AND compliance risk —
    e.g. off-label usage discussion, unapproved claims, or pricing/incentive
    talk that a pharma compliance team would want reviewed. Call this after
    logging or editing an interaction whenever the description discusses
    clinical claims, adverse events, or the HCP's reaction."""

    prompt = f"""You are a pharma compliance reviewer. Read this rep's account
of an HCP interaction and return STRICT JSON with:
  "sentiment": one of "positive", "neutral", "negative"
  "compliance_flag": true if the text mentions off-label use, unapproved
     efficacy/safety claims, adverse events, or improper incentives — else false
  "compliance_notes": one short sentence explaining the flag, or null if not flagged

Interaction text: "{interaction_text}"

Respond with ONLY the JSON object."""

    result = _call_llm_json(prompt)
    sentiment = result.get("sentiment")
    compliance_flag = bool(result.get("compliance_flag", False))
    compliance_notes = result.get("compliance_notes")

    current_draft = state.get("draft", {})
    new_draft = {
        **current_draft,
        "sentiment": sentiment or current_draft.get("sentiment"),
        "compliance_flag": compliance_flag,
        "compliance_notes": compliance_notes,
    }

    changed = [f for f in ("sentiment", "compliance_flag", "compliance_notes") if new_draft.get(f) != current_draft.get(f)]

    message = (
        f"⚠️ Compliance flag raised: {compliance_notes}"
        if compliance_flag
        else f"No compliance concerns detected. Sentiment: {sentiment or 'unclear'}."
    )

    return Command(
        update={
            "draft": new_draft,
            "changed_fields": list(set(state.get("changed_fields", []) + changed)),
            "tool_calls_used": state.get("tool_calls_used", []) + ["compliance_sentiment_flag"],
            "messages": [ToolMessage(content=message, tool_call_id=tool_call_id)],
        }
    )


# ---------------------------------------------------------------------------
# Tool 5 — Summarize Voice Note (consent-gated — mirrors the reference UI)
# ---------------------------------------------------------------------------

@tool
def summarize_voice_note(
    transcript: str,
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Summarize a transcribed voice note into the Topics Discussed field.
    REQUIRES explicit rep consent (the UI's "Summarize from Voice Note
    (Requires Consent)" toggle) — if consent hasn't been given, do not
    process the transcript; ask the rep to confirm consent first."""

    if not state.get("voice_note_consent", False):
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=(
                            "I can't summarize this voice note yet — please confirm consent "
                            "using the 'Summarize from Voice Note' toggle first."
                        ),
                        tool_call_id=tool_call_id,
                    )
                ]
            }
        )

    prompt = f"""Summarize this transcribed voice note from a pharma field rep
into 2-3 concise bullet points suitable for a "Topics Discussed" CRM field.
Keep clinical/product terms exact — do not paraphrase drug names or dosages.

Transcript: "{transcript}"

Respond with ONLY the bullet-point summary text, no JSON, no preamble."""

    llm = get_llm(temperature=0.1)
    summary = llm.invoke(prompt).content.strip()

    current_draft = state.get("draft", {})
    existing_topics = current_draft.get("topics_discussed") or ""
    merged_topics = (existing_topics + "\n" + summary).strip() if existing_topics else summary

    new_draft = {**current_draft, "topics_discussed": merged_topics}

    return Command(
        update={
            "draft": new_draft,
            "changed_fields": list(set(state.get("changed_fields", []) + ["topics_discussed"])),
            "tool_calls_used": state.get("tool_calls_used", []) + ["summarize_voice_note"],
            "messages": [ToolMessage(content="Voice note summarized into Topics Discussed.", tool_call_id=tool_call_id)],
        }
    )


ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    fetch_hcp_history,
    compliance_sentiment_flag,
    summarize_voice_note,
]
