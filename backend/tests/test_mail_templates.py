"""What outgoing mail says, and what it must not say.

Three properties, each of which the messages shipped without at first:

1. **The reader's language, not the sender's.** A colleague whose CargoPilot
   is in German got an English invitation, because the wording lived in the
   code as one English string.
2. **A letter, not a wall of text** — and one that arrives intact, with the
   logo carried along rather than fetched from this server.
3. **No administrator's user name in an invitation.** "admin has made an
   account for you" tells its reader which account is an administrator's,
   including readers who should never have learnt that.
"""
import pytest

from app.core.languages import SUPPORTED
from app.schemas.settings import InstanceSettings
from app.services import mail, mail_templates


def configured() -> InstanceSettings:
    return InstanceSettings(mail_enabled=True, mail_host="smtp.example.com",
                            mail_from="cargopilot@example.com")


ALL_BUILDERS = [
    lambda lang: mail_templates.reset_message(lang, "ada", "https://x/y", 60),
    lambda lang: mail_templates.invite_message(lang, "ada", "https://x/y", 7),
    lambda lang: mail_templates.sign_in_code_message(lang, "123456", 5),
    lambda lang: mail_templates.test_message(lang),
    lambda lang: mail_templates.documents_message(lang, "ada", "CP-1"),
]


# --- the language -----------------------------------------------------------


@pytest.mark.parametrize("language", SUPPORTED)
@pytest.mark.parametrize("build", ALL_BUILDERS)
def test_every_message_exists_in_every_language(build, language):
    message = build(language)
    assert message.subject and message.text and message.html
    assert f'lang="{language}"' in message.html


def test_the_dutch_reset_is_dutch_and_the_german_one_german():
    nl = mail_templates.reset_message("nl", "ada", "https://x/y", 60)
    de = mail_templates.reset_message("de", "ada", "https://x/y", 60)
    assert nl.subject == "Wachtwoord opnieuw instellen"
    assert "wachtwoord" in nl.text.lower()
    # The call to action lives on the button, which is the HTML's own.
    assert "Kies een nieuw wachtwoord" in nl.html
    assert de.subject == "Passwort zurücksetzen"
    assert "Passwort" in de.text


def test_an_unknown_language_falls_back_rather_than_failing():
    """A stored preference for a language that was dropped must not stop
    somebody from resetting their password."""
    message = mail_templates.reset_message("kl", "ada", "https://x/y", 60)
    assert message.subject == mail_templates.RESET["nl"]["subject"]


# --- what the invitation gives away -----------------------------------------


@pytest.mark.parametrize("language", SUPPORTED)
def test_the_invitation_never_names_the_administrator(language):
    """It used to read "admin has made an account for you", which hands an
    administrator's user name to whoever opens the message."""
    message = mail_templates.invite_message(language, "nieuwe-collega",
                                            "https://x/y", 7)
    # The body says who made the account only by role. (The subject names
    # neither, which is right: it is about the reader's own account.)
    for body in (message.text, message.html):
        assert any(word in body.lower() for word in
                   ("beheerder", "administrator", "administrateur"))
    # The reader's own name belongs there; nobody else's does.
    assert "nieuwe-collega" in message.text


def test_the_invitation_carries_the_link_and_its_lifetime():
    message = mail_templates.invite_message("nl", "ada", "https://cp/x?token=abc", 7)
    assert "https://cp/x?token=abc" in message.text
    assert "https://cp/x?token=abc" in message.html
    assert "7 dagen" in message.text


# --- the shape of the letter ------------------------------------------------


def test_a_message_is_plain_text_and_html_and_carries_its_logo():
    message = mail_templates.test_message("nl")
    built = mail.build_message(configured(), "ada@example.com",
                               message.subject, message.text, html=message.html)
    types = [part.get_content_type() for part in built.walk()]
    assert "text/plain" in types
    assert "text/html" in types
    assert "image/png" in types


def test_the_logo_travels_with_the_message_rather_than_being_fetched():
    """A linked image makes the reader's client call this server: a tracking
    pixel by accident, and a broken image on an installation the internet
    cannot reach."""
    message = mail_templates.test_message("nl")
    assert f'src="cid:{mail_templates.LOGO_CID}"' in message.html
    assert "http://" not in message.html.replace("http://www.w3.org", "")

    built = mail.build_message(configured(), "ada@example.com",
                               message.subject, message.text, html=message.html)
    images = [p for p in built.walk() if p.get_content_type() == "image/png"]
    assert images and images[0].get("Content-ID") == f"<{mail_templates.LOGO_CID}>"


def test_a_message_without_html_stays_a_plain_one():
    built = mail.build_message(configured(), "ada@example.com", "S", "Body")
    assert built.get_content_type() == "text/plain"


def test_the_plain_text_says_the_same_as_the_html():
    """The text is not a leftover: somebody reading it must learn the same
    things, including the code and the link."""
    code = mail_templates.sign_in_code_message("nl", "654321", 5)
    assert "654321" in code.text and "654321" in code.html

    reset = mail_templates.reset_message("nl", "ada", "https://cp/reset?t=1", 60)
    assert "https://cp/reset?t=1" in reset.text
    assert "60 minuten" in reset.text and "60 minuten" in reset.html


def test_a_user_name_with_html_in_it_cannot_break_out():
    """User names are not markup, and a mail client is a renderer."""
    message = mail_templates.invite_message(
        "nl", "<script>alert(1)</script>", "https://x/y", 7)
    assert "<script>" not in message.html
    assert "&lt;script&gt;" in message.html


def test_the_senders_own_words_replace_the_standard_sentence():
    """Somebody who writes their own covering note means it to be the note,
    not a preface to a canned one."""
    written = mail_templates.documents_message(
        "nl", "ada", "CP-1", note="Beste Jan, hierbij de papieren.")
    assert "Beste Jan" in written.text
    assert mail_templates.DOCUMENTS["nl"]["intro"] not in written.text
    # And the sender is still named, because the reader has to know who sent it.
    assert "ada" in written.text


def test_the_document_subject_carries_the_reference():
    message = mail_templates.documents_message("nl", "ada", "CP-2026-100")
    assert "CP-2026-100" in message.subject
