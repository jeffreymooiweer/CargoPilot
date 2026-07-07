import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, CalcResult, LineItem } from "../api/client";

const SAMPLE = `Stalen hoekprofiel 80x80x8x6000 | 8 | stuks
staal hoekprofiel 50x50x5x6000mm | 38 | stuks
Staal kokerprofiel 60x60x6x6000mm | 32 | stuks
Staal kokerprofiel 40x40x3x6000 | 12 | stuks
UNP 220 mml=5700mm gegalvaniseerd | 24 | stuks`;

function statusColor(status: string) {
  if (status === "ok") return "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";
  if (status === "error") return "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
  if (status === "needs_review") return "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300";
  return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300";
}

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const buttonSecondary = "px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800";

export default function WizardPage() {
  const { t } = useTranslation();
  const [step, setStep] = useState(1);
  const [text, setText] = useState(SAMPLE);
  const [mode, setMode] = useState<"continue" | "strict">("continue");
  const [autoLang, setAutoLang] = useState(true);
  const [outputLang, setOutputLang] = useState("nl");
  const [result, setResult] = useState<CalcResult | null>(null);
  const [metadata, setMetadata] = useState({ route: "", ba_code: "", annex_serial: "", date: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const analyze = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.calculate({
        text,
        mode,
        input_language: autoLang ? null : "nl",
        output_language: outputLang,
      });
      setResult(res);
      if (mode === "strict" && !res.success) {
        setError(t("wizard.strictBlocked"));
        setStep(2);
        return;
      }
      setStep(2);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const updateLine = (lineId: number, patch: Partial<LineItem>) => {
    if (!result) return;
    const lines = result.lines.map((line) => (line.line_id === lineId ? { ...line, ...patch } : line));
    setResult({ ...result, lines });
  };

  const recalculate = async () => {
    if (!result) return;
    setLoading(true);
    try {
      const res = await api.calculate({ lines: result.lines, output_language: outputLang, mode });
      setResult(res);
    } finally {
      setLoading(false);
    }
  };

  const exportFile = async () => {
    if (!result) return;
    setLoading(true);
    setError("");
    try {
      await api.exportAppendix({
        lines: result.lines,
        output_language: outputLang,
        metadata: { ...metadata, output_language: outputLang },
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex gap-2 flex-wrap">
        {[1, 2, 3].map((s) => (
          <div
            key={s}
            className={`px-4 py-2 rounded-full text-sm font-medium ${
              step === s ? "bg-brand-600 text-white" : "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
            }`}
          >
            {s}. {t(`wizard.step${s}` as "wizard.step1")}
          </div>
        ))}
      </div>

      {step === 1 && (
        <div className={`${panelClass} p-6 space-y-4`}>
          <textarea
            className={`${inputClass} h-64 font-mono text-sm`}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t("wizard.paste")}
          />
          <div className="flex flex-wrap gap-4 items-center">
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input type="checkbox" checked={autoLang} onChange={(e) => setAutoLang(e.target.checked)} />
              {t("wizard.autoLang")}
            </label>
            <select className={`${inputClass} w-auto text-sm`} value={mode} onChange={(e) => setMode(e.target.value as "continue" | "strict")}>
              <option value="continue">{t("wizard.continue")}</option>
              <option value="strict">{t("wizard.strict")}</option>
            </select>
            <select className={`${inputClass} w-auto text-sm`} value={outputLang} onChange={(e) => setOutputLang(e.target.value)}>
              <option value="nl">Nederlands</option>
              <option value="en">English</option>
            </select>
            <button onClick={analyze} disabled={loading} className="ml-auto bg-brand-600 text-white px-5 py-2 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50">
              {t("wizard.analyze")}
            </button>
          </div>
        </div>
      )}

      {step === 2 && result && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label={t("wizard.lines")} value={String(result.totals.line_count ?? 0)} />
            <Stat label={t("wizard.totalWeight")} value={`${result.totals.total_weight_kg ?? 0} kg`} />
            <Stat label={t("wizard.totalVolume")} value={`${result.totals.total_transport_volume_m3 ?? 0} m³`} />
            <Stat label={t("wizard.warnings")} value={String(result.totals.warning_count ?? 0)} />
          </div>
          <div className={`${panelClass} overflow-x-auto`}>
            <table className="w-full text-sm min-w-[900px] text-slate-800 dark:text-slate-200">
              <thead className="bg-slate-50 dark:bg-slate-800/80">
                <tr>
                  <th className="px-3 py-2 text-left">#</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Omschrijving</th>
                  <th className="px-3 py-2 text-left">Aantal</th>
                  <th className="px-3 py-2 text-left">Gewicht/st</th>
                  <th className="px-3 py-2 text-left">Totaal kg</th>
                  <th className="px-3 py-2 text-left">Incl.</th>
                </tr>
              </thead>
              <tbody>
                {result.lines.map((line) => (
                  <tr key={line.line_id} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="px-3 py-2">{line.line_id}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${statusColor(line.status)}`}>
                        {t(`status.${line.status}` as "status.ok")}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <input className={`${inputClass} text-sm`} value={line.output_description} onChange={(e) => updateLine(line.line_id, { output_description: e.target.value })} />
                      {line.messages.length > 0 && <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">{line.messages.join(", ")}</p>}
                    </td>
                    <td className="px-3 py-2">
                      <input type="number" className={`${inputClass} w-20 text-sm`} value={line.quantity ?? ""} onChange={(e) => updateLine(line.line_id, { quantity: Number(e.target.value) })} />
                    </td>
                    <td className="px-3 py-2">{line.weight_each_kg ?? "-"}</td>
                    <td className="px-3 py-2">{line.weight_total_kg ?? "-"}</td>
                    <td className="px-3 py-2">
                      <input type="checkbox" checked={line.include} onChange={(e) => updateLine(line.line_id, { include: e.target.checked })} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex gap-3">
            <button onClick={() => setStep(1)} className={buttonSecondary}>{t("wizard.back")}</button>
            <button onClick={recalculate} className={buttonSecondary}>{t("wizard.recalculate")}</button>
            <button onClick={() => setStep(3)} className="ml-auto bg-brand-600 text-white px-5 py-2 rounded-lg">{t("wizard.toExport")}</button>
          </div>
        </div>
      )}

      {step === 3 && result && (
        <div className={`${panelClass} p-6 space-y-4 max-w-xl`}>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("wizard.summary")}</h3>
          <div className="grid gap-3">
            <Field label={t("wizard.date")} value={metadata.date} onChange={(v) => setMetadata({ ...metadata, date: v })} />
            <Field label={t("wizard.route")} value={metadata.route} onChange={(v) => setMetadata({ ...metadata, route: v })} />
            <Field label={t("wizard.baCode")} value={metadata.ba_code} onChange={(v) => setMetadata({ ...metadata, ba_code: v })} />
            <Field label={t("wizard.annex")} value={metadata.annex_serial} onChange={(v) => setMetadata({ ...metadata, annex_serial: v })} />
            <div>
              <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("wizard.outputLang")}</label>
              <select className={`${inputClass} mt-1`} value={outputLang} onChange={(e) => setOutputLang(e.target.value)}>
                <option value="nl">Nederlands</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>
          <ul className="text-sm text-slate-600 dark:text-slate-400 space-y-1">
            <li>{t("wizard.lines")}: {result.totals.included_count}</li>
            <li>{t("wizard.totalWeight")}: {result.totals.total_weight_kg} kg</li>
            <li>{t("wizard.totalVolume")}: {result.totals.total_transport_volume_m3} m³</li>
          </ul>
          <div className="flex gap-3">
            <button onClick={() => setStep(2)} className={buttonSecondary}>{t("wizard.back")}</button>
            <button onClick={exportFile} disabled={loading} className="ml-auto bg-brand-600 text-white px-5 py-2 rounded-lg disabled:opacity-50">
              {t("wizard.download")}
            </button>
          </div>
        </div>
      )}

      {error && <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className={`${panelClass} p-4`}>
      <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
      <p className="text-lg font-semibold mt-1 text-slate-900 dark:text-slate-100">{value}</p>
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
