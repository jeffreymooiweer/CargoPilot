/**
 * A quiet corner note for the one person who can do something about it.
 *
 * The update check tells an administrator that a newer CargoPilot exists;
 * nobody else operates the container, so nobody else sees the toast. It is
 * deliberately not a modal — an available update is information, not an
 * interruption — and dismissing it remembers the version in localStorage, so
 * the same release does not nag on every page load but a newer one shows up
 * again. The endpoint itself answers admins only and applies the outbound
 * switch server-side; this component just does not ask for anyone else.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, UpdateStatus, User } from "../api/client";

export const DISMISSED_KEY = "cargopilot-update-dismissed";

export default function UpdateToast({ user }: { user: User }) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<UpdateStatus | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (user.role !== "admin") return;
    let cancelled = false;
    void api
      .updateStatus()
      .then((answer) => {
        if (!cancelled) setStatus(answer);
      })
      .catch(() => {
        // An unreachable backend is not this component's news to break.
      });
    return () => {
      cancelled = true;
    };
  }, [user.role]);

  if (
    dismissed ||
    !status?.update_available ||
    !status.latest ||
    localStorage.getItem(DISMISSED_KEY) === status.latest
  ) {
    return null;
  }

  const dismiss = () => {
    localStorage.setItem(DISMISSED_KEY, status.latest ?? "");
    setDismissed(true);
  };

  return (
    <div
      role="status"
      className="fixed bottom-4 right-4 z-40 flex max-w-sm items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-lg dark:border-slate-700 dark:bg-slate-900"
    >
      <div className="min-w-0 text-sm text-slate-700 dark:text-slate-300">
        <p className="font-medium text-slate-900 dark:text-slate-100">
          {t("update.available", { version: status.latest })}
        </p>
        <p className="mt-1">{t("update.hint")}</p>
        {status.url ? (
          <a
            href={status.url}
            target="_blank"
            rel="noreferrer"
            className="mt-1 inline-block text-sky-700 underline dark:text-sky-400"
          >
            {t("update.releaseNotes")}
          </a>
        ) : null}
      </div>
      <button
        type="button"
        onClick={dismiss}
        aria-label={t("update.dismiss")}
        className="rounded-lg px-2 py-1 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
      >
        ×
      </button>
    </div>
  );
}
