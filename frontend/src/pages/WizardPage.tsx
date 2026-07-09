import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, CalcResult, DgEntry } from "../api/client";
import AppendixQuestionsWizard from "../components/AppendixQuestionsWizard";
import DangerousGoodsStep, { buildDgEntries } from "../components/DangerousGoodsStep";
import ImportDialog from "../components/ImportDialog";
import ReviewLinesPanel, { DraftLine, draftToText, textToDraftLines } from "../components/ReviewLinesPanel";
import WizardProgress from "../components/WizardProgress";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm min-h-[44px]";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const buttonSecondary = "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 min-h-[44px] text-sm";
const buttonPrimary = "bg-brand-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";

export default function WizardPage() {
  const { t } = useTranslation();
  const [step, setStep] = useState(1);
  const [draftLines, setDraftLines] = useState<DraftLine[]>([{ id: 1, description: "", quantity: 1, unit: "stuks" }]);
  const [nextId, setNextId] = useState(2);
  const [result, setResult] = useState<CalcResult | null>(null);
  const [metadata, setMetadata] = useState({ route: "", ba_code: "", annex_serial: "", date: "" });
  const [dgEntries, setDgEntries] = useState<DgEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [importOpen, setImportOpen] = useState(false);

  const needsDg = useMemo(
    () => result?.lines.some((line) => line.include && line.appendix_flags?.dangerous_goods === "Y") ?? false,
    [result],
  );

  const exportStep = needsDg ? 4 : 3;

  const stepPills = useMemo(() => {
    const pills = [
      { n: 1, label: t("wizard.step2") },
      { n: 2, label: t("wizard.stepQuestions") },
    ];
    if (needsDg) pills.push({ n: 3, label: t("wizard.step3dg") });
    pills.push({ n: exportStep, label: t("wizard.step4") });
    return pills;
  }, [needsDg, exportStep, t]);

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
      const res = await api.calculate({ text, mode: "continue", input_language: null });
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

  const goToQuestions = async () => {
    const res = result ?? (await calculateFromDraft());
    if (!res) return;
    setStep(2);
  };

  const appendixLang = (lines: CalcResult["lines"]) => {
    const langs = lines.map((l) => l.input_language).filter(Boolean);
    if (langs.length === 0) return "nl";
    const enCount = langs.filter((l) => l === "en").length;
    return enCount > langs.length / 2 ? "en" : "nl";
  };

  const finishQuestions = (updatedLines: CalcResult["lines"]) => {
    setResult((prev) => (prev ? { ...prev, lines: updatedLines } : prev));
    const hasDg = updatedLines.some((line) => line.include && line.appendix_flags?.dangerous_goods === "Y");
    if (hasDg) {
      setDgEntries(buildDgEntries(updatedLines));
      setStep(3);
    } else {
      setDgEntries([]);
      setStep(exportStep);
    }
  };

  const exportFile = async () => {
    if (!result) return;
    setLoading(true);
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
      setLoading(false);
    }
  };

  const translateMessage = (msg: string) => {
    const key = `messages.${msg}`;
    const translated = t(key as "messages.dg_un_detected");
    return translated === key ? msg : translated;
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <WizardProgress steps={stepPills} currentStep={step} />

      {step === 1 && (
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
            onAddLine={addLine}
            onImportClick={() => setImportOpen(true)}
            translateMessage={translateMessage}
          />

          <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
            <button type="button" onClick={recalculate} disabled={loading} className={buttonSecondary}>
              {t("wizard.recalculate")}
            </button>
            <button type="button" onClick={goToQuestions} disabled={loading} className={`${buttonPrimary} sm:ml-auto`}>
              {t("wizard.toQuestions")}
            </button>
          </div>
        </div>
      )}

      {step === 2 && result && (
        <AppendixQuestionsWizard lines={result.lines} onComplete={finishQuestions} onBack={() => setStep(1)} />
      )}

      {step === 3 && result && needsDg && (
        <div className="space-y-4">
          <DangerousGoodsStep lines={result.lines} entries={dgEntries} onChange={setDgEntries} perPosition />
          <div className="flex flex-col gap-2 sm:flex-row">
            <button type="button" onClick={() => setStep(2)} className={buttonSecondary}>{t("wizard.back")}</button>
            <button type="button" onClick={() => setStep(exportStep)} className={`${buttonPrimary} sm:ml-auto`}>
              {t("wizard.toExport")}
            </button>
          </div>
        </div>
      )}

      {step === exportStep && result && (
        <div className={`${panelClass} space-y-4 p-4 sm:p-6`}>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("wizard.summary")}</h3>
          {needsDg && (
            <p className="text-sm text-amber-700 dark:text-amber-300">{t("wizard.dgIncluded", { count: dgEntries.length })}</p>
          )}
          <div className="grid gap-3">
            <Field label={t("wizard.date")} value={metadata.date} onChange={(v) => setMetadata({ ...metadata, date: v })} />
            <Field label={t("wizard.route")} value={metadata.route} onChange={(v) => setMetadata({ ...metadata, route: v })} />
            <Field label={t("wizard.baCode")} value={metadata.ba_code} onChange={(v) => setMetadata({ ...metadata, ba_code: v })} />
            <Field label={t("wizard.annex")} value={metadata.annex_serial} onChange={(v) => setMetadata({ ...metadata, annex_serial: v })} />
          </div>
          <ul className="space-y-1 text-sm text-slate-600 dark:text-slate-400">
            <li>{t("wizard.lines")}: {result.totals.included_count}</li>
            <li>{t("wizard.totalWeight")}: {result.totals.total_weight_kg} kg</li>
            <li>{t("wizard.totalVolume")}: {result.totals.total_transport_volume_m3} m³</li>
          </ul>
          <div className="flex flex-col gap-2 sm:flex-row">
            <button type="button" onClick={() => setStep(needsDg ? 3 : 2)} className={buttonSecondary}>{t("wizard.back")}</button>
            <button type="button" onClick={exportFile} disabled={loading} className={`${buttonPrimary} sm:ml-auto`}>
              {t("wizard.download")}
            </button>
          </div>
        </div>
      )}

      <ImportDialog open={importOpen} onClose={() => setImportOpen(false)} onImport={handleImport} />

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </div>
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
