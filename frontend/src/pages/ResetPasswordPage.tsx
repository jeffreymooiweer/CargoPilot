import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";
import { api } from "../api/client";

const fieldClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2";

/** Where a reset link lands: choose a new password, once.
 *
 *  Reached signed out, which is the whole point — the token in the address
 *  bar is the only proof of identity here, and the server checks it. */
export default function ResetPasswordPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== repeat) {
      setError(t("reset.mismatch"));
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 dark:bg-slate-950 px-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-800 p-8 w-full max-w-md space-y-4">
        <div className="text-center">
          <img
            src="/shipping.png"
            alt=""
            aria-hidden="true"
            className="mx-auto h-16 w-16 dark:brightness-0 dark:invert"
          />
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 mt-3">
            {t("reset.title")}
          </h1>
        </div>

        {done ? (
          <>
            <p className="text-sm text-emerald-700 dark:text-emerald-400">{t("reset.done")}</p>
            <Link
              to="/login"
              className="block w-full rounded-lg bg-brand-600 py-2.5 text-center font-medium text-white hover:bg-brand-700"
            >
              {t("reset.toLogin")}
            </Link>
          </>
        ) : !token ? (
          // Somebody who opened the page by hand rather than from a link.
          <p className="text-sm text-red-600 dark:text-red-400">{t("reset.noToken")}</p>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <p className="text-sm text-slate-600 dark:text-slate-300">{t("reset.intro")}</p>
            <div>
              <label className="block text-sm font-medium mb-1 text-slate-800 dark:text-slate-200" htmlFor="new-password">
                {t("reset.password")}
              </label>
              <input
                id="new-password"
                type="password"
                autoComplete="new-password"
                className={fieldClass}
                minLength={8}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t("reset.passwordHint")}</p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-slate-800 dark:text-slate-200" htmlFor="repeat-password">
                {t("reset.repeat")}
              </label>
              <input
                id="repeat-password"
                type="password"
                autoComplete="new-password"
                className={fieldClass}
                required
                value={repeat}
                onChange={(e) => setRepeat(e.target.value)}
              />
            </div>
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-lg bg-brand-600 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {busy ? t("reset.saving") : t("reset.submit")}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
