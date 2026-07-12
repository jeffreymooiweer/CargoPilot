import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  api,
  CalcResult,
  DgEntry,
  DocumentDefinition,
  DocumentRegistry,
  LocalizedText,
} from "../api/client";
import AppendixQuestionsWizard from "../components/AppendixQuestionsWizard";
import DangerousGoodsStep, { buildDgEntries } from "../components/DangerousGoodsStep";
import DocumentFieldsStep, { resolveSections } from "../components/DocumentFieldsStep";
import FormSelectionStep from "../components/FormSelectionStep";
import ImportDialog from "../components/ImportDialog";
import ReviewLinesPanel, { DraftLine, draftToText, textToDraftLines } from "../components/ReviewLinesPanel";
import WizardProgress from "../components/WizardProgress";
import { isModalityKey } from "./ModalitySelectPage";
import {
  applyLineWeightChange,
  recalcTotals,
  scaleLinesToTotalWeight,
  weightOverridesFromLines,
} from "../utils/lineWeights";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm min-h-[44px]";
const weightInputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const buttonSecondary =
  "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 min-h-[44px] text-sm";
const buttonPrimary =
  "bg-brand-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";

type StepKey = "forms" | "lines" | "questions" | "dg" | "details" | "export";

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
  IMDG: ["technical_name", "marine_pollutant", "ems_code", "emergency_contact"],
  IATA_DGR: ["technical_name", "cargo_aircraft_only", "overpack", "emergency_contact"],
};

