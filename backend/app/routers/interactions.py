from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Interaction
from app.schemas import ConfirmInteractionRequest, InteractionOut

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("", response_model=InteractionOut)
def confirm_interaction(req: ConfirmInteractionRequest, db: Session = Depends(get_db)):
    """Persist a draft the rep has reviewed and confirmed in the UI.
    This is the ONLY endpoint that writes to the interactions table — it's
    called after the agent has proposed/edited a draft and the human has
    clicked 'Confirm', matching the human-in-the-loop rule described in the
    assignment write-up."""

    data = req.draft.model_dump()

    if req.interaction_id:
        row = db.query(Interaction).get(req.interaction_id)
        if not row:
            raise HTTPException(status_code=404, detail="Interaction not found")
        for k, v in data.items():
            setattr(row, k, v)
    else:
        row = Interaction(**data)
        db.add(row)

    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=List[InteractionOut])
def list_interactions(db: Session = Depends(get_db)):
    return db.query(Interaction).order_by(Interaction.created_at.desc()).all()


@router.get("/{interaction_id}", response_model=InteractionOut)
def get_interaction(interaction_id: int, db: Session = Depends(get_db)):
    row = db.query(Interaction).get(interaction_id)
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return row
