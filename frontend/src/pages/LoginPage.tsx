import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";

const fieldClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2";

export default function LoginPage({ onLogin }: { onLogin: () => void }) {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [setupWarning, setSetupWarning] = useState("");
  // Forgetting a password happens on this screen or nowhere: somebody who
  // cannot get in cannot reach a page behind the sign-in.
  const [forgotOpen, setForgotOpen] = useState(false);
  const [identifier, setIdentifier] = useState("");
  const [forgotBusy, setForgotBusy] = useState(false);
  const [forgotDone, setForgotDone] = useState("");

  const askReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setForgotBusy(true);
    try {
      await api.forgotPassword(identifier);
    } catch {
      // The server answers the same either way; a network hiccup should not
      // be the one thing that tells somebody the address was unknown.
    } finally {
      // The same sentence whatever happened — see the endpoint's own reason.
      setForgotDone(t("login.forgotSent"));
      setForgotBusy(false);
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.login(username, password);
      onLogin();
    } catch (err) {
      setError(String(err));
      const status = await api.setupStatus().catch(() => null);
      if (status && !status.has_admin) setSetupWarning(t("login.setup"));
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 dark:bg-slate-950 px-4">
      <form onSubmit={submit} className="bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-800 p-8 w-full max-w-md space-y-4">
        <div className="text-center">
          <img
            src="/shipping.png"
            alt=""
            aria-hidden="true"
            className="mx-auto h-16 w-16 dark:brightness-0 dark:invert"
          />
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 mt-3">{t("app.name")}</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">{t("app.tagline")}</p>
        </div>
        {setupWarning && <p className="text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg p-3 text-sm">{setupWarning}</p>}
        <div>
          <label className="block text-sm font-medium mb-1 text-slate-800 dark:text-slate-200">{t("login.username")}</label>
          <input className="w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2" value={username} onChange={(e) => setUsername(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1 text-slate-800 dark:text-slate-200">{t("login.password")}</label>
          <input type="password" className="w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>}
        <button type="submit" className="w-full bg-brand-600 hover:bg-brand-700 text-white rounded-lg py-2.5 font-medium">
          {t("login.submit")}
        </button>

        <div className="border-t border-slate-100 dark:border-slate-800 pt-3">
          {!forgotOpen && !forgotDone && (
            <button
              type="button"
              onClick={() => setForgotOpen(true)}
              className="text-sm text-brand-700 hover:underline dark:text-brand-300"
            >
              {t("login.forgot")}
            </button>
          )}
          {forgotOpen && !forgotDone && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-800 dark:text-slate-200">
                {t("login.forgotLabel")}
              </label>
              <p className="text-xs text-slate-500 dark:text-slate-400">{t("login.forgotHint")}</p>
              <input
                className={fieldClass}
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
              />
              <button
                type="button"
                onClick={askReset}
                disabled={forgotBusy || !identifier.trim()}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                {forgotBusy ? t("login.forgotSending") : t("login.forgotSubmit")}
              </button>
            </div>
          )}
          {forgotDone && (
            <p className="text-sm text-slate-600 dark:text-slate-300">{forgotDone}</p>
          )}
        </div>
      </form>
    </div>
  );
}
