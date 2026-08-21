"""Sending mail through the server the administrator configured.

Deliberately thin, and deliberately stdlib: ``smtplib`` and ``email.message``
speak SMTP well enough for a handful of messages, and a dependency that
brings its own retry policy and its own opinions about queues would be a
larger thing than this needs.

Nothing here decides *whether* mail may be sent. That is the instance
setting, read fresh on every send, so switching the mail server off takes
effect immediately rather than at the next restart.

Failures are reported, never swallowed. A mail server that refuses the
password says so in words the administrator can act on, and those words are
carried through to the screen unchanged — guessing what "authentication
failed" means for their particular relay is not this module's job.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from app.schemas.settings import InstanceSettings

logger = logging.getLogger(__name__)


class MailError(RuntimeError):
    """A message could not be sent, with the reason as the server gave it."""


def is_configured(settings: InstanceSettings) -> bool:
    """Whether sending is switched on and pointed at a server."""
    return bool(settings.mail_enabled and settings.mail_host and settings.mail_from)


def _sender(settings: InstanceSettings) -> str:
    """The From header: a display name when one is set, the bare address
    otherwise. The envelope sender stays the address either way."""
    if settings.mail_from_name:
        return formataddr((settings.mail_from_name, settings.mail_from))
    return settings.mail_from


#: What one message may carry. Mail servers cap attachments — 25 MB at
#: Google, 10 at many corporate relays — and they cap the *encoded* size,
#: which base64 inflates by a third. Refusing here names the size and the
#: limit; letting it through returns whatever cryptic code the relay picks.
MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024


def build_message(
    settings: InstanceSettings,
    to: str | list[str],
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = _sender(settings)
    message["To"] = ", ".join(to) if isinstance(to, list) else to
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    # Without a Message-ID some relays add their own and others reject the
    # message outright; the sender's domain is the honest origin for it.
    domain = settings.mail_from.rsplit("@", 1)[-1] or None
    message["Message-ID"] = make_msgid(domain=domain)
    message.set_content(body)
    for filename, content, mimetype in attachments or []:
        main, _, sub = mimetype.partition("/")
        message.add_attachment(content, maintype=main or "application",
                               subtype=sub or "octet-stream", filename=filename)
    return message


def _connect(settings: InstanceSettings) -> smtplib.SMTP:
    timeout = settings.mail_timeout_seconds
    if settings.mail_security == "ssl":
        context = ssl.create_default_context()
        return smtplib.SMTP_SSL(
            settings.mail_host, settings.mail_port, timeout=timeout, context=context)
    client = smtplib.SMTP(settings.mail_host, settings.mail_port, timeout=timeout)
    if settings.mail_security == "starttls":
        client.starttls(context=ssl.create_default_context())
        # The greeting from before STARTTLS says nothing about what the
        # encrypted session offers; asking again is what the RFC expects.
        client.ehlo()
    return client


def send(
    settings: InstanceSettings,
    to: str | list[str],
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> None:
    """Send one message, or raise :class:`MailError` saying why not."""
    if not is_configured(settings):
        raise MailError("No mail server is configured.")
    recipients = [to] if isinstance(to, str) else list(to)
    recipients = [address.strip() for address in recipients if address.strip()]
    if not recipients:
        raise MailError("No recipient given.")

    total = sum(len(content) for _, content, _ in attachments or [])
    if total > MAX_ATTACHMENT_BYTES:
        raise MailError(
            f"The attachments are {total / 1024 / 1024:.1f} MB, more than the "
            f"{MAX_ATTACHMENT_BYTES // 1024 // 1024} MB one message may carry. "
            "Send fewer documents, or download them and share them another way."
        )

    message = build_message(settings, recipients, subject, body, attachments)
    to = ", ".join(recipients)
    try:
        with _connect(settings) as client:
            if settings.mail_username:
                client.login(settings.mail_username, settings.mail_password)
            client.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:
        raise MailError(
            f"The mail server refused the user name or password: {_reason(exc)}"
        ) from exc
    except smtplib.SMTPRecipientsRefused as exc:
        raise MailError(f"The mail server refused the recipient {to}.") from exc
    except smtplib.SMTPException as exc:
        raise MailError(f"The mail server refused the message: {_reason(exc)}") from exc
    except ssl.SSLError as exc:
        raise MailError(
            f"The encrypted connection failed: {exc}. "
            "Check whether the port expects STARTTLS or direct TLS."
        ) from exc
    except OSError as exc:
        # Host not found, connection refused, timeout: the network layer, and
        # the one an operator most often has to fix.
        raise MailError(
            f"Could not reach {settings.mail_host}:{settings.mail_port}: {exc}"
        ) from exc
    logger.info("Sent mail to %s via %s", to, settings.mail_host)


def _reason(exc: smtplib.SMTPException) -> str:
    """What the server said, without the Python tuple around it."""
    message = getattr(exc, "smtp_error", None)
    if isinstance(message, bytes):
        return message.decode("utf-8", "replace").strip()
    return str(message or exc).strip()


#: The test message. Short on purpose: it is read by the person who just
#: pressed the button, and its only job is to prove the path works.
TEST_SUBJECT = "CargoPilot test message"
TEST_BODY = (
    "This is a test message from CargoPilot.\n\n"
    "If you are reading it, the mail server settings work: CargoPilot "
    "reached the server, was accepted, and the message was delivered.\n"
)


def send_test(settings: InstanceSettings, to: str) -> None:
    send(settings, to, TEST_SUBJECT, TEST_BODY)