export default function WizardPage() {
  const { t, i18n } = useTranslation();
  const { modality } = useParams();
  const lang = (i18n.language.startsWith("en") ? "en" : "nl") as "nl" | "en";
  const L = (text?: LocalizedText) => text?.[lang] ?? "";

  const [registry, setRegistry] = useState<DocumentRegistry | null>(null);
  const [registryError, setRegistryError] = useState("");
  const [stepKey, setStepKey] = useState<StepKey>("forms");
  const [selectedDocs, setSelectedDocs] = useState<string[] | null>(null);
  const [docValues, setDocValues] = useState<Record<string, string>>({});
  const [draftLines, setDraftLines] = useState<DraftLine[]>([{ id: 1, description: "", quantity: 1, unit: "stuks" }]);
  const [nextId, setNextId] = useState(2);
  const [result, setResult] = useState<CalcResult | null>(null);
  const [metadata, setMetadata] = useState({ route: "", ba_code: "", annex_serial: "", date: "" });
  const [dgEntries, setDgEntries] = useState<DgEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [exportingDoc, setExportingDoc] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [importOpen, setImportOpen] = useState(false);

  useEffect(() => {
    api
      .documentsRegistry()
      .then(setRegistry)
      .catch((e) => setRegistryError(String(e)));
  }, []);

  const modalityDef = registry?.modalities.find((m) => m.key === modality);

  useEffect(() => {
    if (registry && modalityDef && selectedDocs === null) {
      setSelectedDocs(
        modalityDef.documents.filter(
          (key) => registry.documents.find((d) => d.key === key)?.default_selected,
        ),
      );
    }
  }, [registry, modalityDef, selectedDocs]);

  const selected = selectedDocs ?? [];

  const selectedDefinitions = useMemo(
    () =>
      selected
        .map((key) => registry?.documents.find((d) => d.key === key))
        .filter((d): d is DocumentDefinition => !!d),
    [selected, registry],
  );

  const genericDocs = useMemo(
    () => selectedDefinitions.filter((d) => d.exporter === "generic"),
    [selectedDefinitions],
  );
  const appendixSelected = selected.includes("intern_formulier");

  const needsDg = useMemo(
    () =>
      result?.lines.some(
        (line) =>
          line.include &&
          (line.appendix_flags?.dangerous_goods === "Y" || (line.detected_un_numbers?.length ?? 0) > 0),
      ) ?? false,
    [result],
  );

  const dgExtraFields = useMemo(() => {
    const fields: string[] = [];
    for (const doc of selectedDefinitions) {
      for (const field of DG_EXTRA_FIELDS[doc.dg_profile ?? ""] ?? []) {
        if (!fields.includes(field)) fields.push(field);
      }
    }
    return fields;
  }, [selectedDefinitions]);

  const steps: StepKey[] = useMemo(() => {
    const list: StepKey[] = ["forms", "lines"];
    if (appendixSelected) list.push("questions");
    if (needsDg) list.push("dg");
    if (genericDocs.length > 0) list.push("details");
    list.push("export");
    return list;
  }, [appendixSelected, needsDg, genericDocs.length]);

  const stepLabels: Record<StepKey, string> = {
    forms: t("wizard.stepForms"),
    lines: t("wizard.step2"),
    questions: t("wizard.stepQuestions"),
    dg: t("wizard.step3dg"),
    details: t("wizard.stepDetails"),
    export: t("wizard.step4"),
  };

  const stepPills = steps.map((key, index) => ({ n: index + 1, label: stepLabels[key] }));
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

  if (!isModalityKey(modality)) {
    return <Navigate to="/" replace />;
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
        line_overrides: result ? weightOverridesFromLines(result.lines) : undefined,
      });
      setResult(res);
      return res;
    } catch (e) {
      setError(String(e));
      return null;
    } finally {
      setLoading(false);
    }
  };

  const recalculate = async () => {
    await calculateFromDraft();
  };

  const addLine = () => {
    setDraftLines((lines) => [...lines, { id: nextId, description: "", quantity: 1, unit: "stuks" }]);
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

  const goFromLines = async () => {
    const res = result ?? (await calculateFromDraft());
    if (!res) return;
    if (appendixSelected) {
      setStepKey("questions");
      return;
    }
    const hasDg = res.lines.some(
      (line) =>
        line.include &&
        (line.appendix_flags?.dangerous_goods === "Y" || (line.detected_un_numbers?.length ?? 0) > 0),
    );
    if (hasDg) {
      if (dgEntries.length === 0) setDgEntries(buildDgEntries(res.lines));
      setStepKey("dg");
    } else if (genericDocs.length > 0) {
      setStepKey("details");
    } else {
      setStepKey("export");
    }
  };

  const appendixLang = (lines: CalcResult["lines"]) => {
    const langs = lines.map((l) => l.input_language).filter(Boolean);
    if (langs.length === 0) return "nl";
    const enCount = langs.filter((l) => l === "en").length;
    return enCount > langs.length / 2 ? "en" : "nl";
  };

  const finishQuestions = (updatedLines: CalcResult["lines"]) => {
    setResult((prev) => (prev ? { ...prev, lines: updatedLines, totals: recalcTotals(updatedLines) } : prev));
    const hasDg = updatedLines.some((line) => line.include && line.appendix_flags?.dangerous_goods === "Y");
    if (hasDg) {
      setDgEntries(buildDgEntries(updatedLines));
      setStepKey("dg");
    } else if (genericDocs.length > 0) {
      setDgEntries([]);
      setStepKey("details");
    } else {
      setDgEntries([]);
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

  const exportAppendixFile = async () => {
    if (!result) return;
    setExportingDoc("intern_formulier");
    setError("");
    try {
      await api.exportAppendix({
        lines: result.lines,
        output_language: appendixLang(result.lines),
        metadata: { ...metadata, output_language: appendixLang(result.lines) },
        dangerous_goods: needsDg ? dgEntries : undefined,
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setExportingDoc(null);
    }
  };

  const exportGenericDoc = async (doc: DocumentDefinition) => {
    if (!result) return;
    setExportingDoc(doc.key);
    setError("");
    try {
      await api.exportDocument({
        document_key: doc.key,
        values: exportValuesFor(doc),
        lines: result.lines,
        dangerous_goods: dgEntries.length > 0 ? dgEntries : undefined,
        output_language: lang,
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setExportingDoc(null);
    }
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

  if (!registry || selectedDocs === null) {
    return <div className="py-12 text-center text-slate-500 dark:text-slate-400">{t("wizard.loading")}</div>;
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-2 rounded-full bg-brand-100 px-3 py-1 text-xs font-medium text-brand-700 dark:bg-brand-900/50 dark:text-brand-200">
          {t(`modality.${modality}`)}
        </span>
        <Link to="/" className="text-xs text-slate-500 hover:underline dark:text-slate-400">
          {t("wizard.changeModality")}
        </Link>
      </div>

      <WizardProgress steps={stepPills} currentStep={currentIndex + 1} />

      {stepKey === "forms" && (
        <div className="space-y-4">
          <FormSelectionStep
            registry={registry}
            modality={modality}
            selected={selected}
            onChange={setSelectedDocs}
          />
          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={() => goNextFrom("forms")}
              disabled={selected.length === 0}
              className={`${buttonPrimary} sm:ml-auto`}
            >
              {t("wizard.toLines")}
            </button>
          </div>
          {selected.length === 0 && (
            <p className="text-sm text-amber-600 dark:text-amber-300">{t("forms.selectAtLeastOne")}</p>
          )}
        </div>
      )}

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
              setResult(null);
            }}
            onRemoveLine={removeLine}
            onDuplicateLine={duplicateLine}
            onAddLine={addLine}
            onImportClick={() => setImportOpen(true)}
            onLineWeightChange={result ? handleLineWeightChange : undefined}
            translateMessage={translateMessage}
          />

          <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
            <button type="button" onClick={() => setStepKey("forms")} className={buttonSecondary}>
              {t("wizard.back")}
            </button>
            <button type="button" onClick={recalculate} disabled={loading} className={buttonSecondary}>
              {t("wizard.recalculate")}
            </button>
            <button type="button" onClick={goFromLines} disabled={loading} className={`${buttonPrimary} sm:ml-auto`}>
              {appendixSelected ? t("wizard.toQuestions") : t("wizard.continue")}
            </button>
          </div>
        </div>
      )}

      {stepKey === "questions" && result && (
        <AppendixQuestionsWizard lines={result.lines} onComplete={finishQuestions} onBack={() => setStepKey("lines")} />
      )}

      {stepKey === "dg" && result && (
        <div className="space-y-4">
          <DangerousGoodsStep
            lines={result.lines}
            entries={dgEntries}
            onChange={setDgEntries}
            perPosition
            extraFields={dgExtraFields}
          />
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
          <DocumentFieldsStep
            registry={registry}
            documents={genericDocs}
            values={docValues}
            onChange={setDocValues}
            autoValues={autoValues}
          />
          <div className="flex flex-col gap-2 sm:flex-row">
            <button type="button" onClick={() => goBackFrom("details")} className={buttonSecondary}>
              {t("wizard.back")}
            </button>
            <button type="button" onClick={() => setStepKey("export")} className={`${buttonPrimary} sm:ml-auto`}>
              {t("wizard.toExport")}
            </button>
          </div>
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
            {appendixSelected && (
              <div className="grid gap-3">
                <Field label={t("wizard.date")} value={metadata.date} onChange={(v) => setMetadata({ ...metadata, date: v })} />
                <Field label={t("wizard.route")} value={metadata.route} onChange={(v) => setMetadata({ ...metadata, route: v })} />
                <Field label={t("wizard.baCode")} value={metadata.ba_code} onChange={(v) => setMetadata({ ...metadata, ba_code: v })} />
                <Field label={t("wizard.annex")} value={metadata.annex_serial} onChange={(v) => setMetadata({ ...metadata, annex_serial: v })} />
              </div>
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

          <div className={`${panelClass} space-y-3 p-4 sm:p-6`}>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("wizardDocs.title")}</h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">{t("wizardDocs.intro")}</p>
            <div className="space-y-2">
              {selectedDefinitions.map((doc) => {
                const isAppendix = doc.exporter === "appendix_template";
                const info = isAppendix
                  ? { status: "ready" as DocStatus, missing: [], waitingCarrier: false }
                  : docStatus(doc);
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
                      </div>
                      <button
                        type="button"
                        onClick={() => (isAppendix ? exportAppendixFile() : exportGenericDoc(doc))}
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

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{label}</label>
      <input className={`${inputClass} mt-1`} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
