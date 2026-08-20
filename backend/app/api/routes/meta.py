"""What the application can say about itself: version and release notes.

Split off from ``/api/health`` deliberately. Health is unauthenticated because
a Docker HEALTHCHECK has no session; the changelog is behind the same login as
everything else — not because release notes are secret, but because nothing
that is not needed for monitoring should be readable from outside.
"""
import logging
import threading

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.services import changelog, settings_store, updater, updates
from app.version import get_version

logger = logging.getLogger(__name__)

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


@router.post("/update-check")
def update_check_now(admin: User = Depends(require_admin),
                     db: Session = Depends(get_db)):
    """A fresh look at the release feed, on the administrator's click.

    The passive status call lives off a six-hour cache so settings visits
    stay cheap; this one empties that cache first, because a person who
    presses "check now" is asking GitHub, not the cache.
    """
    if not settings_store.instance_settings(db).update_check_enabled:
        raise HTTPException(status_code=409, detail="The update check is switched off")
    updates.clear_cache()
    return update_status(admin=admin, db=db)


@router.get("/update-capability")
def update_capability(admin: User = Depends(require_admin)):
    """Whether this installation can update itself, and if not, why not.

    "No, because the switch is off" and "no, because no Docker socket is
    mounted" are different answers with different fixes, and the settings
    screen shows the right instructions for each.
    """
    return updater.capability()


@router.get("/update-state")
def update_state(admin: User = Depends(require_admin)):
    """How the last in-app update went, surviving the restart it caused.

    A ``done`` state whose work is visible (the running version) is
    cleared on read, so the message shows once; a ``failed`` state stays
    until the next attempt overwrites it — an error that vanishes on
    refresh was never reported.
    """
    state = updater.read_state()
    if state and state.get("phase") == "done":
        updater.clear_state()
    return {"state": state, "current": get_version()}


@router.post("/update-apply")
def update_apply(admin: User = Depends(require_admin),
                 db: Session = Depends(get_db)):
    """Update to the newest release and restart, where the operator allows.

    The version is never caller input: it is whatever the check found,
    compared against what runs. The pull and the swap happen in the
    background — the response returns before the restart, and the client
    follows progress through the state endpoint until the connection
    drops and the new instance answers.
    """
    ability = updater.capability()
    if not ability["available"]:
        raise HTTPException(status_code=409, detail={
            "error": "apply_unavailable", "reason": ability["reason"]})
    status = update_status(admin=admin, db=db)
    if not status.get("update_available"):
        raise HTTPException(status_code=409, detail={
            "error": "no_update", "current": status.get("current")})
    target = status["latest"]

    def run() -> None:
        try:
            updater.start_update(target)
        except updater.UpdateError as exc:
            logger.warning("In-app update to %s failed: %s", target, exc)
            updater.write_state({"phase": "failed", "to": target,
                                 "error": str(exc)})

    threading.Thread(target=run, name="update-apply", daemon=True).start()
    return {"started": True, "to": target}
