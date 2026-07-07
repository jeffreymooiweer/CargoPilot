import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, CalcResult, LineItem } from "../api/client";

const SAMPLE = `Stalen hoekprofiel 80x80x8x6000 | 8 | stuks
staal hoekprofiel 50x50x5x6000mm | 38 | stuks
Staal kokerprofiel 60x60x6x6000mm | 32 | stuks
Staal kokerprofiel 40x40x3x6000 | 12 | stuks
UNP 220 mml=5700mm gegalvaniseerd | 24 | stuks`;

function statusColor(status: string) {
  if (status === "ok") return "bg-green-100 text-green-800";
  if (status === "error") return "bg-red-100 text-red-800";
  if (status === "needs_review") return "bg-amber-100 text-amber-800";
  return "bg-yellow-100 text-yellow-800";
}

export default function WizardPage() {
  const { t } = useTranslation();
  const [step, setStep] = useState(1);
  const [text, setText] = useState(SAMPLE);
  const [mode, setMode] = useState<"continue" | "strict">("continue");
  const [autoLang, setAutoLang] = useState(true);
  const [outputLang, setOutputLang] = useState("nl");
  const [result, setResult] = useState<CalcResult | null>(null);
  const [jobId, setJobId] = useState<number | null>(null);
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
        setError("Strict mode: corrigeer fouten voor u verdergaat.");
        setStep(2);
        return;
      }
      const job = await api.createJob({
        title: "Appendix",
        text,
        mode,
        output_language: outputLang,
      });
      setJobId(job.job.id);
      setResult(job.result);
      setStep(2);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const updateLine = (lineId: number, patch: Partial<LineItem>) => {
    if (!result) return;
    const lines = result.lines.map((l) => (l.line_id === lineId ? { ...l, ...patch } : l));
    setResult({ ...result, lines });
  };

  const recalculate = async () => {
    if (!result) return;
    setLoading(true);
    try {
      const res = await api.calculate({ lines: result.lines, output_language: outputLang, mode });
      setResult(res);
      if (jobId) {
        await api.updateJob(jobId, { calculated_json: res, status: "review" });
      }
    } finally {
      setLoading(false);
    }
  };

  const exportFile = async () => {
    if (!jobId || !result) return;
    setLoading(true);
    try {
      await api.updateJob(jobId, { calculated_json: result, metadata_json: { ...metadata, output_language: outputLang } });
      await api.exportJob(jobId, { output_language: outputLang, metadata });
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        {[1, 2, 3].map((s) => (
          <div key={s} className={`px-4 py-2 rounded-full text-sm font-medium ${step === s ? "bg-brand-600 text-white" : "bg-slate-200 text-slate-600"}`}>
            {s}. {t(`wizard.step${s}` as "wizard.step1")}
          </div>
        ))}
      </div>

      {step === 1 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
          <textarea
            className="w-full h-64 font-mono text-sm border rounded-xl p-4"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t("wizard.paste")}
          />
          <div className="flex flex-wrap gap-4 items-center">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={autoLang} onChange={(e) => setAutoLang(e.target.checked)} />
              {t("wizard.autoLang")}
            </label>
            <select className="border rounded-lg px-3 py-2 text-sm" value={mode} onChange={(e) => setMode(e.target.value as "continue" | "strict")}>
              <option value="continue">{t("wizard.continue")}</option>
              <option value="strict">{t("wizard.strict")}</option>
            </select>
            <select className="border rounded-lg px-3 py-2 text-sm" value={outputLang} onChange={(e) => setOutputLang(e.target.value)}>
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
          <div className="bg-white rounded-2xl border border-slate-200 overflow-x-auto">
            <table className="w-full text-sm min-w-[900px]">
              <thead className="bg-slate-50">
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
                  <tr key={line.line_id} className="border-t border-slate-100">
                    <td className="px-3 py-2">{line.line_id}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${statusColor(line.status)}`}>
                        {t(`status.${line.status}` as "status.ok")}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <input className="w-full border rounded px-2 py-1" value={line.output_description} onChange={(e) => updateLine(line.line_id, { output_description: e.target.value })} />
                      {line.messages.length > 0 && <p className="text-xs text-amber-700 mt-1">{line.messages.join(", ")}</p>}
                    </td>
                    <td className="px-3 py-2">
                      <input type="number" className="w-20 border rounded px-2 py-1" value={line.quantity ?? ""} onChange={(e) => updateLine(line.line_id, { quantity: Number(e.target.value) })} />
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
            <button onClick={() => setStep(1)} className="px-4 py-2 rounded-lg border">Terug</button>
            <button onClick={recalculate} className="px-4 py-2 rounded-lg border">Herbereken</button>
            <button onClick={() => setStep(3)} className="ml-auto bg-brand-600 text-white px-5 py-2 rounded-lg">Naar export</button>
          </div>
        </div>
      )}

      {step === 3 && result && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4 max-w-xl">
          <h3 className="text-lg font-semibold">{t("wizard.summary")}</h3>
          <div className="grid gap-3">
            <Field label={t("wizard.date")} value={metadata.date} onChange={(v) => setMetadata({ ...metadata, date: v })} />
            <Field label={t("wizard.route")} value={metadata.route} onChange={(v) => setMetadata({ ...metadata, route: v })} />
            <Field label={t("wizard.baCode")} value={metadata.ba_code} onChange={(v) => setMetadata({ ...metadata, ba_code: v })} />
            <Field label={t("wizard.annex")} value={metadata.annex_serial} onChange={(v) => setMetadata({ ...metadata, annex_serial: v })} />
            <div>
              <label className="text-sm font-medium">{t("wizard.outputLang")}</label>
              <select className="w-full border rounded-lg px-3 py-2 mt-1" value={outputLang} onChange={(e) => setOutputLang(e.target.value)}>
                <option value="nl">Nederlands</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>
          <ul className="text-sm text-slate-600 space-y-1">
            <li>{t("wizard.lines")}: {result.totals.included_count}</li>
            <li>{t("wizard.totalWeight")}: {result.totals.total_weight_kg} kg</li>
            <li>{t("wizard.totalVolume")}: {result.totals.total_transport_volume_m3} m³</li>
          </ul>
          <div className="flex gap-3">
            <button onClick={() => setStep(2)} className="px-4 py-2 rounded-lg border">Terug</button>
            <button onClick={exportFile} disabled={loading || !jobId} className="ml-auto bg-brand-600 text-white px-5 py-2 rounded-lg disabled:opacity-50">
              {t("wizard.download")}
            </button>
          </div>
        </div>
      )}

      {error && <p className="text-red-600 text-sm">{error}</p>}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-lg font-semibold mt-1">{value}</p>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="text-sm font-medium">{label}</label>
      <input className="w-full border rounded-lg px-3 py-2 mt-1" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
