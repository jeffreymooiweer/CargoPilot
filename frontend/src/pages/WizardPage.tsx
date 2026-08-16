import { useEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate, useParams } from "react-router";
import { useTranslation } from "react-i18next";
import {
  api,
  CalcResult,
  DgEntry,
  DocumentDefinition,
  DocumentExportPayload,
  DocumentRegistry,
  LocalizedText,
  UnCardsAvailability,
  WrittenInstruction,
  UserPreferences,
} from "../api/client";
import { documentLanguage, localised, LANGUAGE_NAMES, SUPPORTED_LANGUAGES, Language } from "../i18n/language";
import DangerousGoodsStep, { buildDgEntries } from "../components/DangerousGoodsStep";
import DgCompliancePanel from "../components/DgCompliancePanel";
import DocumentWarnings, { useDocumentValidation } from "../components/DocumentWarnings";
import AiIcon from "../components/AiIcon";
import AssistantModal from "../components/AssistantModal";
import DocumentFieldsStep, { resolveSections } from "../components/DocumentFieldsStep";
import DocumentAdvicePanel, { buildAdvice } from "../components/DocumentAdvicePanel";
import ImportDialog from "../components/ImportDialog";
import ReviewLinesPanel, { DraftLine, draftToText, textToDraftLines } from "../components/ReviewLinesPanel";
import WizardProgress from "../components/WizardProgress";
import { isModalityAvailable } from "./ModalitySelectPage";
import { usePreferences } from "../settings/preferences";
import {
  applyLineWeightChange,
  recalcTotals,
  scaleLinesToTotalWeight,
  weightOverridesFromLines,
  dimensionOverridesFromDrafts,
  mergeOverrides,
} from "../utils/lineWeights";

const weightInputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const buttonSecondary =
  "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 min-h-[44px] text-sm";
const buttonPrimary =
  "bg-brand-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";

type StepKey = "lines" | "dg" | "details" | "export";

/** Dates that mean "drawn up today" and may therefore start as today. The
 *  operational dates (loading, requested departure) are facts of the trip and
 *  are never guessed. */
const TODAY_DATE_FIELDS = new Set([
  "established_date",
  "declaration_date",
  "document_date",
  "determination_date",
]);

const LAST_SHIPMENT_KEY = "cargopilot:last-shipment";

type DocStatus = "ready" | "draft" | "blocked" | "not_applicable";

const DG_BASE_REQUIRED = ["un_number", "proper_shipping_name", "class"] as const;
const DG_PROFILE_REQUIRED: Record<string, string[]> = {
  ADR: [...DG_BASE_REQUIRED],
  RID: [...DG_BASE_REQUIRED],
  ADN: [...DG_BASE_REQUIRED],
  IMDG: [...DG_BASE_REQUIRED, "quantity_packages", "type_of_package"],
  IATA_DGR: [
    ...DG_BASE_REQUIRED,
    "packing_instruction",
    "quantity_packages",
    "type_of_package",
    "net_mass_liters_per_package",
  ],
};

const DG_EXTRA_FIELDS: Record<string, string[]> = {
  // The mode comes first because it decides what the rest of the answers mean:
  // admission, the tunnel code and the placarding all branch on it, and until
  // v1.66.0 a tank load silently got the answers for packages.
  // The tank's own code comes straight after the mode that makes it relevant:
  // column (12) says which code the substance requires, and ADR 4.3 decides
  // whether the tank standing on the yard may carry it. The field only shows
  // once the mode says a tank is involved.
  // The tank's own code, then what 4.3.2.2 needs to say how full it may be.
  // All four only show once the mode says a tank is involved.
  // The three special cases of 5.4.1.1.3/.5/.6 change what the description
  // line must say, and none of them is derivable from the UN number: whether
  // the goods are waste is a fact about the consignment.
  ADR: ["carriage_mode", "tank_code", "filling_temperature", "density_15",
        "density_50", "transport_category", "adr_total_quantity",
        "is_waste", "empty_uncleaned", "salvage_packaging",
        "molten", "residue_classes", "classified_2_1_2_8"],
  RID: ["carriage_mode", "transport_category", "adr_total_quantity",
        "is_waste", "empty_uncleaned", "salvage_packaging",
        "molten", "residue_classes", "classified_2_1_2_8"],
  // Where it goes on the vessel: 7.1.4.11.1 asks the boatmaster to say which
  // goods are in which hold or on deck, and no table can answer that.
  ADN: ["carriage_mode", "hold", "container_number", "containers_only",
        "transport_category", "adr_total_quantity", "is_waste",
        "empty_uncleaned", "salvage_packaging", "molten", "residue_classes",
        "classified_2_1_2_8"],
  IMDG: ["technical_name", "marine_pollutant", "ems_code", "emergency_contact"],
  IATA_DGR: [
    "technical_name",
    "cargo_aircraft_only",
    "overpack",
    "emergency_contact",
    "q_net_quantity",
    "q_max_net_quantity",
  ],
};

/** Which saved detail belongs in which document field.
 *
 * The consignor, the haulier and the loading point are the same on nearly every
 * consignment the same person makes, and were retyped every time. Only empty
 * fields are filled: a prefill that overwrites what someone just typed is worse
 * than no prefill at all. */
const PREFILL_FIELDS: Record<string, keyof UserPreferences> = {
  consignor_name: "consignor_name",
  consignor_address: "consignor_address",
  consignor_contact: "consignor_contact",
  carrier_name: "carrier_name",
  loading_point: "loading_point",
};

