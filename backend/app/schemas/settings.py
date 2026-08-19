"""What can be set, and within which bounds.

Two audiences, two models. :class:`UserPreferences` is what one person chose for
themselves and nobody else sees. :class:`InstanceSettings` is what the
administrator chose for the whole installation, and it is the one that can
switch off outbound network traffic — so every field here is validated rather
than trusted.

Every field carries a default. That is what makes the JSON storage in
``app.models.settings`` upgrade-proof: a database written before a setting
existed simply lacks the key, and the default fills in.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.languages import DEFAULT as DEFAULT_LANGUAGE
from app.core.languages import SUPPORTED as SUPPORTED_LANGUAGES

#: The transport modes the wizard offers, mirrored from ``MODALITIES`` in
#: ``frontend/src/pages/ModalitySelectPage.tsx``. An empty string means "ask me
#: every time", which stays the default: guessing wrong sends someone into the
#: wrong set of forms.
MODALITIES = ("road", "rail", "sea", "inland", "air", "multimodal")

ThemeChoice = Literal["light", "dark", "system"]

#: A drawn signature is a PNG data URL. The cap is deliberate — the pad produces
#: roughly 10-30 kB, so anything past a quarter of a megabyte is not a signature.
MAX_SIGNATURE_CHARS = 262_144


class UserPreferences(BaseModel):
    """One user's own settings.

    Before v1.45.0 the language and the theme lived in ``localStorage``. That
    worked until the same person opened the app on a second device and found it
    back in Dutch on a white background. Both now travel with the account; the
    browser keeps a copy only so the first paint does not flash.
    """

    #: Empty means: follow the instance default (and, failing that, the browser).
    language: str = ""
    theme: ThemeChoice = "system"

    #: Skip the transport-mode tiles and open this mode straight away. Empty
    #: keeps the tiles, which is right for anyone who ships by more than one mode.
    default_modality: str = ""

    #: The unit a freshly added line starts with. Used to be the hard-coded
    #: string "stuks" — a Dutch word that reached German and French screens too.
    default_unit: str = "pcs"

    #: Whether the details below are filled in for you at all. Off means they are
    #: kept but never applied, which beats deleting them to stop the prefill.
    prefill_documents: bool = True

    #: The consignor is nearly always the same company for the same person, and
    #: it is retyped on every single shipment.
    consignor_name: str = ""
    consignor_address: str = ""
    consignor_contact: str = ""

    #: Frequently, though not always, the same. Optional on every form.
    carrier_name: str = ""
    loading_point: str = ""

    #: The 24-hour emergency telephone number. IMDG 5.4.1.5.11 and the IATA DGR
    #: shipper's declaration both want it, it never changes, and it was retyped
    #: for every consignment.
    emergency_contact: str = ""

    #: A signature drawn once, kept for reuse. Opt-in by being empty until the
    #: user saves one, and described in ``docs/privacy.md``.
    signature_image: str = Field(default="", max_length=MAX_SIGNATURE_CHARS)

    #: The version whose release notes this user has already seen. The
    #: what's-new card shows the entries between this and the running version,
    #: then writes the running version here. Empty means no marker yet — a new
    #: account, or one from before v1.125.0 — and shows nothing rather than
    #: the whole history.
    last_seen_version: str = ""

    @field_validator("language")
    @classmethod
    def _known_language(cls, value: str) -> str:
        value = (value or "").strip().lower()
        if value and value not in SUPPORTED_LANGUAGES:
            raise ValueError(f"unknown language: {value}")
        return value

    @field_validator("default_modality")
    @classmethod
    def _known_modality(cls, value: str) -> str:
        value = (value or "").strip().lower()
        if value and value not in MODALITIES:
            raise ValueError(f"unknown transport mode: {value}")
        return value

    @field_validator("last_seen_version")
    @classmethod
    def _version_like(cls, value: str) -> str:
        value = (value or "").strip()
        if value and not re.fullmatch(r"\d+\.\d+\.\d+", value):
            raise ValueError("not a version number")
        return value

    @field_validator("signature_image")
    @classmethod
    def _looks_like_an_image(cls, value: str) -> str:
        value = (value or "").strip()
        if value and not value.startswith("data:image/"):
            raise ValueError("signature must be an image data URL")
        return value

    @field_validator(
        "consignor_name",
        "consignor_address",
        "consignor_contact",
        "carrier_name",
        "loading_point",
        "emergency_contact",
        "default_unit",
    )
    @classmethod
    def _trimmed(cls, value: str) -> str:
        return (value or "").strip()


class InstanceSettings(BaseModel):
    """What the administrator decides for everyone.

    The defaults are read from the environment variables that already governed
    these choices, so an installation that never opens this screen keeps behaving
    exactly as its ``.env`` says. Saving here takes precedence from then on —
    and, unlike an environment variable, without restarting the container.
    """

    #: The language a user who has not chosen one gets, and the language of the
    #: login screen.
    default_language: str = DEFAULT_LANGUAGE
    default_theme: ThemeChoice = "system"

    #: Address autocomplete is the only outbound request the app makes while
    #: someone is using it. On an air-gapped or privacy-sensitive installation
    #: this switch is the point of this whole screen.
    address_lookup_enabled: bool = True
    address_api_url: str = "https://photon.komoot.io/api"
    address_timeout_seconds: float = Field(default=8.0, ge=1.0, le=60.0)

    #: The other outbound request, made at startup only. Turning it off takes
    #: effect the next time the container starts.
    catalog_auto_sync: bool = True

    #: The UN card download. Some installations would rather hand out their own
    #: instruction cards than these.
    un_cards_enabled: bool = True

    #: How long a session stays valid. Eight hours is one working day.
    session_timeout_minutes: int = Field(default=480, ge=15, le=10_080)

    #: Used as the consignor for users who filled in nothing of their own, so a
    #: new colleague starts with the company already on the form.
    organisation_name: str = ""
    organisation_address: str = ""

    @field_validator("default_language")
    @classmethod
    def _known_language(cls, value: str) -> str:
        value = (value or "").strip().lower()
        if value not in SUPPORTED_LANGUAGES:
            raise ValueError(f"unknown language: {value}")
        return value

    @field_validator("address_api_url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        value = (value or "").strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError("address API must be an http(s) URL")
        return value

    @field_validator("organisation_name", "organisation_address")
    @classmethod
    def _trimmed(cls, value: str) -> str:
        return (value or "").strip()


class PublicSettings(BaseModel):
    """The part of the instance settings every signed-in user may know.

    Deliberately narrow. The wizard needs to know whether to offer the UN card
    download and whether address lookup will answer; it has no business knowing
    the session lifetime or which geocoder is configured.
    """

    default_language: str
    default_theme: ThemeChoice
    address_lookup_enabled: bool
    un_cards_enabled: bool
    organisation_name: str
    organisation_address: str
