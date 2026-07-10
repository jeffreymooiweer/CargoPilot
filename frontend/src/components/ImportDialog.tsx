import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-xl px-3 py-2 font-mono text-sm min-h-[10rem] focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:focus:border-brand-500 sm:min-h-[12rem]";
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
  onImport: (text: string, mode: "append" | "replace") => void;
}

export default function ImportDialog({ open, onClose, onImport }: Props) {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const [mode, setMode] = useState<"append" | "replace">("replace");
  const [fileError, setFileError] = useState("");
  const [loadingFile, setLoadingFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!open) return null;

  const handleFile = async (file: File | null) => {
    if (!file) return;
    setFileError("");
    setLoadingFile(true);
    try {
      const result = await api.parseWizardImportFile(file);
      setText(result.text);
    } catch (e) {
      setFileError(String(e));
    } finally {
      setLoadingFile(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDownloadTemplate = async () => {
    setFileError("");
    try {
      await api.downloadWizardTemplate();
    } catch (e) {
      setFileError(String(e));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4" role="dialog" aria-modal>
      <div className={`${panelClass} max-h-[90vh] w-full max-w-2xl overflow-y-auto`}>
        <div className="border-b border-slate-100 px-4 py-4 dark:border-slate-800 sm:px-6 sm:py-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("review.importTitle")}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{t("review.importHint")}</p>
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
                className={`${iconActionClass} cursor-pointer ${loadingFile ? "pointer-events-none opacity-50" : ""}`}
                aria-label={t("import.chooseFile")}
                title={loadingFile ? t("import.parsingFile") : t("import.chooseFile")}
              >
                <UploadIcon />
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.csv,.txt"
                  className="sr-only"
                  onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
                />
              </label>
              <button
                type="button"
                onClick={onClose}
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                aria-label={t("review.cancel")}
              >
                <span className="text-xl leading-none">×</span>
              </button>
            </div>
          </div>
          <div className="mt-3 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/50">
            <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{t("review.importExampleTitle")}</p>
            <p className="mt-1 font-mono text-xs text-slate-700 dark:text-slate-300">{t("review.importExample")}</p>
          </div>
          {fileError && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{fileError}</p>}
        </div>

        <div className="space-y-3 px-4 py-4 sm:space-y-4 sm:px-6 sm:py-5">
          <textarea className={inputClass} value={text} onChange={(e) => setText(e.target.value)} placeholder={t("wizard.paste")} />

          <div className="grid gap-2 sm:grid-cols-2">
            <label
              className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors sm:gap-3 sm:rounded-xl sm:px-4 sm:py-3 ${
                mode === "replace"
                  ? "border-brand-300 bg-brand-50 text-brand-900 dark:border-brand-700 dark:bg-brand-950/40 dark:text-brand-100"
                  : "border-slate-200 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800/50"
              }`}
            >
              <input type="radio" className="accent-brand-600" checked={mode === "replace"} onChange={() => setMode("replace")} />
              {t("review.importReplace")}
            </label>
            <label
              className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors sm:gap-3 sm:rounded-xl sm:px-4 sm:py-3 ${
                mode === "append"
                  ? "border-brand-300 bg-brand-50 text-brand-900 dark:border-brand-700 dark:bg-brand-950/40 dark:text-brand-100"
                  : "border-slate-200 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800/50"
              }`}
            >
              <input type="radio" className="accent-brand-600" checked={mode === "append"} onChange={() => setMode("append")} />
              {t("review.importAppend")}
            </label>
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-100 px-4 py-3 dark:border-slate-800 sm:px-6 sm:py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-200"
          >
            {t("review.cancel")}
          </button>
          <button
            type="button"
            disabled={!text.trim()}
            onClick={() => {
              onImport(text, mode);
              setText("");
              onClose();
            }}
            className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {t("review.importConfirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
