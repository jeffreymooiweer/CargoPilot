"""The ten tasks of the usability plan, driven against the running application."""
from __future__ import annotations

import re

import requests
from bench import OUT, BASE, Bench, browser, dismiss_toasts, history, sign_in, write
from playwright.sync_api import sync_playwright

GOODS = [
    ("Stalen hoekprofiel 80x80x8x6000", 8),
    ("Stalen plaat 2000x1000x10", 4),
    ("Stalen buis 60x60x4x4000", 12),
]
FORWARD = re.compile(r"^(Naar export|Naar zendinggegevens|Naar gevaarlijke stoffen|Volgende|Doorgaan)$")
#: Since v1.196.0 a form with required fields still empty says which on the
#: first press and walks on on the second, under a different label.
ANYWAY = re.compile(r"^Toch doorgaan$")

#: What a required field gets, by what its label says. The content only has to
#: be plausible; what is measured is how many of them there are.
BY_LABEL = [
    ("laad", "Rotterdam"), ("los", "Antwerpen"), ("plaats", "Rotterdam"),
    ("afzender", "Mooiweer BV"), ("geadresseerde", "Klant NV"), ("vervoerder", "Transport BV"),
    ("adres", "Havenweg 1, Rotterdam"), ("referentie", "CP-2026-900"),
    ("gewicht", "100"), ("aantal", "1"), ("nummer", "1"),
]


def new_shipment(page) -> None:
    page.goto(f"{BASE}/wizard/road")
    page.wait_for_timeout(2500)
    dismiss_toasts(page)


def fill_line(b: Bench, index: int, description: str, quantity: int) -> None:
    """One goods line, on the line itself."""
    b.fill(b.page.get_by_label(re.compile(f"Omschrijving van regel {index + 1}")), description)
    b.page.keyboard.press("Escape")  # close the catalogue suggestions
    b.page.wait_for_timeout(200)
    b.fill(b.page.get_by_label(re.compile(f"Aantal van regel {index + 1}")), str(quantity))


def set_quantity(b: Bench, index: int, quantity: int) -> None:
    b.fill(b.page.get_by_label(re.compile(f"Aantal van regel {index + 1}")), str(quantity))


def wait_for_calculation(b: Bench, seconds: int = 30) -> None:
    """Wait until no line is left saying it still has to be rechecked."""
    for _ in range(seconds * 2):
        if b.page.get_by_text("Te controleren").count() == 0:
            return
        b.page.wait_for_timeout(500)


def add_line(b: Bench) -> None:
    b.click(b.page.get_by_role("button", name="Regel toevoegen"))


def value_for(label: str) -> str:
    low = label.lower()
    for needle, value in BY_LABEL:
        if needle in low:
            return value
    return "Mooiweer BV"


def fill_required(b: Bench) -> int:
    """Fill what the form now showing marks with a star. Returns how many."""
    boxes = b.page.locator("div:has(> div > label > span.text-red-500)")
    filled = 0
    for index in range(boxes.count()):
        box = boxes.nth(index)
        try:
            if not box.is_visible():
                continue
            label = box.locator("label").first.inner_text()
            # The textarea first: an address field leads with a lookup box, and
            # filling that one leaves the field the export needs still empty.
            control = box.locator("textarea:visible").first
            if not control.count():
                control = box.locator("select:visible").first
            if not control.count():
                control = box.locator("input:visible").first
            if not control.count():
                continue
            tag = control.evaluate("el => el.tagName")
            kind = control.evaluate("el => el.type || ''")
            if tag == "SELECT":
                if control.input_value():
                    continue
                control.select_option(index=1)
                b.m.actions += 1
            elif kind == "checkbox":
                if control.is_checked():
                    continue
                control.check()
                b.m.actions += 1
            elif kind == "date":
                if control.input_value():
                    continue
                b.fill(control, "2026-09-06")
            else:
                if control.input_value():
                    continue
                b.fill(control, value_for(label))
            filled += 1
        except Exception:
            continue
    return filled


def missing_chips(page):
    """The fields a document card names as still missing.

    Each of them is a button since v1.196.0: the notice used to be one line of
    plain text, and reaching the field it named meant walking back by hand.
    """
    return page.locator("p:has-text('Ontbrekend:') button")


