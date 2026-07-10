import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, EquipmentImportResult } from "../api/client";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl";
const iconActionClass =
  "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100";

function DownloadIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M10 3a.75.75 0 0 1 .75.75v7.19l2.22-2.22a.75.75 0 1 1 1.06 1.06l-3.5 3.5a.75.75 0 0 1-1.06 0l-3.5-3.5a.75.75 0 1 1 1.06-1.06l2.22 2.22V3.75A.75.75 0 0 1 10 3Z" />
      <path d="M4 14.25a.75.75 0 0 0-1.5 0v1A2.75 2.75 0 0 0 5.25 18h9.5A2.75 2.75 0 0 0 17.5 15.25v-1a.75.75 0 0 0-1.5 0v1c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-1Z" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M10 17a.75.75 0 0 1-.75-.75v-7.19l-2.22 2.22a.75.75 0 1 1-1.06-1.06l3.5-3.5a.75.75 0 0 1 1.06 0l3.5 3.5a.75.75 0 1 1-1.06 1.06l-2.22-2.22v7.19A.75.75 0 0 1 10 17Z" />
      <path d="M4 14.25a.75.75 0 0 0-1.5 0v1A2.75 2.75 0 0 0 5.25 18h9.5A2.75 2.75 0 0 0 17.5 15.25v-1a.75.75 0 0 0-1.5 0v1c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-1Z" />
    </svg>
  );
}

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
        <div className="border-b border-slate-100 px-4 py-4 dark:border-slate-800 sm:px-6 sm:py-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("materieel.importTitle")}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{t("materieel.importHint")}</p>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <button
                type="button"
                onClick={handleDownloadTemplate}
                className={iconActionClass}
                aria-label={t("import.downloadTemplate")}
                title={t("import.downloadTemplate")}
              >
                <DownloadIcon />
              </button>
              <label
                className={`${iconActionClass} cursor-pointer ${loading ? "pointer-events-none opacity-50" : ""}`}
                aria-label={t("import.chooseFile")}
                title={loading ? t("import.importingFile") : t("import.chooseFile")}
              >
                <UploadIcon />
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.csv,.txt"
                  className="sr-only"
                  disabled={loading}
                  onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
                />
              </label>
              <button
                type="button"
                onClick={handleClose}
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                aria-label={t("materieel.cancel")}
              >
                <span className="text-xl leading-none">×</span>
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-3 px-4 py-4 sm:space-y-4 sm:px-6 sm:py-5">
          {result && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm dark:border-slate-700 dark:bg-slate-800/50 sm:px-4 sm:py-3">
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
      </div>
    </div>
  );
}
