"""What the application can say about itself: version and release notes.

Split off from ``/api/health`` deliberately. Health is unauthenticated because
a Docker HEALTHCHECK has no session; the changelog is behind the same login as
everything else — not because release notes are secret, but because nothing
that is not needed for monitoring should be readable from outside.
"""
from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.models.user import User
from app.services import changelog
from app.version import get_version

router = APIRouter(tags=["meta"])


@router.get("/changelog")
def release_notes(
    since: str = Query(default="", max_length=32),
    user: User = Depends(get_current_user),
):
    """The releases newer than ``since``, for the what's-new card.

    ``version`` is the version actually running, which is what the caller
    stores as seen — not the newest entry in the file, so a changelog that is
    ahead of or behind the binary can never wedge the card open.
    """
    result = changelog.entries_since(since)
    return {"version": get_version(), **result}