def answer_from_chip(b: Bench, chip) -> bool:
    """Answer one named missing field from where it is named, and come back."""
    label = chip.inner_text().strip()
    b.click(chip)
    b.page.wait_for_timeout(2500)
    b.observe()
    focused = b.page.locator("*:focus")
    if not focused.count():
        b.note(f"{label}: the form opened but the cursor was not put in the field")
        return False
    b.note(f"one action opened the form the field is on and put the cursor in {label}")
    tag = focused.evaluate("el => el.tagName")
    kind = focused.evaluate("el => el.type || ''")
    if tag == "SELECT":
        focused.select_option(index=1)
        b.m.actions += 1
    elif kind == "date":
        b.fill(focused, "2026-09-06")
    else:
        b.fill(focused, value_for(label))
    back = b.page.get_by_role("button", name="Terug naar het overzicht")
    if not back.count():
        b.note("nothing led straight back to where the question was asked")
        return False
    b.click(back.first)
    b.page.wait_for_timeout(2500)
    b.observe()
    return b.current_step() == "Export"


def confirm_declarations(b: Bench) -> bool:
    """Tick the declaration a document needs before it may be exported.

    It is not marked with a star — its status is SIGNATURE_REQUIRED, not
    USER_REQUIRED — so the form does not present it as something missing, but
    without it the export button stays disabled.
    """
    box = b.page.get_by_label(re.compile("bevestig deze verklaringen", re.I))
    if not box.count() or not box.first.is_visible() or box.first.is_checked():
        return False
    box.first.check()
    b.m.actions += 1
    b.note("the declaration that unlocks the export carries no star: it is not "
           "presented as a required field, but nothing exports without it")
    return True


def advance(b: Bench, limit: int = 10) -> None:
    """Walk forward to the export step, counting the forms crossed on the way."""
    forms = 0
    for _ in range(limit):
        if b.current_step() == "Export":
            break
        fill_required(b)
        confirm_declarations(b)
        nxt = b.page.get_by_role("button", name=FORWARD)
        if not nxt.count():
            break
        was = b.current_step()
        b.click(nxt.last)
        b.page.wait_for_timeout(2200)
        b.observe()
        if was == "Zendinggegevens":
            forms += 1
    b.m.sub_steps = forms


# --- 1. a simple shipment, and the right package ---------------------------------


def task_1(page) -> object:
    b = Bench(page, "1", "A simple shipment to a downloaded package")
    new_shipment(page)
    b.observe()
    for index, (description, quantity) in enumerate(GOODS):
        if index:
            add_line(b)
            focused = page.evaluate(
                "document.activeElement && (document.activeElement.getAttribute('aria-label') "
                "|| document.activeElement.tagName)")
            b.note(f"after Regel toevoegen the focus is on {focused}")
        fill_line(b, index, description, quantity)
    wait_for_calculation(b)
    b.shot("goods")
    advance(b)
    b.shot("export")
    b.note(f"{b.m.sub_steps} form(s) crossed inside the shipment-details step before the export step")
    names = page.locator("button:visible").evaluate_all(
        "els => els.map(e => (e.innerText || e.getAttribute('aria-label') || '').trim()).filter(Boolean)")
    b.note(f"{len(names)} button(s) are on offer on the export step: {'; '.join(names[:20])}")
    downloads = page.get_by_role("button", name=re.compile("downloaden", re.I))
    b.note(f"{downloads.count()} of them download something")
    statuses = page.locator("span.rounded-full:visible").evaluate_all(
        "els => els.map(e => e.innerText.trim()).filter(Boolean)")
    b.note(f"the document cards report: {'; '.join(statuses[:6]) or 'nothing'}")
    missing = page.get_by_text(re.compile("Ontbrekend"))
    if missing.count():
        b.note(f"still missing after every starred field was filled: "
               f"{missing.first.inner_text()[:140]}")
    for index in range(downloads.count()):
        if downloads.nth(index).is_disabled():
            b.note("the export step's only download button is disabled, with the reason "
                   "on the document card rather than at the button, and no way from the "
                   "button to the field that would enable it")
            continue
        try:
            downloads.nth(index).scroll_into_view_if_needed()
            with page.expect_download(timeout=45000) as caught:
                b.click(downloads.nth(index))
            got = caught.value
            target = OUT / f"task1-{got.suggested_filename}"
            got.save_as(str(target))
            b.m.output["file"] = got.suggested_filename
            b.m.output["bytes"] = target.stat().st_size
            break
        except Exception as exc:
            b.note(f"the download button {index + 1} produced no file: {str(exc)[:70]}")
    return b.done(bool(b.m.output))


