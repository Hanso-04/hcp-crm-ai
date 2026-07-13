from langchain_groq import ChatGroq

from app.config import settings


def get_llm(temperature: float = 0.1) -> ChatGroq:
    """Primary model — mandated by the assignment brief."""
    return ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=temperature,
    )


def get_fallback_llm(temperature: float = 0.1) -> ChatGroq:
    """Heavier model, used only where gemma2-9b-it's small context/reasoning
    budget struggles — e.g. multi-entity extraction from a long voice-note
    transcript. Swap calls to this in tools.py if you see gemma2 mis-parsing."""
    return ChatGroq(
        model=settings.GROQ_FALLBACK_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=temperature,
    )
