from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON

from app.database import Base


class Interaction(Base):
    """A single logged HCP (Healthcare Professional) interaction.

    Rows here are only ever created/updated through the LangGraph agent's
    Log Interaction / Edit Interaction tools — never through a raw form POST —
    which is the "AI writes, human confirms" rule the assignment calls for.
    """

    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)

    hcp_name = Column(String(255), nullable=False, index=True)
    interaction_type = Column(String(50), default="Meeting")  # Meeting / Call / Email / Conference
    interaction_date = Column(String(20), nullable=True)   # stored as YYYY-MM-DD (string keeps agent patches simple)
    interaction_time = Column(String(20), nullable=True)   # stored as HH:MM AM/PM
    attendees = Column(Text, nullable=True)
    topics_discussed = Column(Text, nullable=True)
    materials_shared = Column(Text, nullable=True)

    sentiment = Column(String(20), nullable=True)          # positive / neutral / negative
    compliance_flag = Column(Boolean, default=False)
    compliance_notes = Column(Text, nullable=True)

    # Free-form audit trail: list of {source: "log"|"edit", text, timestamp}
    change_log = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