# --- 2. five quantities on five lines --------------------------------------------


def task_2(page) -> object:
    b = Bench(page, "2", "Five quantities changed on five lines")
    new_shipment(page)
    for _ in range(4):
        add_line(b)
    b.m.actions = 0  # the setup is not the task
    b.m.windows = 0
    b.m.notes.clear()
    b.observe()
    for index in range(5):
        set_quantity(b, index, 10 + index)
    b.note("each quantity is typed on its own line: one action, no window")
    b.shot("quantities")
    return b.done()


# --- 3. fifty imported rows, one of them unclear ----------------------------------


def task_3(page) -> object:
    b = Bench(page, "3", "Fifty rows imported, one unclear")
    new_shipment(page)
    rows = [f"Stalen hoekprofiel 80x80x8x{3000 + i * 10} | {i + 1} | stuks" for i in range(49)]
    rows.insert(24, "Diverse onderdelen | 3 | stuks")  # the one without dimensions
    b.click(page.get_by_role("button", name="Plakken uit Excel"))
    b.fill(page.get_by_label("Plakken uit Excel"), "\n".join(rows))
    b.click(page.get_by_role("button", name=re.compile("^(Importeren|Toevoegen)$")).last)
    page.wait_for_timeout(3000)
    b.observe()
    b.m.output["lines"] = page.get_by_role("button", name="Details").count()
    wait_for_calculation(b, 60)  # the recalculation over fifty lines
    b.observe()
    b.shot("imported")
    statuses = page.locator("span.rounded-full").evaluate_all(
        "els => els.map(e => e.innerText.trim()).filter(t => t && t.length < 20)")
    tally = {name: statuses.count(name) for name in set(statuses)}
    b.m.output["statuses"] = tally
    b.note(f"of {b.m.output['lines']} imported lines the statuses are {tally}")
    summary = page.get_by_text(re.compile("wil aandacht"))
    b.note(f"the list says: {summary.first.inner_text()}" if summary.count()
           else "nothing above the list says how the import came out")
    narrow = page.get_by_role("button", name="Alleen deze tonen")
    if narrow.count():
        b.click(narrow)
        shown = page.get_by_role("button", name="Details").count()
        b.m.output["narrowed_to"] = shown
        left = page.get_by_label(re.compile("Omschrijving van regel"))
        reason = left.first.input_value() if left.count() else ""
        why = page.get_by_text(re.compile("Geen maten|Geen lengte|niet herkend"))
        if why.count():
            reason += f" — {why.first.inner_text()}"
        b.note(f"narrowing to what wants attention leaves {shown} line(s): {reason[:120]}")
    else:
        unclear = page.get_by_text("Diverse onderdelen", exact=False)
        if unclear.count():
            position = unclear.first.evaluate(
                "el => Math.round(el.getBoundingClientRect().top + window.scrollY)")
            b.note(f"the one row without dimensions sits {position} px down the page, "
                   "with nothing on screen pointing at it")
    return b.done(b.m.output.get("lines", 0) >= 50)


# --- 4. a substance suggestion: close it, judge it, revisit it ---------------------


def task_4(page) -> object:
    b = Bench(page, "4", "A substance suggestion closed, judged and revisited")
    new_shipment(page)
    fill_line(b, 0, "Benzine 25 L jerrycan", 4)
    wait_for_calculation(b)
    page.wait_for_timeout(1500)
    b.observe()
    b.shot("suggestion")
    asked = page.get_by_text(re.compile(r"lijkt op UN ?\d{4}"))
    b.note(f"{asked.count()} recognition question(s), on the line they are about")
    if not asked.count():
        b.note("no question was offered to answer")
        return b.done(False)

    # 1. Say the suggestion is wrong — the answer the old close button pretended
    #    to be, now said in words.
    b.click(page.get_by_role("button", name=re.compile("klopt niet")))
    said = page.get_by_text(re.compile("Beantwoord"))
    b.note(f"the line now says: {said.first.inner_text() if said.count() else 'nothing'}")

    # 2. Find the decision again and change it.
    change = page.get_by_role("button", name=re.compile("Antwoord wijzigen"))
    b.note(f"{change.count()} way(s) to revise the answer from the line itself")
    if change.count():
        b.click(change.first)
        take = page.get_by_role("button", name=re.compile("^Neem UN"))
        if take.count():
            b.click(take.first)
    wait_for_calculation(b)
    page.wait_for_timeout(800)
    confirmed = page.get_by_text(re.compile("Beantwoord: UN"))
    b.note(f"after revising, the line says: {confirmed.first.inner_text() if confirmed.count() else 'nothing'}")
    b.shot("answered")
    return b.done(confirmed.count() > 0)


