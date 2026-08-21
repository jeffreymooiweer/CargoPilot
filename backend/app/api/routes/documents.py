import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import (
    BundleMailResult,
    DocumentBundleMailRequest,
    DocumentBundleRequest,
    DocumentExportRequest,
    UnCardsRequest,
)
from app.services import mail
from app.services.documents import (
    build_un_cards_zip,
    fill_pdf_document,
    get_document,
    get_registry,
    has_pdf_template,
    render_document_pdf,
    un_card_count,
    un_cards_availability,
    validate_document,
)
from app.services import regulations
from app.services.documents.un_card_store import card_path as un_card_path
from app.services.documents.avc_form import fill_avc_waybill, has_avc_template
from app.services.documents.carrier_confirmation import parse_carrier_confirmation
from app.services.documents.onboard_pack import (
    render_onboard_documents,
    render_packing_certificate,
)
from app.services.documents.equipment_sheet import render_equipment_sheet
from app.services.documents.placarding_sheet import render_placarding_sheet
from app.services.documents.stowage_plan import render_stowage_plan
from app.services.documents.signature import decode_signature_image
from app.services.settings_store import instance_settings

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/registry")
def document_registry(user: User = Depends(get_current_user)):
    return get_registry()


@router.post("/carrier-confirmation")
def read_carrier_confirmation(
    payload: dict,
    user: User = Depends(get_current_user),
):
    """The carrier-assigned references found in a pasted booking confirmation.

    Reading only — nothing is stored and no field is written here. The
    interface decides what to do with the findings, and it fills only fields
    that are still empty, so nothing a user typed is ever overwritten. Keys
    the text does not support are absent, never defaulted.
    """
    text = str(payload.get("text") or "")
    if len(text) > 100_000:
        raise HTTPException(status_code=413, detail="confirmation text too large")
    return {"found": parse_carrier_confirmation(text)}


@router.post("/validate")
def validate(payload: DocumentExportRequest, user: User = Depends(get_current_user)):
    document = get_document(payload.document_key)
    if document is None:
        raise HTTPException(status_code=404, detail="Unknown document")
    errors, warnings = validate_document(
        document, payload.values, payload.lines, payload.dangerous_goods, payload.output_language
    )
    return {"document_key": payload.document_key, "errors": errors, "warnings": warnings}


def _render_export(document: dict, payload: DocumentExportRequest,
                   signature_png: bytes | None) -> "Path":
    """One document as a file, by its registered exporter.

    The single export and the bundle both come through here, so the archive
    can never contain a different rendering than the per-document button
    hands out.
    """
    exporter = document.get("exporter")
    if exporter == "pdf_template" and has_pdf_template(payload.document_key):
        # Officieel, invulbaar formulier: template invullen.
        out_path = fill_pdf_document(
            payload.document_key,
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
            signature_png=signature_png,
        )
    elif exporter == "avc" and has_avc_template():
        # AVC waybill: filling in the official sVa form. That form has no
        # AcroForm fields, so the values go on as a text layer over the
        # template.
        out_path = fill_avc_waybill(
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
            signature_png=signature_png,
        )
    elif exporter == "placarding":
        # The placarding sheet is not a form to fill in: it is the answer
        # chapter 5.3 gives for this consignment, printed. Nothing on it is
        # typed by the user, so it is built from the goods rather than from
        # the document's fields.
        out_path = render_placarding_sheet(
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
        )
    elif exporter == "placarding_adn":
        # The same sheet with the water's own chapter 5.3 answering: what the
        # cargo transport units on board must show, per kind of unit.
        out_path = render_placarding_sheet(
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
            regime="ADN",
        )
    elif exporter == "placarding_rid":
        # And with the rail's chapter answering: package wagons placard for
        # every class, the orange plates attach only via column (20).
        out_path = render_placarding_sheet(
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
            regime="RID",
        )
    elif exporter == "stowage":
        # The stowage plan is drawn from where the goods are, not from typed
        # document fields: 7.1.4.11.1 asks which goods are in which hold, and
        # the description is the transport document's own.
        out_path = render_stowage_plan(
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
        )
    elif exporter == "equipment":
        # The 8.1.4/8.1.5 list as paper: derived from the labels of the load,
        # ticked at the vehicle and never beforehand.
        out_path = render_equipment_sheet(
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
        )
    elif exporter == "packing_certificate":
        # The certificate of 5.4.2: the model with nothing pre-ticked. Every
        # declaration concerns what was established at packing.
        out_path = render_packing_certificate(
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
        )
    elif exporter in ("onboard_adr", "onboard_adn"):
        # The list of 8.1.2, split by who can produce each paper: what this
        # application drew up, and what has to be brought.
        out_path = render_onboard_documents(
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
            regime="ADN" if exporter == "onboard_adn" else "ADR",
        )
    else:
        # Self-designed document: generate a clean PDF.
        out_path = render_document_pdf(
            document,
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
            signature_png=signature_png,
        )
    return out_path


def _decoded_signature(signature_image: str | None) -> bytes | None:
    if not signature_image:
        return None
    try:
        return decode_signature_image(signature_image)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/export")
