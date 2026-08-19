"""What the application can say about itself: version and release notes.

Split off from ``/api/health`` deliberately. Health is unauthenticated because
a Docker HEALTHCHECK has no session; the changelog is behind the same login as
everything else — not because release notes are secret, but because nothing
that is not needed for monitoring should be readable from outside.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.services import changelog, settings_store, updates
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


@router.get("/update-status")
def update_status(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Whether a newer release exists, for the one person who could pull it.

    Admin-only on both grounds: the toast is only useful to whoever operates
    the container, and a signed-in user must not be able to make this
    installation call GitHub when its administrator switched that off — the
    switch is checked here, per request, not once at startup.

    Three shapes of answer, kept distinct on purpose: the check is off
    (``enabled`` false), GitHub could not say (``reachable`` false — which is
    *not* "you are up to date"), or a real comparison.
    """
    current = get_version()
    if not settings_store.instance_settings(db).update_check_enabled:
        return {"enabled": False, "current": current}
    release = updates.latest_release()
    if release is None:
        return {"enabled": True, "reachable": False, "current": current}
    ours = updates.version_key(current)
    theirs = updates.version_key(release["version"])
    return {
        "enabled": True,
        "reachable": True,
        "current": current,
        "latest": release["version"],
        "url": release["url"],
        "update_available": ours is not None and theirs is not None and theirs > ours,
    }
