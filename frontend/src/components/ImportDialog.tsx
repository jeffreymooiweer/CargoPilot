import { useState } from "react";
import { useTranslation } from "react-i18next";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 font-mono text-sm min-h-[12rem]";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

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
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50" role="dialog" aria-modal>
      <div className={`${panelClass} w-full sm:max-w-2xl max-h-[90vh] overflow-y-auto p-4 sm:p-6 space-y-4`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("review.importTitle")}</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t("review.importHint")}</p>
          </div>
          <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 text-2xl leading-none p-2" aria-label={t("review.cancel")}>
            ×
          </button>
        </div>
        <textarea className={inputClass} value={text} onChange={(e) => setText(e.target.value)} placeholder={t("wizard.paste")} />
        <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input type="radio" checked={mode === "replace"} onChange={() => setMode("replace")} />
            {t("review.importReplace")}
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input type="radio" checked={mode === "append"} onChange={() => setMode("append")} />
            {t("review.importAppend")}
          </label>
        </div>
        <div className="flex flex-col-reverse sm:flex-row gap-2 sm:justify-end">
          <button type="button" onClick={onClose} className="px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-sm min-h-[44px]">
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
            className="bg-brand-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium min-h-[44px] disabled:opacity-50"
          >
            {t("review.importConfirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