def export(
    payload: DocumentExportRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    document = get_document(payload.document_key)
    if document is None:
        raise HTTPException(status_code=404, detail="Unknown document")
    errors, _warnings = validate_document(
        document, payload.values, payload.lines, payload.dangerous_goods, payload.output_language
    )
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    signature_png = _decoded_signature(payload.signature_image)
    ref = datetime.now().strftime("%Y%m%d%H%M%S")
    out_path = _render_export(document, payload, signature_png)
    background_tasks.add_task(_delete_file, out_path)
    return FileResponse(
        path=out_path,
        filename=f"{payload.document_key}_{ref}.pdf",
        media_type="application/pdf",
    )


def _build_bundle(payload: DocumentBundleRequest, db: Session) -> tuple[Path, str]:
    """The archive itself, for whoever wants to do something with it.

    Downloading and mailing must produce the same bundle — one built by the
    endpoint and one assembled beside it would drift, and the difference
    would show up as a document that is in the download and not in the mail.
    Returns the path and the timestamp reference used in the file names; the
    caller owns the file from then on.
    """
    if not payload.documents:
        raise HTTPException(status_code=422, detail="Nothing to bundle")

    signature_png = _decoded_signature(payload.signature_image)
    ref = datetime.now().strftime("%Y%m%d%H%M%S")
    notes: list[str] = []
    produced: list[tuple[Path, str]] = []

    try:
        for item in payload.documents:
            document = get_document(item.document_key)
            if document is None:
                notes.append(f"{item.document_key}: unknown document, not included")
                continue
            errors, _warnings = validate_document(
                document, item.values, item.lines,
                item.dangerous_goods, item.output_language,
            )
            if errors:
                notes.append(f"{item.document_key}: not included, still incomplete: "
                             + "; ".join(str(e) for e in errors[:3]))
                continue
            out_path = _render_export(document, item, signature_png)
            produced.append((out_path, f"{item.document_key}_{ref}.pdf"))

        if not produced:
            raise HTTPException(
                status_code=422,
                detail={"errors": notes or ["No document could be produced"]})

        fd, name = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        bundle_path = Path(name)
        try:
            _fill_bundle(bundle_path, produced, payload, notes, db)
        except BaseException:
            _delete_file(bundle_path)
            raise
    finally:
        for path, _ in produced:
            _delete_file(path)

    return bundle_path, ref


@router.post("/export/bundle")
def export_bundle(
    payload: DocumentBundleRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Every ready paper of the export step in one archive.

    The documents are rendered by the same code path as the per-document
    buttons; the UN cards and the instructions in writing for the journey's
    regimes ride along. What cannot be included is written down in the
    archive's README rather than silently dropped — a bundle that looks
    complete and is not would be worse than no bundle.
    """
    bundle_path, ref = _build_bundle(payload, db)
    background_tasks.add_task(_delete_file, bundle_path)
    return FileResponse(
        path=bundle_path,
        filename=f"cargopilot-documents-{ref}.zip",
        media_type="application/zip",
    )


@router.post("/export/bundle/mail", response_model=BundleMailResult)
def mail_bundle(
    payload: DocumentBundleMailRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The same archive, sent instead of downloaded.

    Same bundle, same rules: it is built by :func:`_build_bundle`, so what
    arrives in the mail is what the download button produces, README and all.
    The archive is deleted as soon as the message is out — CargoPilot keeps
    no copy of a consignment's papers.
    """
    settings = instance_settings(db)
    if not mail.is_configured(settings):
        raise HTTPException(
            status_code=400,
            detail="No mail server is configured. An administrator sets one "
                   "under Settings, Administration, Mail server.")

    bundle_path, ref = _build_bundle(payload.bundle, db)
    try:
        content = bundle_path.read_bytes()
        filename = f"cargopilot-documents-{ref}.zip"
        body = payload.message.strip() or _default_mail_body(user)
        try:
            mail.send(settings, payload.to, payload.subject.strip() or
                      f"CargoPilot documents {ref}", body,
                      [(filename, content, "application/zip")])
        except mail.MailError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        _delete_file(bundle_path)
    return BundleMailResult(ok=True, to=payload.to, filename=filename)


def _default_mail_body(user: User) -> str:
    """What to write when the sender wrote nothing.

    Named rather than anonymous: the recipient is a carrier or a consignee
    who has to know who sent them a consignment's papers.
    """
    return (
        f"The transport documents for this consignment are attached, "
        f"sent from CargoPilot by {user.username}.\n"
    )


def _fill_bundle(bundle_path: Path, produced: list[tuple[Path, str]],
                 payload: DocumentBundleRequest, notes: list[str],
                 db: Session) -> None:
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, arcname in produced:
            archive.write(path, arcname=arcname)

        if payload.include_un_cards and payload.dangerous_goods:
            cards = un_cards_availability(payload.dangerous_goods,
                                          payload.profiles)
            if instance_settings(db).un_cards_enabled and cards["cards"]:
                for card in cards["cards"]:
                    path = un_card_path(card["un_number"], card["modality"])
                    if path is not None:
                        archive.write(path, arcname=f"un-cards/{path.name}")
                for un in cards["missing"]:
                    notes.append(f"UN {un}: no card held for the selected regimes")
            elif cards["requested"]:
                notes.append("UN cards: no card set is installed on this server")

        if payload.include_instructions and payload.dangerous_goods:
            language = (payload.output_language or "nl").lower()
            for profile in payload.profiles:
                regime = str(profile).strip().lower()
                if regime not in regulations.REGIMES:
                    continue
                status = regulations.instruction_status(regime, language)
                if status.get("available"):
                    pdf = regulations.instructions_pdf(regime, language)
                    if pdf is not None:
                        archive.write(
                            pdf,
                            arcname=f"instructions/{regime}-instructions-{language}.pdf")
                        continue
                notes.append(
                    f"instructions in writing ({regime.upper()}, {language}): "
                    "not on this server — the model is served only as the "
                    "edition prints it")

        if notes:
            archive.writestr(
                "README.txt",
                "Not everything could be included:\n\n"
                + "".join(f"  - {note}\n" for note in notes))


@router.get("/instructions")
def instructions_overview(user: User = Depends(get_current_user)):
    """What this installation can hand a driver or a boatmaster under 5.4.3.

    Per regime and language, because the model is only ever offered as the
    edition prints it: a language the store cannot produce is reported as
    missing with the document that would produce it, never filled in from a
    neighbouring language.
    """
    return {"documents": [
        regulations.instruction_status(doc["model_of"]["regime"],
                                       doc["model_of"]["language"])
        for doc in regulations.instruction_documents()]}


@router.get("/instructions/{regime}/{language}")
def instructions_file(regime: str, language: str,
                      user: User = Depends(get_current_user)):
    if regime not in regulations.REGIMES or language not in regulations.LANGUAGES:
        raise HTTPException(status_code=404, detail="Unknown regime or language")
    status = regulations.instruction_status(regime, language)
    if not status.get("available"):
        raise HTTPException(status_code=409, detail=status)
    path = regulations.instructions_pdf(regime, language)
    if path is None:  # pragma: no cover - the status said it was there
        raise HTTPException(status_code=409, detail=status)
    return FileResponse(
        path, media_type="application/pdf",
        filename=f"{regime}-2025-instructions-{language}.pdf")


@router.get("/models/{provision}")
def models_overview(provision: str, user: User = Depends(get_current_user)):
    """What this installation can hand over for one prescribed model.

    The instructions in writing were the first; ADN 8.6.3 — the checklist a
    tank vessel fills in before loading or unloading — is another. Both are
    printed by the regulation rather than described by it, and both are served
    as the edition prints them or reported as missing. Nothing here paraphrases
    a model, and nothing fills one in.
    """
    if provision not in regulations.model_provisions():
        raise HTTPException(status_code=404, detail="No model for that provision")
    return {"provision": provision, "documents": [
        regulations.instruction_status(doc["model_of"]["regime"],
                                       doc["model_of"]["language"], provision)
        for doc in regulations.instruction_documents(provision)]}


@router.get("/models/{provision}/{regime}/{language}")
def model_file(provision: str, regime: str, language: str,
               user: User = Depends(get_current_user)):
    if regime not in regulations.REGIMES or language not in regulations.LANGUAGES:
        raise HTTPException(status_code=404, detail="Unknown regime or language")
    if provision not in regulations.model_provisions():
        raise HTTPException(status_code=404, detail="No model for that provision")
    status = regulations.instruction_status(regime, language, provision)
    if not status.get("available"):
        raise HTTPException(status_code=409, detail=status)
    path = regulations.instructions_pdf(regime, language, provision)
    if path is None:  # pragma: no cover - the status said it was there
        raise HTTPException(status_code=409, detail=status)
    return FileResponse(
        path, media_type="application/pdf",
        filename=f"{regime}-2025-{provision.replace('.', '-')}-{language}.pdf")


@router.post("/un-cards/availability")
def un_cards_status(
    payload: UnCardsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Which UN cards this shipment can be given, before offering the download."""
    status = un_cards_availability(payload.dangerous_goods, payload.profiles)
    if not instance_settings(db).un_cards_enabled:
        # Switched off for this installation. Reported the same way as a missing
        # card library, so the wizard simply does not offer the download.
        return {**status, "enabled": False, "available": [], "count": 0, "library_size": 0}
    return {**status, "library_size": un_card_count()}


@router.post("/un-cards")
def export_un_cards(
    payload: UnCardsRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A zip with the UN cards for the substances in this shipment."""
    if not instance_settings(db).un_cards_enabled:
        raise HTTPException(status_code=404, detail="UN cards are disabled for this installation")
    try:
        out_path, status = build_un_cards_zip(payload.dangerous_goods, payload.profiles)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    background_tasks.add_task(_delete_file, out_path)
    ref = datetime.now().strftime("%Y%m%d%H%M%S")
    return FileResponse(
        path=out_path,
        filename=f"un_cards_{ref}.zip",
        media_type="application/zip",
        headers={"X-UN-Cards-Count": str(status["count"])},
    )


def _delete_file(path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
