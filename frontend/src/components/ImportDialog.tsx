import { useState } from "react";
import { useTranslation } from "react-i18next";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-xl px-3 py-2 font-mono text-sm min-h-[12rem] focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:focus:border-brand-500";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl";

interface Props {
  open: boolean;
  onClose: () => void;
  onImport: (text: string, mode: "append" | "replace") => void;
}

export default function ImportDialog({ open, onClose, onImport }: Props) {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const [mode, setMode] = useState<"append" | "replace">("replace");

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4" role="dialog" aria-modal>
      <div className={`${panelClass} max-h-[90vh] w-full max-w-2xl overflow-y-auto`}>
        <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800 sm:px-6 sm:py-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("review.importTitle")}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{t("review.importHint")}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
              aria-label={t("review.cancel")}
            >
              <span className="text-xl leading-none">×</span>
            </button>
          </div>
          <div className="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-2.5 dark:border-slate-700 dark:bg-slate-800/50">
            <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{t("review.importExampleTitle")}</p>
            <p className="mt-1 font-mono text-xs text-slate-700 dark:text-slate-300">{t("review.importExample")}</p>
          </div>
        </div>

        <div className="space-y-4 px-5 py-4 sm:px-6 sm:py-5">
          <textarea className={inputClass} value={text} onChange={(e) => setText(e.target.value)} placeholder={t("wizard.paste")} />

          <div className="grid gap-2 sm:grid-cols-2">
            <label
              className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 text-sm transition-colors ${
                mode === "replace"
                  ? "border-brand-300 bg-brand-50 text-brand-900 dark:border-brand-700 dark:bg-brand-950/40 dark:text-brand-100"
                  : "border-slate-200 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800/50"
              }`}
            >
              <input type="radio" className="accent-brand-600" checked={mode === "replace"} onChange={() => setMode("replace")} />
              {t("review.importReplace")}
            </label>
            <label
              className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 text-sm transition-colors ${
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

        <div className="flex flex-col-reverse gap-2 border-t border-slate-100 px-5 py-4 dark:border-slate-800 sm:flex-row sm:justify-end sm:px-6">
          <button
            type="button"
            onClick={onClose}
            className="min-h-[44px] rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-200"
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
            className="min-h-[44px] rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {t("review.importConfirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
