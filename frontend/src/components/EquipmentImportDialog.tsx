import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, EquipmentImportResult } from "../api/client";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl";

interface Props {
  open: boolean;
  onClose: () => void;
  onComplete: () => void;
}

export default function EquipmentImportDialog({ open, onClose, onComplete }: Props) {
  const { t } = useTranslation();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EquipmentImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!open) return null;

  const reset = () => {
    setError("");
    setResult(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleDownloadTemplate = async () => {
    setError("");
    try {
      await api.downloadEquipmentTemplate();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleFile = async (file: File | null) => {
    if (!file) return;
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const importResult = await api.importEquipmentFile(file);
      setResult(importResult);
      onComplete();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4" role="dialog" aria-modal>
      <div className={`${panelClass} max-h-[90vh] w-full max-w-lg overflow-y-auto`}>
        <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800 sm:px-6 sm:py-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("materieel.importTitle")}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{t("materieel.importHint")}</p>
            </div>
            <button
              type="button"
              onClick={handleClose}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
              aria-label={t("materieel.cancel")}
            >
              <span className="text-xl leading-none">×</span>
            </button>
          </div>
        </div>

        <div className="space-y-4 px-5 py-4 sm:px-6 sm:py-5">
          <button
            type="button"
            onClick={handleDownloadTemplate}
            className="w-full min-h-[44px] rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800/50"
          >
            {t("import.downloadTemplate")}
          </button>

          <label className="flex min-h-[44px] cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-brand-300 bg-brand-50/50 px-4 py-6 text-center text-sm font-medium text-brand-800 hover:bg-brand-50 dark:border-brand-800 dark:bg-brand-950/30 dark:text-brand-100 dark:hover:bg-brand-950/50">
            {loading ? t("import.importingFile") : t("import.chooseFile")}
            <span className="mt-1 text-xs font-normal text-slate-500 dark:text-slate-400">.xlsx, .csv, .txt</span>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.csv,.txt"
              className="sr-only"
              disabled={loading}
              onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
            />
          </label>

          {result && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm dark:border-slate-700 dark:bg-slate-800/50">
              <p className="font-medium text-slate-900 dark:text-slate-100">{t("materieel.importDone")}</p>
              <ul className="mt-2 space-y-1 text-slate-600 dark:text-slate-400">
                <li>{t("materieel.importCreated", { count: result.created })}</li>
                <li>{t("materieel.importUpdated", { count: result.updated })}</li>
                {result.skipped > 0 && <li>{t("materieel.importSkipped", { count: result.skipped })}</li>}
              </ul>
              {result.errors.length > 0 && (
                <ul className="mt-3 space-y-1 text-amber-700 dark:text-amber-300">
                  {result.errors.map((msg) => (
                    <li key={msg}>{msg}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        </div>

        <div className="flex justify-end border-t border-slate-100 px-5 py-4 dark:border-slate-800 sm:px-6">
          <button
            type="button"
            onClick={handleClose}
            className="min-h-[44px] rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-200"
          >
            {t("materieel.cancel")}
          </button>
        </div>
      </div>
    </div>
  );
}