# --- 5. an extra document that needs one new answer --------------------------------


def task_5(page, session: requests.Session) -> object:
    b = Bench(page, "5", "An extra document needing one new answer")
    new_shipment(page)
    fill_line(b, 0, "Stalen plaat 2000x1000x10", 4)
    advance(b)
    b.shot("export-before")
    b.m.actions = 0  # getting there is task 1; this task is the extra document
    b.m.windows = 0
    b.m.notes.clear()
    # Since v1.198.0 the choice is made where its questions are asked, before
    # the fields are filled in, rather than on the export step after they all
    # are. From a finished shipment that is one press back to it.
    b.click(page.get_by_role("button", name="Documentenpakket wijzigen").first)
    page.wait_for_timeout(2500)
    b.observe()
    boxes = page.locator("input[type=checkbox]:visible")
    b.note(f"the document choice is on the {b.current_step()} step, among {boxes.count()} "
           "checkbox(es), where its questions are asked")
    picked = -1
    for index in range(boxes.count()):
        box = boxes.nth(index)
        if not box.is_checked():
            b.click(box)
            picked = index
            break
    page.wait_for_timeout(2500)
    b.observe()
    if picked < 0:
        b.note("no unchecked document was on offer")
        b.shot("extra-document")
        return b.done(False)
    said = page.get_by_text(re.compile("voegt"))
    b.note(f"what it added is said straight away: {said.first.inner_text() if said.count() else 'nothing'}")
    to = page.get_by_role("button", name="Naar die vragen")
    if not to.count():
        b.note("the extra document asked nothing that was not already asked")
        b.shot("extra-document")
        advance(b)
        return b.done(b.current_step() == "Export")
    b.click(to.first)
    page.wait_for_timeout(1500)
    focused = page.locator("*:focus")
    if focused.count():
        b.note("one action put the cursor in the first question it added")
        if focused.evaluate("el => el.type || ''") == "date":
            b.fill(focused, "2026-09-06")
        else:
            b.fill(focused, "Rotterdam")
    b.shot("extra-document")
    back = page.get_by_role("button", name="Terug naar het overzicht")
    if back.count():
        b.click(back.first)
        page.wait_for_timeout(2500)
        b.observe()
    else:
        advance(b)
    return b.done(b.current_step() == "Export")


# --- 6. an error corrected from the final overview ----------------------------------


def task_6(page) -> object:
    b = Bench(page, "6", "An error corrected from the final overview")
    new_shipment(page)
    fill_line(b, 0, "Stalen plaat 2000x1000x10", 4)
    b.click(page.get_by_role("button", name="Doorgaan"))
    page.wait_for_timeout(3000)
    b.observe()
    # The required fields stay empty on purpose: this task is about what the
    # export step then says, and how far it is from the field that says it.
    # Walking on with them empty now takes two presses — the form says what is
    # still empty before it walks on — and the second press has its own label.
    for _ in range(12):
        if b.current_step() == "Export":
            break
        nxt = page.get_by_role("button", name=ANYWAY)
        if not nxt.count():
            nxt = page.get_by_role("button", name=FORWARD)
        if not nxt.count():
            break
        b.click(nxt.last)
        page.wait_for_timeout(2200)
        b.observe()
    b.m.actions = 0
    b.m.windows = 0
    b.m.notes.clear()
    b.shot("overview")
    chips = missing_chips(page)
    b.note(f"{chips.count()} missing field(s) named on the export step, each of them a button")
    pills = page.locator("nav[aria-label='Wizard voortgang'] li")
    clickable = pills.evaluate_all(
        "els => els.filter(e => e.querySelector('button, a') || e.tagName === 'BUTTON').length")
    b.note(f"{clickable} of {pills.count()} main step pills can be clicked to go back")
    if not chips.count():
        b.note("nothing was named as missing, so there was nothing to correct")
        return b.done(False)
    # One error, corrected: the baseline could not do that — it had to walk back
    # and cross the whole form again, which is what its eleven actions bought.
    corrected = answer_from_chip(b, chips.first)
    b.shot("corrected")
    return b.done(corrected)


# --- 7. an earlier shipment as a new basis -------------------------------------------


