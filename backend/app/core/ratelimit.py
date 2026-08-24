"""Who a rate limit counts against.

``slowapi.util.get_remote_address`` returns ``request.client.host`` and never
reads ``X-Forwarded-For``. That is correct for a container someone reaches
directly and wrong for every installation that terminates TLS behind a reverse
proxy — which is most of them, and all of the ones on the public internet. There
every caller arrives wearing the proxy's address, so they share one bucket:
fifteen colleagues behind one nginx shared the ten sign-in attempts a minute and
could lock each other out.

The header is not simply trusted instead. A caller can send an
``X-Forwarded-For`` of their own, and a proxy **appends** rather than replaces,
so the header the application sees is ``<what the caller claimed>, <what the
proxy actually saw>``. The leftmost entry is therefore the one under the
caller's control and the rightmost is the one the nearest proxy vouches for.
Reading the left of that list is not a smaller version of this fix; it is a rate
limiter with a bypass in it, because a caller who picks a fresh value per request
gets a fresh bucket per request.

So the entry is counted from the right, one position per proxy in front:

    client -> nginx -> app          "C"        take the 1st from the right
    client -> cdn -> nginx -> app   "C, cdn"   take the 2nd from the right

``TRUSTED_PROXY_COUNT`` is that number and defaults to 1. When the header holds
fewer entries than there are proxies the installation is misconfigured, and this
falls back to the peer address: a limiter that counts everyone as one caller is
useless, but a limiter keyed on a value the caller chooses is worse.

**And the limiter itself lives here**, for a reason found while fixing the above.
There used to be two: one built in ``main.py`` and put on ``app.state``, and a
second built in ``api/routes/auth.py`` that carried every one of the six
``@limiter.limit`` decorators. Only the second enforced anything, so re-keying
the first changed nothing at all — a fix that would have shipped as a no-op and
tested green, because a unit test of the key function passes either way. One
limiter, defined in one place, imported by both.
"""
from __future__ import annotations

from fastapi import Request
from slowapi import Limiter

from app.core.config import get_settings

#: What slowapi falls back to when there is no peer at all (a test client, a
#: unix socket). Kept identical to ``get_remote_address`` so behaviour without
#: a proxy is unchanged.
NO_PEER = "127.0.0.1"


def _peer(request: Request) -> str:
    if not request.client or not request.client.host:
        return NO_PEER
    return request.client.host


def client_address(request: Request) -> str:
    """The address a rate limit is counted against."""
    settings = get_settings()
    if not settings.trusted_proxy_headers:
        return _peer(request)

    forwarded = request.headers.get("x-forwarded-for", "")
    hops = [part.strip() for part in forwarded.split(",") if part.strip()]
    if not hops:
        return _peer(request)

    # One position per proxy in front of us, counted from the right. Anything
    # further left than that was appended by something we do not vouch for.
    count = max(1, settings.trusted_proxy_count)
    if count > len(hops):
        return _peer(request)
    return hops[-count]


#: The application's one rate limiter. Import it; do not build another.
limiter = Limiter(key_func=client_address)
