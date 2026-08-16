"""The assistant endpoints: one conversational turn, and a status probe.

Stateless on the server: the wizard state travels with the request and comes
back patched. Nothing of the conversation is stored — the same privacy stance
the rest of the application takes with pasted data and documents.
"""
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.assistant.orchestrator import step

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantStepRequest(BaseModel):
    message: str = Field(default="", max_length=4000)
    state: dict[str, Any] = Field(default_factory=dict)
    pending: dict[str, Any] | None = None
    language: str = Field(default="nl", max_length=10)


@router.post("/step")
def assistant_step(
    payload: AssistantStepRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return step(payload.state, payload.message, payload.pending, db, payload.language)


@router.get("/status")
def assistant_status(user: User = Depends(get_current_user)):
    """Whether the assistant can run, and in which mode.

    Phase 22 always answers with the deterministic mode: the guided chain of
    parser, name recognition and open questions. A language model (phase 23)
    only changes how flexibly free text is read, never what may be asked or
    answered.
    """
    return {"available": True, "mode": "deterministic", "model": None}