def task_7(page, session: requests.Session) -> object:
    b = Bench(page, "7", "An earlier shipment as a new basis")
    page.goto(f"{BASE}/shipments")
    page.wait_for_timeout(3000)
    dismiss_toasts(page)
    b.observe()
    # Since v1.200.0 the three things one does with a kept shipment are on the
    # row itself; the baseline found none of them anywhere but the detail page.
    direct = page.locator("button:visible, a:visible").filter(
        has_text=re.compile("sjabloon|basis|opnieuw|Openen|Documenten", re.I))
    b.note(f"{direct.count()} reuse action(s) on the list itself")
    b.shot("list")
    basis = page.get_by_role("link", name="Als sjabloon gebruiken")
    if not basis.count():
        b.note("no way to start a new shipment from this one on the list")
        return b.done(False)
    b.click(basis.first)
    page.wait_for_timeout(4500)
    b.observe()
    b.shot("as-basis")
    b.note(f"the copy lands on {page.url.split('127.0.0.1:8765')[-1]}")
    # What a copy must not carry over: the old shipment's identity.
    reference = page.locator("#field-shipment_reference")
    b.note("the copy's own reference field: "
           + (f"'{reference.input_value()}'" if reference.count() else "not on this step"))
    return b.done("wizard" in page.url and "template=" in page.url)


# --- 8. a reload during entry ----------------------------------------------------------


def task_8(page, mode: str = "organisation") -> object:
    b = Bench(page, "8", f"A reload during entry ({mode})")
    new_shipment(page)
    fill_line(b, 0, "Stalen hoekprofiel 80x80x8x6000", 8)
    b.click(page.get_by_role("button", name="Doorgaan"))
    page.wait_for_timeout(4000)
    b.observe()
    before = b.current_step()
    # The draft is written a few seconds after the typing stops; a reload one
    # second later is a different measurement than the one this task is about.
    page.wait_for_timeout(4000)
    page.reload()
    page.wait_for_timeout(4500)
    dismiss_toasts(page)
    after = b.current_step()
    b.note(f"before the reload the wizard was on {before or 'unknown'}; after it is on {after or 'unknown'}")
    said = page.get_by_text(re.compile("Concept|concept"))
    b.note(f"what the screen says about the entry: "
           f"{said.first.inner_text() if said.count() else 'nothing'}")
    # The goods themselves: one press on the step the user has already been on.
    goods = page.get_by_role("button", name="Goederen")
    if goods.count():
        b.click(goods.first)
        page.wait_for_timeout(2000)
        b.observe()
    typed = page.get_by_label(re.compile("Omschrijving van regel 1"))
    kept = typed.input_value() if typed.count() else ""
    b.note(f"the typed description after the reload: {kept or 'gone'}")
    b.shot("reloaded")
    return b.done("hoekprofiel" in kept.lower() and after == before)


def task_8_open(page, session: requests.Session) -> object:
    """The same reload where nothing may be stored.

    Release 115 is where the promise "nothing is kept" has to hold *and* the
    user has to be able to keep their own work. The measurement is therefore
    not "did it survive" — it must not — but "was the user warned, and were
    they given the draft".
    """
    b = Bench(page, "8b", "A reload during entry (nothing stored)")
    # The switch is refused while kept shipments are in the table — off means
    # off — so the measurement starts from an installation that holds none.
    session.post(f"{BASE}/api/settings/instance/history/discard")
    history(session, False)
    try:
        new_shipment(page)
        fill_line(b, 0, "Stalen hoekprofiel 80x80x8x6000", 8)
        page.wait_for_timeout(2500)
        dismiss_toasts(page)
        said = page.get_by_text(re.compile("bewaart niets"))
        b.note("the screen says nothing is stored: "
               + (said.first.inner_text() if said.count() else "it does not"))
        offers = page.get_by_role("button", name=re.compile("Concept downloaden|Concept openen"))
        b.note(f"{offers.count()} way(s) to keep the draft yourself")
        b.shot("nothing-stored")
        return b.done(said.count() > 0 and offers.count() == 2)
    finally:
        history(session, True)
        seed(session)


# --- 9. five shipments into one trip ----------------------------------------------------


