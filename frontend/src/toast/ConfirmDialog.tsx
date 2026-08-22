/** A confirmation the application asks in its own voice.
 *
 * Five places used the browser's native `confirm()`: it speaks the browser's
 * language instead of the user's, ignores the theme, and cannot mark the
 * destructive choice. Three of the five became undoable toasts — act now,
 * take it back for six seconds. This dialog is for the two that did not:
 * clearing somebody's two-factor verification is a security action, and
 * applying an update restarts the application under everyone using it. Both
 * deserve a deliberate step *before* they happen, not a regret window after.
 */
import { useEffect, useRef, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

interface Props {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({ open, title, body, confirmLabel, onConfirm, onCancel }: Props) {
  const { t } = useTranslation();
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Focus lands on the safe choice, and Escape is always the safe choice.
  useEffect(() => {
    if (!open) return;
    cancelRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/50" onClick={onCancel} aria-hidden />
      <div
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
        className="relative w-full max-w-md rounded-2xl border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-900"
      >
        <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
        <div className="mt-2 text-sm text-slate-600 dark:text-slate-300">{body}</div>
        <div className="mt-4 flex justify-end gap-2">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {t("toast.cancel")}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-red-700"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
