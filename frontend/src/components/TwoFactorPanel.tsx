import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, TwoFactorSetup, TwoFactorStatus } from "../api/client";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const buttonPrimary =
  "bg-brand-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";
const buttonSecondary =
  "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 min-h-[44px] text-sm";

/** Setting up, checking on, and switching off your own second factor.
 *
 *  The recovery codes are shown once, here, and never again: only their
 *  hashes are kept. That is worth saying on the screen rather than only in
 *  the documentation, because somebody who closes this panel without
 *  writing them down has lost them. */
export default function TwoFactorPanel() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<TwoFactorStatus | null>(null);
  const [setup, setSetup] = useState<TwoFactorSetup | null>(null);
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = () => api.twoFactorStatus().then(setStatus).catch((e) => setError(String(e)));
  useEffect(() => {
    void load();
  }, []);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await action();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const start = (method: "totp" | "email") =>
    run(async () => {
      setCodes(null);
      setSetup(await api.twoFactorStart(method));
      setCode("");
    });

  const confirm = () =>
    run(async () => {
      const result = await api.twoFactorConfirm(code);
      setCodes(result.recovery_codes);
      setSetup(null);
      setCode("");
      await load();
    });

  const disable = () =>
    run(async () => {
      await api.twoFactorDisable(code);
      setCode("");
      setMessage(t("twoFactor.disabled"));
      await load();
    });

  const newCodes = () =>
    run(async () => {
      const result = await api.twoFactorNewRecoveryCodes();
      setCodes(result.recovery_codes);
      await load();
    });

  if (!status) {
    return error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null;
  }

  return (
    <section className={`${panelClass} p-5 space-y-4`}>
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("twoFactor.title")}
        </h3>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t("twoFactor.intro")}</p>
      </div>

      {status.required && !status.active && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-300">
          {t("twoFactor.requiredHere")}
        </p>
      )}

      {status.active ? (
        <div className="space-y-3">
          <p className="text-sm text-slate-700 dark:text-slate-200">
            {t(status.method === "email" ? "twoFactor.onByMail" : "twoFactor.onByApp")}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t("twoFactor.codesLeft", { count: status.recovery_codes_left })}
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" className={buttonSecondary} disabled={busy} onClick={newCodes}>
              {t("twoFactor.newCodes")}
            </button>
          </div>
          {!status.required && (
            <div className="border-t border-slate-100 pt-3 dark:border-slate-800">
              <label className="text-sm font-medium text-slate-800 dark:text-slate-200" htmlFor="off-code">
                {t("twoFactor.turnOff")}
              </label>
              <p className="text-xs text-slate-500 dark:text-slate-400">{t("twoFactor.turnOffHint")}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <input
                  id="off-code"
                  className={`${inputClass} max-w-[12rem]`}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                />
                <button type="button" className={buttonSecondary} disabled={busy || !code.trim()} onClick={disable}>
                  {t("twoFactor.turnOffDo")}
                </button>
              </div>
            </div>
          )}
        </div>
      ) : setup ? (
        <div className="space-y-3">
          {setup.method === "totp" ? (
            <>
              <p className="text-sm text-slate-700 dark:text-slate-200">{t("twoFactor.scan")}</p>
              {/* Drawn by this server, not fetched from a QR service: the
                  secret in it is the whole secret. */}
              <div
                className="inline-block rounded-lg bg-white p-2"
                dangerouslySetInnerHTML={{ __html: setup.qr_svg }}
              />
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t("twoFactor.orType")} <code className="font-mono">{setup.secret}</code>
              </p>
            </>
          ) : (
            <p className="text-sm text-slate-700 dark:text-slate-200">{t("twoFactor.mailSent")}</p>
          )}
          <label className="block text-sm font-medium text-slate-800 dark:text-slate-200" htmlFor="confirm-code">
            {t("twoFactor.enterCode")}
          </label>
          <div className="flex flex-wrap gap-2">
            <input
              id="confirm-code"
              className={`${inputClass} max-w-[12rem]`}
              autoComplete="one-time-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
            <button type="button" className={buttonPrimary} disabled={busy || !code.trim()} onClick={confirm}>
              {t("twoFactor.confirm")}
            </button>
            <button type="button" className={buttonSecondary} disabled={busy} onClick={() => setSetup(null)}>
              {t("twoFactor.cancel")}
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <button type="button" className={buttonPrimary} disabled={busy} onClick={() => start("totp")}>
            {t("twoFactor.setUpApp")}
          </button>
          <button type="button" className={buttonSecondary} disabled={busy} onClick={() => start("email")}>
            {t("twoFactor.setUpMail")}
          </button>
        </div>
      )}

      {codes && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 dark:border-emerald-900/50 dark:bg-emerald-900/20">
          <p className="text-sm font-medium text-emerald-900 dark:text-emerald-200">
            {t("twoFactor.recoveryTitle")}
          </p>
          <p className="mt-0.5 text-xs text-emerald-800 dark:text-emerald-300">
            {t("twoFactor.recoveryHint")}
          </p>
          <ul className="mt-2 grid grid-cols-2 gap-1 font-mono text-sm text-emerald-900 dark:text-emerald-100">
            {codes.map((one) => (
              <li key={one}>{one}</li>
            ))}
          </ul>
        </div>
      )}

      {message && <p className="text-sm text-emerald-700 dark:text-emerald-400">{message}</p>}
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </section>
  );
}