def task_9(page, session: requests.Session) -> object:
    b = Bench(page, "9", "Five shipments into one trip")
    page.goto(f"{BASE}/shipments")
    page.wait_for_timeout(3000)
    dismiss_toasts(page)
    b.observe()
    boxes = page.locator("table input[type=checkbox]:visible")
    b.note(f"{boxes.count()} shipment(s) on the list can be selected")
    picked = 0
    for index in range(min(5, boxes.count())):
        b.click(boxes.nth(index))
        picked += 1
    b.shot("selected")
    to_trip = page.get_by_role("link", name=re.compile("^Aan een rit toevoegen"))
    if not to_trip.count():
        b.note("the selection led nowhere: no way to make a trip of it")
        return b.done(False)
    b.click(to_trip.first)
    page.wait_for_timeout(6000)
    b.observe()
    dismiss_toasts(page)
    on_board = page.get_by_label("Naam van de zending")
    b.m.output["added"] = on_board.count()
    b.note(f"{picked} selected on the list, {on_board.count()} on the trip, "
           "in one action from the list")
    b.shot("trip")
    return b.done(on_board.count() >= 5)


# --- 10. recovering from a refused save --------------------------------------------------


def task_10(page, session: requests.Session) -> object:
    b = Bench(page, "10", "A refused save recovered without losing entry")
    new_shipment(page)
    fill_line(b, 0, "Stalen plaat 2000x1000x10", 4)
    advance(b)
    b.m.actions = 0
    b.m.windows = 0
    b.m.notes.clear()
    keep = page.get_by_role("button", name=re.compile("bewaren|opslaan", re.I))
    if not keep.count():
        b.note("no save action was visible on the export step")
        b.shot("no-save")
        return b.done(False)
    page.route("**/api/shipments", lambda route: route.fulfill(
        status=500, content_type="application/json", body='{"detail":"opslag geweigerd"}'))
    b.click(keep.first)
    page.wait_for_timeout(3500)
    b.observe()
    still_there = page.get_by_text(re.compile("Plaat|Stalen plaat")).count()
    snack = page.locator(".fixed.inset-x-0.bottom-0")
    told = snack.inner_text().strip() if snack.count() else ""
    b.note(f"the entry is still on screen after the refusal: {still_there > 0}")
    b.note(f"what the user is told: {told[:140] or 'nothing visible'}")
    b.shot("refused-save")
    page.unroute("**/api/shipments")
    return b.done(still_there > 0)


def seed(session: requests.Session, count: int = 6) -> None:
    """Earlier shipments, so tasks 7 and 9 have something to reuse."""
    if len(session.get(f"{BASE}/api/shipments").json().get("items", [])) >= count:
        return
    for n in range(count):
        values = {"reference": f"CP-2026-{100 + n}", "consignor_name": "Mooiweer BV",
                  "consignor_address": "Havenweg 1, Rotterdam", "consignee_name": "Klant NV",
                  "loading_point": "Rotterdam", "discharge_point": "Antwerpen"}
        product = {"un_number": "1203", "proper_shipping_name": "BENZINE", "class": "3",
                   "packing_group": "II", "transport_category": "2",
                   "adr_total_quantity": "100 L", "quantity_packages": "4",
                   "type_of_package": "jerrycans"}
        session.post(f"{BASE}/api/shipments", json={
            "modality": "road", "language": "nl", "profiles": ["ADR"], "values": values,
            "lines": [{"description": "Vaten benzine", "quantity": 4, "weight_total_kg": 100.0}],
            "dangerous_goods": [{"line_id": "1", "products": [product]}],
            "documents": ["cmr"],
            "snapshot": {"version": 1, "stepKey": "export", "docValues": values}})


def main() -> None:
    session = sign_in()
    history(session, True)
    seed(session)
    measurements = []
    with sync_playwright() as playwright:
        engine, context = browser(playwright, session)
        page = context.new_page()
        plan = [
            ("task_1", lambda: task_1(page)),
            ("task_2", lambda: task_2(page)),
            ("task_3", lambda: task_3(page)),
            ("task_4", lambda: task_4(page)),
            ("task_5", lambda: task_5(page, session)),
            ("task_6", lambda: task_6(page)),
            ("task_7", lambda: task_7(page, session)),
            ("task_8", lambda: task_8(page, "organisation")),
            ("task_8_open", lambda: task_8_open(page, session)),
            ("task_9", lambda: task_9(page, session)),
            ("task_10", lambda: task_10(page, session)),
        ]
        for name, run in plan:
            try:
                measurements.append(run())
                print(f"-- {name} done")
            except Exception as exc:
                print(f"!! {name}: {str(exc)[:200]}")
        engine.close()
    write(measurements)


if __name__ == "__main__":
    main()