const MODALITY_DG_PROFILES: Record<string, string[]> = {
  road: ["ADR"],
  rail: ["RID"],
  inland: ["ADN"],
  sea: ["IMDG"],
  air: ["IATA_DGR"],
  multimodal: ["ADR", "IATA_DGR", "IMDG"],
};

export default function WizardPage() {
  const { t, i18n } = useTranslation();
  const { modality } = useParams();
  const lang = documentLanguage(i18n.language);
  const L = (text?: LocalizedText) => localised(text, lang);
  // The language the documents are drawn up in is not the language the screen
  // is in. ADR 5.4.1.4.1 (and RID and ADN in the same words) asks for an
  // official language of the forwarding country and, where that is not German,
  // English or French, additionally one of those three — which is about the
  // consignment, not about who is typing. So it is a choice, defaulting to the
  // screen's language because that is right more often than not.
  const [chosenDocLang, setChosenDocLang] = useState<Language | null>(null);
  const docLang = chosenDocLang ?? lang;
  const { preferences, loaded: preferencesLoaded } = usePreferences();
  const prefill = preferencesLoaded && preferences.prefill_documents;

  const [registry, setRegistry] = useState<DocumentRegistry | null>(null);
  const [registryError, setRegistryError] = useState("");
  const [stepKey, setStepKey] = useState<StepKey>("lines");
  // null means "the advice decides": the selection follows the shipment until
  // the user touches it, and from that moment it is theirs.
  const [selectedDocs, setSelectedDocs] = useState<string[] | null>(null);
  const [docValues, setDocValues] = useState<Record<string, string>>({});
  const [draftLines, setDraftLines] = useState<DraftLine[]>([{ id: 1, description: "", quantity: 1, unit: "pcs" }]);
  const [nextId, setNextId] = useState(2);
  const [result, setResult] = useState<CalcResult | null>(null);
  const [dgEntries, setDgEntries] = useState<DgEntry[]>([]);
  const [signature, setSignature] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exportingDoc, setExportingDoc] = useState<string | null>(null);
  const [unCards, setUnCards] = useState<UnCardsAvailability | null>(null);
  const [instructions, setInstructions] = useState<WrittenInstruction[]>([]);
  const [checklist, setChecklist] = useState<WrittenInstruction[]>([]);
  const [unCardsBusy, setUnCardsBusy] = useState(false);
  const [error, setError] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);

  useEffect(() => {
    api
      .documentsRegistry()
      .then(setRegistry)
      .catch((e) => setRegistryError(String(e)));
  }, []);

  // The saved details land in the form as soon as they arrive, and only in
  // fields that are still empty — the preferences come back over the network,
  // so someone may already have started typing by then.
  useEffect(() => {
    if (!prefill) return;
    setDocValues((current) => {
      const filled = { ...current };
      for (const [field, key] of Object.entries(PREFILL_FIELDS)) {
        const value = String(preferences[key] ?? "");
        if (value && !(filled[field] ?? "").trim()) filled[field] = value;
      }
      return filled;
    });
  }, [prefill, preferences]);

  // A signature that was drawn once in the settings. Never overwrites one drawn
  // for this shipment.
  useEffect(() => {
    if (prefill && preferences.signature_image) {
      setSignature((current) => current ?? preferences.signature_image);
    }
  }, [prefill, preferences.signature_image]);

  // The previous shipment's details, saved at export. The same consignor ships
  // to the same handful of parties; retyping them every ride was the details
  // step's whole cost. Dates stay out: last week's date on today's document
  // would be a wrong answer prefilled.
  const [lastShipment] = useState<Record<string, string> | null>(() => {
    try {
      return JSON.parse(localStorage.getItem(LAST_SHIPMENT_KEY) ?? "null");
    } catch {
      return null;
    }
  });
  const reuseLastShipment = () => {
    if (!lastShipment) return;
    setDocValues((current) => {
      const filled = { ...current };
      for (const [key, value] of Object.entries(lastShipment)) {
        if (key.endsWith("_date") || !String(value ?? "").trim()) continue;
        if (!(filled[key] ?? "").trim()) filled[key] = String(value);
      }
      return filled;
    });
  };

  // The discharge point defaults to the consignee's own address line the
  // moment the details step is done — only while the user typed nothing else,
  // and visibly editable on the way back.
  const completeDetails = () => {
    setDocValues((current) => {
      if ((current.discharge_point ?? "").trim() || !(current.consignee_address ?? "").trim()) {
        return current;
      }
      const lines = current.consignee_address
        .split(/\n/)
        .map((line) => line.trim())
        .filter(Boolean);
      const place = lines[lines.length - 1];
      return place ? { ...current, discharge_point: place } : current;
    });
    setStepKey("export");
  };

  // A blank starting line still carries the default unit; the moment something
  // has been typed it is left alone.
  useEffect(() => {
    if (!preferencesLoaded || !preferences.default_unit) return;
    setDraftLines((lines) =>
      lines.some((line) => line.description.trim())
        ? lines
        : lines.map((line) => ({ ...line, unit: preferences.default_unit })),
    );
  }, [preferencesLoaded, preferences.default_unit]);

  const modalityDef = registry?.modalities.find((m) => m.key === modality);

  const needsDg = useMemo(
    () =>
      result?.lines.some(
        (line) =>
          line.include &&
          (line.dangerous_goods || (line.detected_un_numbers?.length ?? 0) > 0),
      ) ?? false,
    [result],
  );

  // The advice assembles the document set from the shipment; the user adjusts
  // it on the export step. Until they do, the selection follows the shipment —
  // a DG line appearing pulls the transport document and the DG papers in.
  const advice = useMemo(
    () => (registry && modalityDef ? buildAdvice(registry, modalityDef.key, needsDg) : null),
    [registry, modalityDef, needsDg],
  );
  const selected = selectedDocs ?? advice?.preselected ?? [];

  const selectedDefinitions = useMemo(
    () =>
      selected
        .map((key) => registry?.documents.find((d) => d.key === key))
        .filter((d): d is DocumentDefinition => !!d),
    [selected, registry],
  );

  const genericDocs = selectedDefinitions;

  // "Drawn up on" dates start as today — that is what they mean — and each
  // field is defaulted at most once, so a date the user deliberately cleared
  // stays cleared. The operational dates (loading, departure) are facts of
  // the trip and never guessed.
  const datesDefaulted = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (!registry) return;
    const today = new Date().toISOString().slice(0, 10);
    setDocValues((current) => {
      const filled = { ...current };
      let changed = false;
      for (const doc of selectedDefinitions) {
        for (const section of resolveSections(doc, registry)) {
          for (const field of section.fields ?? []) {
            if (
              field.type === "date" &&
              TODAY_DATE_FIELDS.has(field.key) &&
              !datesDefaulted.current.has(field.key) &&
              !(filled[field.key] ?? "").trim()
            ) {
              filled[field.key] = today;
              datesDefaulted.current.add(field.key);
              changed = true;
            }
          }
        }
      }
      return changed ? filled : current;
    });
  }, [registry, selectedDefinitions]);

  const dgProfiles = useMemo(() => {
    const profiles = new Set<string>(MODALITY_DG_PROFILES[modality ?? ""] ?? []);
    for (const doc of selectedDefinitions) {
      if (doc.dg_profile) profiles.add(doc.dg_profile);
    }
    return [...profiles];
  }, [selectedDefinitions, modality]);

  const dgExtraFields = useMemo(() => {
    const fields: string[] = [];
    for (const profile of dgProfiles) {
      for (const field of DG_EXTRA_FIELDS[profile] ?? []) {
        if (!fields.includes(field)) fields.push(field);
      }
    }
    return fields;
  }, [dgProfiles]);

  const steps: StepKey[] = useMemo(() => {
    const list: StepKey[] = ["lines"];
    if (needsDg) list.push("dg");
    if (genericDocs.length > 0) list.push("details");
    list.push("export");
    return list;
  }, [needsDg, genericDocs.length]);

  const stepLabels: Record<StepKey, string> = {
    lines: t("wizard.step2"),
    dg: t("wizard.step3dg"),
    details: t("wizard.stepDetails"),
    export: t("wizard.step4"),
  };

  const stepPills = steps.map((key, index) => ({ n: index + 1, key, label: stepLabels[key] }));
  const currentIndex = Math.max(0, steps.indexOf(stepKey));

  const goNextFrom = (from: StepKey) => {
    const index = steps.indexOf(from);
    const next = steps[index + 1];
    if (next) setStepKey(next);
  };

  const goBackFrom = (from: StepKey) => {
    const index = steps.indexOf(from);
    const prev = steps[Math.max(0, index - 1)];
    if (prev) setStepKey(prev);
  };

  // Not only "is this a modality" but "may documents be drawn up for it". A
  // bookmark to /wizard/rail is the route that skips every tile.
  if (!isModalityAvailable(modality)) {
    return <Navigate to="/?choose=1" replace />;
  }

  const updateResultLines = (lines: CalcResult["lines"]) => {
    setResult((prev) => (prev ? { ...prev, lines, totals: recalcTotals(lines) } : prev));
  };

  const calculateFromDraft = async (): Promise<CalcResult | null> => {
    const text = draftToText(draftLines);
    if (!text.trim()) {
      setError(t("review.noLines"));
      return null;
    }
    setLoading(true);
    setError("");
    setDgEntries([]);
    try {
      const res = await api.calculate({
        text,
        mode: "continue",
        input_language: null,
        // Dimensions come from the input and therefore have to count towards the
        // very first calculation; weight corrections only exist once there is a
        // result to correct.
        line_overrides: mergeOverrides(
          dimensionOverridesFromDrafts(draftLines),
          result ? weightOverridesFromLines(result.lines) : [],
        ),
      });
      // Apply the DG ticks of the packages (same order as the non-empty lines),
      // and the UN number a user confirmed from a name suggestion: that answer
      // travels to the DG step so nothing recognised is typed twice.
      const flagged = draftLines.filter((l) => l.description.trim());
      const withDg = {
        ...res,
        lines: res.lines.map((line, i) => ({
          ...line,
          dangerous_goods: Boolean(line.dangerous_goods || flagged[i]?.dangerous_goods),
          detected_un_numbers: flagged[i]?.confirmed_un
            ? [
                flagged[i].confirmed_un as string,
                ...(line.detected_un_numbers ?? []).filter((un) => un !== flagged[i].confirmed_un),
              ]
            : line.detected_un_numbers,
        })),
      };
      setResult(withDg);
      return withDg;
    } catch (e) {
      setError(String(e));
      return null;
    } finally {
      setLoading(false);
    }
  };

  /**
   * What was entered, as one string.
   *
   * If this changes, the weight shown is no longer right. Manual weight
   * corrections are deliberately not in it: those are an *answer* to a
   * calculation and would otherwise set themselves off again.
   */
  const signatureOf = (lines: DraftLine[]) =>
    JSON.stringify(
      lines.map((line) => [
        line.description.trim(),
        line.quantity,
        line.unit,
        line.cargo_form ?? "",
        line.length_cm ?? "",
        line.width_cm ?? "",
        line.height_cm ?? "",
        line.wall_thickness_mm ?? "",
      ]),
    );
  const draftSignature = signatureOf(draftLines);

  // Recalculating used to be a button, and a button you have to press to see a
  // correct figure is a button that gets forgotten — with a stale weight on the
  // screen as the result. Now it happens by itself, shortly after the typing
  // stops. The delay is there so as not to send a request on every keystroke.
  const calculatedSignature = useRef<string | null>(null);
  useEffect(() => {
    if (stepKey !== "lines") return;
    if (!draftLines.some((line) => line.description.trim())) return;
    if (calculatedSignature.current === draftSignature) return;

    const timer = setTimeout(() => {
      calculatedSignature.current = draftSignature;
      void calculateFromDraft();
    }, 600);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftSignature, stepKey]);

  const addLine = () => {
    const unit = preferences.default_unit || "pcs";
    setDraftLines((lines) => [...lines, { id: nextId, description: "", quantity: 1, unit }]);
    setNextId((n) => n + 1);
  };

  const removeLine = (id: number) => {
    setDraftLines((lines) => lines.filter((l) => l.id !== id));
    setResult(null);
  };

  const duplicateLine = (id: number) => {
    setDraftLines((lines) => {
      const index = lines.findIndex((l) => l.id === id);
      if (index === -1) return lines;
      const copy: DraftLine = { ...lines[index], id: nextId };
      return [...lines.slice(0, index + 1), copy, ...lines.slice(index + 1)];
    });
    setNextId((n) => n + 1);
    setResult(null);
  };

  const handleImport = (text: string, importMode: "append" | "replace") => {
    if (importMode === "replace") {
      const lines = textToDraftLines(text);
      setDraftLines(lines);
      setNextId(Math.max(...lines.map((l) => l.id), 0) + 1);
    } else {
      const imported = textToDraftLines(text, nextId);
      setNextId((n) => n + imported.length);
      setDraftLines((prev) => [...prev.filter((l) => l.description.trim()), ...imported]);
    }
    setResult(null);
  };

  const handleLineWeightChange = (
    lineId: number,
    field: "weight_each_kg" | "weight_total_kg",
    value: number | null,
  ) => {
    if (!result) return;
    updateResultLines(applyLineWeightChange(result.lines, lineId, field, value));
  };

  const handleTotalWeightChange = (value: number | null) => {
    if (!result || value == null || Number.isNaN(value)) return;
    updateResultLines(scaleLinesToTotalWeight(result.lines, value));
  };

  /** The 24-hour emergency number, which IMDG 5.4.1.5.11 and the IATA DGR
   *  shipper's declaration both ask for. It never changes and was typed again
   *  for every product on every consignment. */
  const withEmergencyContact = (entries: DgEntry[]): DgEntry[] => {
    const contact = prefill ? preferences.emergency_contact : "";
    if (!contact) return entries;
    return entries.map((entry) => ({
      ...entry,
      products: entry.products.map((product) =>
        (product.emergency_contact ?? "").trim() ? product : { ...product, emergency_contact: contact },
      ),
    }));
  };

  const goFromLines = async () => {
    const res = await calculateFromDraft();
    if (!res) return;
    const hasDg = res.lines.some(
      (line) => line.include && (line.dangerous_goods || (line.detected_un_numbers?.length ?? 0) > 0),
    );
    if (hasDg) {
      setDgEntries(withEmergencyContact(buildDgEntries(res.lines)));
      setStepKey("dg");
    } else if (genericDocs.length > 0) {
      setStepKey("details");
    } else {
      setStepKey("export");
    }
  };

  const autoValues = useMemo(
    () => ({
      total_weight_kg: result?.totals.total_weight_kg != null ? String(result.totals.total_weight_kg) : "",
    }),
    [result],
  );

  const exportValuesFor = (doc: DocumentDefinition): Record<string, string> => {
    if (!registry) return docValues;
    const merged = { ...docValues };
    for (const section of resolveSections(doc, registry)) {
      for (const field of section.fields ?? []) {
        if (field.auto_from && !(merged[field.key] ?? "").trim()) {
          const auto = autoValues[field.auto_from as keyof typeof autoValues];
          if (auto) merged[field.key] = auto;
        }
      }
    }
    return merged;
  };

  const docStatus = (doc: DocumentDefinition): { status: DocStatus; missing: string[]; waitingCarrier: boolean } => {
    if (!registry) return { status: "draft", missing: [], waitingCarrier: false };
    if (doc.dg_only && !needsDg) return { status: "not_applicable", missing: [], waitingCarrier: false };
    const values = exportValuesFor(doc);
    const missing: string[] = [];
    let waitingCarrier = false;
    for (const section of resolveSections(doc, registry)) {
      for (const field of section.fields ?? []) {
        const value = (values[field.key] ?? "").trim();
        if (field.status === "USER_REQUIRED" && !value) missing.push(L(field.label));
        if (field.status === "CARRIER_PROVIDED" && !value) waitingCarrier = true;
      }
    }
    if (doc.dg_profile && (doc.dg_only || dgEntries.length > 0)) {
      const required = DG_PROFILE_REQUIRED[doc.dg_profile] ?? [...DG_BASE_REQUIRED];
      const incomplete =
        dgEntries.length === 0 ||
        dgEntries.some((entry) =>
          entry.products.some((product) =>
            required.some((field) => !String(product[field as keyof typeof product] ?? "").trim()),
          ),
        );
      if (incomplete) return { status: "blocked", missing, waitingCarrier };
    }
    if (missing.length > 0) return { status: "draft", missing, waitingCarrier };
    return { status: "ready", missing: [], waitingCarrier };
  };

  // One payload builder for validation and export both, so that what is
  // validated is what is exported by construction. These used to be able to
  // drift — and did: the validate endpoint had no caller at all, so every
  // warning it computed (missing unit, lost exemption, VGM mismatch, eleven
  // more) was thrown away twice over. The signature is export-only; validation
  // does not read it.
  const payloadFor = (doc: DocumentDefinition): DocumentExportPayload => ({
    document_key: doc.key,
    values: exportValuesFor(doc),
    lines: result?.lines ?? [],
    dangerous_goods: dgEntries.length > 0 ? dgEntries : undefined,
    output_language: docLang,
  });

  // Warnings per document, shown on the card before the download button — a
  // warning after the file is on disk is a warning shown too late. This runs
  // whether or not there are dangerous goods: the VGM mass check warns on a
  // plain sea consignment.
  const docWarnings = useDocumentValidation(
    stepKey === "export" && result ? selectedDefinitions.map(payloadFor) : [],
    stepKey === "export" && !!result,
  );

  const exportGenericDoc = async (doc: DocumentDefinition) => {
    if (!result) return;
    setExportingDoc(doc.key);
    setError("");
    try {
      await api.exportDocument({
        ...payloadFor(doc),
        signature_image: signature ?? undefined,
      });
      // What was exported is worth offering next time.
      try {
        localStorage.setItem(LAST_SHIPMENT_KEY, JSON.stringify(docValues));
      } catch {
        // Storage full or blocked: the export succeeded, the memory is a bonus.
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setExportingDoc(null);
    }
  };

  // One click for the whole pack: every selected document that is ready,
  // in order. Drafts and blocked documents stay behind — downloading an
  // incomplete paper on a bulk action would hide that it is incomplete.
  const readyDocs = selectedDefinitions.filter((doc) => docStatus(doc).status === "ready");
  const [downloadingAll, setDownloadingAll] = useState(false);
  const downloadAll = async () => {
    setDownloadingAll(true);
    try {
      for (const doc of readyDocs) {
        await exportGenericDoc(doc);
      }
    } finally {
      setDownloadingAll(false);
    }
  };

  // Which UN cards this shipment can be given. Asked only on the export step,
  // and only when dangerous goods were actually declared.
  useEffect(() => {
    if (stepKey !== "export" || dgEntries.length === 0) {
      setUnCards(null);
      return;
    }
    let cancelled = false;
    api
      .unCardsAvailability({ dangerous_goods: dgEntries, output_language: docLang })
      .then((status) => {
        if (!cancelled) setUnCards(status);
      })
      .catch(() => {
        if (!cancelled) setUnCards(null);
      });
    return () => {
      cancelled = true;
    };
  }, [stepKey, dgEntries, docLang]);

  // The instructions in writing of 5.4.3, which the crew has to carry with the
  // transport document. Asked for the regimes this shipment actually travels
  // under — ADR on the road, ADN on the water — and only when dangerous goods
  // were declared, because without them the document is not required.
  useEffect(() => {
    if (stepKey !== "export" || dgEntries.length === 0) {
      setInstructions([]);
      return;
    }
    let cancelled = false;
    api
      .writtenInstructions()
      .then((answer) => {
        if (!cancelled) setInstructions(answer.documents);
      })
      .catch(() => {
        if (!cancelled) setInstructions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [stepKey, dgEntries]);

  const instructionRegimes = useMemo(
    () => ["adr", "adn"].filter((regime) => dgProfiles.includes(regime.toUpperCase())),
    [dgProfiles],
  );

  // ADN 8.6.3: the checklist that has to be filled in and signed before a tank
  // vessel is loaded or unloaded. It is asked for only when this shipment is
  // one — a dry cargo vessel does not fill it in, and a card that offered it
  // anyway would be telling the boatmaster something untrue about his trip.
  const inCargoTanks = useMemo(
    () =>
      dgProfiles.includes("ADN") &&
      dgEntries.some((entry) =>
        (entry.products ?? []).some((product) => product.carriage_mode === "tank"),
      ),
    [dgProfiles, dgEntries],
  );

  useEffect(() => {
    if (stepKey !== "export" || !inCargoTanks) {
      setChecklist([]);
      return;
    }
    let cancelled = false;
    api
      .models("8.6.3")
      .then((answer) => {
        if (!cancelled) setChecklist(answer.documents);
      })
      .catch(() => {
        if (!cancelled) setChecklist([]);
      });
    return () => {
      cancelled = true;
    };
  }, [stepKey, inCargoTanks]);

  const downloadChecklist = async (regime: string, language: string) => {
    setError("");
    try {
      await api.downloadModel("8.6.3", regime, language);
    } catch (e) {
      setError(String(e));
    }
  };

  const downloadInstructions = async (regime: string, language: string) => {
    setError("");
    try {
      await api.downloadInstructions(regime, language);
    } catch (e) {
      setError(String(e));
    }
  };

  const downloadUnCards = async () => {
    setUnCardsBusy(true);
    setError("");
    try {
      await api.downloadUnCards({ dangerous_goods: dgEntries, output_language: docLang });
    } catch (e) {
      setError(String(e));
    } finally {
      setUnCardsBusy(false);
    }
  };

  /** The wizard state, in the shape the assistant exchanges. Result-derived
   *  facts (recognised candidates) ride along so the assistant asks about
   *  what the user already sees on the lines step. */
  const buildAssistantState = () => ({
    modality,
    draft_lines: draftLines
      .filter((line) => line.description.trim())
      .map((line) => {
        const resultLine = result?.lines.find((r) => r.line_id === line.id);
        return {
          id: line.id,
          description: line.description,
          quantity: line.quantity || 1,
          unit: line.unit,
          dangerous_goods: Boolean(line.dangerous_goods),
          confirmed_un: line.confirmed_un,
          dg_dismissed: line.dg_dismissed,
          detected_un_numbers: resultLine?.detected_un_numbers ?? [],
          dg_name_candidates: resultLine?.dg_name_candidates ?? [],
          weight_each_kg: resultLine?.weight_each_kg ?? undefined,
          package_content: line.package_content ?? resultLine?.package_content ?? undefined,
        };
      }),
    dg_entries: dgEntries,
    doc_values: docValues,
    selected_docs: selectedDocs,
  });

  /** What the assistant changed lands in the same state the classic wizard
   *  uses — switching between the two can therefore never lose data. */
  const applyAssistantState = (state: import("../api/client").AssistantState) => {
    if (Array.isArray(state.draft_lines)) {
      const mapped: DraftLine[] = state.draft_lines.map((line) => ({
        id: Number(line.id),
        description: String(line.description ?? ""),
        quantity: (line.quantity as number) ?? 1,
        unit: String(line.unit ?? "pcs"),
        dangerous_goods: Boolean(line.dangerous_goods),
        confirmed_un: (line.confirmed_un as string) || undefined,
        dg_dismissed: Boolean(line.dg_dismissed) || undefined,
        package_content: (line.package_content as string) || undefined,
      }));
      if (mapped.length > 0) {
        setDraftLines((current) => {
          const byId = new Map(current.map((line) => [line.id, line]));
          return mapped.map((line) => ({ ...(byId.get(line.id) ?? {}), ...line }));
        });
      }
    }
    if (Array.isArray(state.dg_entries)) setDgEntries(state.dg_entries);
    if (state.doc_values) setDocValues((current) => ({ ...current, ...state.doc_values }));
  };

  const translateMessage = (msg: string) => {
    const key = `messages.${msg}`;
    const translated = t(key as "messages.dg_un_detected");
    return translated === key ? msg : translated;
  };

  const includedLines = result?.lines.filter((line) => line.include) ?? [];

  if (registryError) {
    return <p className="text-sm text-red-600 dark:text-red-400">{registryError}</p>;
  }

  if (!registry) {
    return <div className="py-12 text-center text-slate-500 dark:text-slate-400">{t("wizard.loading")}</div>;
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-2 rounded-full bg-brand-100 px-3 py-1 text-xs font-medium text-brand-700 dark:bg-brand-900/50 dark:text-brand-200">
          {t(`modality.${modality}`)}
        </span>
        <Link to="/?choose=1" className="text-xs text-slate-500 hover:underline dark:text-slate-400">
          {t("wizard.changeModality")}
        </Link>
        <button
          type="button"
          onClick={() => setAssistantOpen((open) => !open)}
          aria-label={assistantOpen ? t("assistant.close") : t("assistant.open")}
          title={assistantOpen ? t("assistant.close") : t("assistant.open")}
          className={`ml-auto inline-flex h-9 w-9 items-center justify-center rounded-lg border transition ${
            assistantOpen
              ? "border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-950/50 dark:text-brand-200"
              : "border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          }`}
        >
          <AiIcon className="h-5 w-5" />
        </button>
      </div>

      <WizardProgress steps={stepPills} currentStep={currentIndex + 1} />

      <AssistantModal
        open={assistantOpen}
        onClose={() => setAssistantOpen(false)}
        buildState={buildAssistantState}
        onApplyState={applyAssistantState}
      />

      {stepKey === "lines" && (
        <div className="space-y-4">
          {result && (
            <div className="grid grid-cols-2 gap-2 sm:gap-3 lg:grid-cols-4">
              <Stat label={t("wizard.lines")} value={String(result.totals.line_count ?? 0)} />
              <Stat label={t("wizard.totalWeight")} value={`${result.totals.total_weight_kg ?? 0} kg`} />
              <Stat label={t("wizard.totalVolume")} value={`${result.totals.total_transport_volume_m3 ?? 0} m³`} />
              <Stat label={t("wizard.warnings")} value={String(result.totals.warning_count ?? 0)} />
            </div>
          )}

          <ReviewLinesPanel
            draftLines={draftLines}
            resultLines={result?.lines}
            onDraftChange={(lines) => {
              setDraftLines(lines);
              // Ticking DG or answering a name suggestion does not change what
              // was calculated; clearing the result for it would wipe the
              // weights off the screen for an answer, not an edit.
              if (signatureOf(lines) !== draftSignature) setResult(null);
            }}
            onRemoveLine={removeLine}
            onDuplicateLine={duplicateLine}
            onAddLine={addLine}
            onImportClick={() => setImportOpen(true)}
            onLineWeightChange={result ? handleLineWeightChange : undefined}
            translateMessage={translateMessage}
          />

          <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
            <button type="button" onClick={goFromLines} disabled={loading} className={`${buttonPrimary} sm:ml-auto`}>
              {t("wizard.continue")}
            </button>
          </div>
        </div>
      )}

      {stepKey === "dg" && result && (
        <div className="space-y-4">
          <DangerousGoodsStep
            lines={result.lines}
            entries={dgEntries}
            onChange={setDgEntries}
            perPosition
            extraFields={dgExtraFields}
            profiles={dgProfiles}
          />
          <DgCompliancePanel entries={dgEntries} profiles={dgProfiles} />
          <div className="flex flex-col gap-2 sm:flex-row">
            <button type="button" onClick={() => goBackFrom("dg")} className={buttonSecondary}>
              {t("wizard.back")}
            </button>
            <button type="button" onClick={() => goNextFrom("dg")} className={`${buttonPrimary} sm:ml-auto`}>
              {genericDocs.length > 0 ? t("wizard.toDetails") : t("wizard.toExport")}
            </button>
          </div>
        </div>
      )}

      {stepKey === "details" && (
        <div className="space-y-4">
          {lastShipment && (
            <div className={`${panelClass} flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between`}>
              <p className="text-sm text-slate-600 dark:text-slate-400">{t("docfields.reuseLastHint")}</p>
              <button type="button" onClick={reuseLastShipment} className={buttonSecondary}>
                {t("docfields.reuseLast")}
              </button>
            </div>
          )}
          <DocumentFieldsStep
            registry={registry}
            documents={genericDocs}
            values={docValues}
            onChange={setDocValues}
            autoValues={autoValues}
            modality={modality}
            onBack={() => goBackFrom("details")}
            onDone={completeDetails}
            signature={signature}
            onSignatureChange={setSignature}
          />
        </div>
      )}

      {stepKey === "export" && result && (
        <div className="space-y-4">
          <div className={`${panelClass} space-y-4 p-4 sm:p-6`}>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("wizard.summary")}</h3>
            {needsDg && (
              <p className="text-sm text-amber-700 dark:text-amber-300">
                {t("wizard.dgIncluded", { count: dgEntries.length })}
              </p>
            )}
            <div className="space-y-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("wizard.products")}</h4>
                <div className="sm:w-48">
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400">{t("wizard.adjustTotalWeight")}</label>
                  <input
                    type="number"
                    step="0.01"
                    className={`${weightInputClass} mt-1`}
                    value={result.totals.total_weight_kg ?? ""}
                    onChange={(e) => handleTotalWeightChange(e.target.value === "" ? null : Number(e.target.value))}
                  />
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t("wizard.adjustTotalWeightHint")}</p>
                </div>
              </div>

              <div className="space-y-2">
                {includedLines.map((line) => (
                  <div key={line.line_id} className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm dark:border-slate-700">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <p className="truncate font-medium text-slate-900 dark:text-slate-100">
                          {line.output_description || line.description}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {line.quantity ?? "—"} {line.unit ?? ""}
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-2 sm:w-56">
                        <div>
                          <label className="text-[11px] text-slate-500 dark:text-slate-400">{t("review.weightEach")}</label>
                          <input
                            type="number"
                            step="0.01"
                            className={`${weightInputClass} mt-0.5`}
                            value={line.weight_each_kg ?? ""}
                            onChange={(e) =>
                              handleLineWeightChange(line.line_id, "weight_each_kg", e.target.value === "" ? null : Number(e.target.value))
                            }
                          />
                        </div>
                        <div>
                          <label className="text-[11px] text-slate-500 dark:text-slate-400">{t("review.weightTotal")}</label>
                          <input
                            type="number"
                            step="0.01"
                            className={`${weightInputClass} mt-0.5`}
                            value={line.weight_total_kg ?? ""}
                            onChange={(e) =>
                              handleLineWeightChange(line.line_id, "weight_total_kg", e.target.value === "" ? null : Number(e.target.value))
                            }
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <ul className="space-y-1 text-sm text-slate-600 dark:text-slate-400">
              <li>{t("wizard.lines")}: {result.totals.included_count}</li>
              <li>{t("wizard.totalWeight")}: {result.totals.total_weight_kg} kg</li>
              <li>{t("wizard.totalVolume")}: {result.totals.total_transport_volume_m3} m³</li>
            </ul>
          </div>

          {needsDg && dgEntries.length > 0 && <DgCompliancePanel entries={dgEntries} profiles={dgProfiles} />}

          <DocumentAdvicePanel
            registry={registry}
            modality={modality ?? ""}
            needsDg={needsDg}
            selected={selected}
            onChange={setSelectedDocs}
          />

          <div className={`${panelClass} space-y-3 p-4 sm:p-6`}>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("wizardDocs.title")}</h3>
              {readyDocs.length > 1 && (
                <button
                  type="button"
                  onClick={downloadAll}
                  disabled={downloadingAll}
                  className={buttonPrimary}
                >
                  {downloadingAll
                    ? t("wizardDocs.exporting")
                    : t("wizardDocs.downloadAll", { count: readyDocs.length })}
                </button>
              )}
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">{t("wizardDocs.intro")}</p>
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-300">
              {t("wizardDocs.exportNotice")}{" "}
              <Link to="/legal" className="font-medium underline">
                {t("nav.legal")}
              </Link>
            </p>
            <div className="space-y-2">
              {selectedDefinitions.map((doc) => {
                const info = docStatus(doc);
                const busy = exportingDoc === doc.key;
                return (
                  <div key={doc.key} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700 sm:p-4">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-medium text-slate-900 dark:text-slate-100">{L(doc.label)}</p>
                          <StatusBadge status={info.status} />
                          {info.waitingCarrier && info.status !== "not_applicable" && (
                            <span className="rounded-full bg-sky-100 px-2 py-0.5 text-[11px] font-medium text-sky-800 dark:bg-sky-900/40 dark:text-sky-300">
                              {t("wizardDocs.waitingCarrier")}
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{L(doc.issue_status)}</p>
                        {info.status === "draft" && info.missing.length > 0 && (
                          <p className="mt-1 text-xs text-amber-600 dark:text-amber-300">
                            {t("wizardDocs.missingFields", { fields: info.missing.slice(0, 4).join(", ") })}
                            {info.missing.length > 4 ? ` (+${info.missing.length - 4})` : ""}
                          </p>
                        )}
                        {info.status === "blocked" && (
                          <p className="mt-1 text-xs text-red-600 dark:text-red-400">{t("wizardDocs.dgBlocked")}</p>
                        )}
                        <DocumentWarnings
                          heading={t("wizardDocs.checkWarnings")}
                          warnings={docWarnings[doc.key] ?? []}
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => exportGenericDoc(doc)}
                        disabled={busy || info.status === "blocked" || info.status === "not_applicable" || info.status === "draft"}
                        className={buttonPrimary}
                      >
                        {busy ? t("wizardDocs.exporting") : t("wizard.download")}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className={`${panelClass} space-y-2 p-4 sm:p-6`}>
            <label
              htmlFor="document-language"
              className="text-sm font-medium text-slate-800 dark:text-slate-100"
            >
              {t("wizardDocs.documentLanguage")}
            </label>
            <select
              id="document-language"
              value={docLang}
              onChange={(event) => setChosenDocLang(event.target.value as Language)}
              className={weightInputClass + " sm:max-w-xs"}
            >
              {SUPPORTED_LANGUAGES.map((code) => (
                <option key={code} value={code}>
                  {LANGUAGE_NAMES[code]}
                </option>
              ))}
            </select>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {t("wizardDocs.documentLanguageRule")}
            </p>
          </div>

          {instructionRegimes.length > 0 && instructions.length > 0 && (
            <div className={`${panelClass} space-y-3 p-4 sm:p-6`}>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                {t("instructions.title")}
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {t("instructions.intro")}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t("instructions.languageRule")}
              </p>
              {instructionRegimes.map((regime) => (
                <div key={regime} className="space-y-2">
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                    {regime.toUpperCase()}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {instructions
                      .filter((item) => item.regime === regime)
                      .map((item) => (
                        <button
                          key={`${item.regime}-${item.language}`}
                          type="button"
                          disabled={!item.available}
                          title={
                            item.available
                              ? undefined
                              : `${t("instructions.unavailable", { document: item.needs ?? "" })} ${t("instructions.howto")}`
                          }
                          onClick={() => downloadInstructions(item.regime, item.language)}
                          className={`${buttonSecondary} ${item.available ? "" : "opacity-40"}`}
                        >
                          {item.language.toUpperCase()}
                        </button>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {checklist.length > 0 && (
            <div className={`${panelClass} space-y-3 p-4 sm:p-6`}>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                {t("checklist.title")}
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {t("checklist.intro")}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t("checklist.notFilledIn")}
              </p>
              <div className="flex flex-wrap gap-2">
                {checklist.map((item) => (
                  <button
                    key={`${item.regime}-${item.language}`}
                    type="button"
                    disabled={!item.available}
                    title={
                      item.available
                        ? undefined
                        : `${t("instructions.unavailable", { document: item.needs ?? "" })} ${t("instructions.howto")}`
                    }
                    onClick={() => downloadChecklist(item.regime, item.language)}
                    className={`${buttonSecondary} ${item.available ? "" : "opacity-40"}`}
                  >
                    {item.language.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
          )}

          {unCards && unCards.enabled && unCards.count > 0 && (
            <div className={`${panelClass} space-y-3 p-4 sm:p-6`}>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                {t("unCards.title")}
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400">{t("unCards.intro")}</p>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    {t("unCards.forSubstances", {
                      list: unCards.available.map((un) => `UN ${un}`).join(", "),
                    })}
                  </p>
                  {unCards.missing.length > 0 && (
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {t("unCards.missing", {
                        list: unCards.missing.map((un) => `UN ${un}`).join(", "),
                      })}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={downloadUnCards}
                  disabled={unCardsBusy}
                  className={buttonSecondary}
                >
                  {unCardsBusy
                    ? t("wizardDocs.exporting")
                    : t("unCards.download", { count: unCards.count })}
                </button>
              </div>
            </div>
          )}

          <div className="flex flex-col gap-2 sm:flex-row">
            <button type="button" onClick={() => goBackFrom("export")} className={buttonSecondary}>
              {t("wizard.back")}
            </button>
          </div>
        </div>
      )}

      <ImportDialog open={importOpen} onClose={() => setImportOpen(false)} onImport={handleImport} />

      {error && <p className="whitespace-pre-line text-sm text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}

function StatusBadge({ status }: { status: DocStatus }) {
  const { t } = useTranslation();
  const styles: Record<DocStatus, string> = {
    ready: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    draft: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    blocked: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
    not_applicable: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  };
  const labels: Record<DocStatus, string> = {
    ready: t("wizardDocs.statusReady"),
    draft: t("wizardDocs.statusDraft"),
    blocked: t("wizardDocs.statusBlocked"),
    not_applicable: t("wizardDocs.statusNotApplicable"),
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${styles[status]}`}>{labels[status]}</span>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className={`${panelClass} p-3 sm:p-4`}>
      <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100 sm:text-lg">{value}</p>
    </div>
  );
}
