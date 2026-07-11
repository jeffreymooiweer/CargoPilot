import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { applySystemTheme, applyTheme, getStoredTheme, type Theme } from "../theme";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";

export default function SettingsPage() {
  const { t, i18n } = useTranslation();
  const [theme, setTheme] = useState<Theme | "system">(() => getStoredTheme() ?? "system");
  const [version, setVersion] = useState("");

  useEffect(() => {
    api.health().then((h) => setVersion(h.version)).catch(() => {});
  }, []);

  useEffect(() => {
    const sync = () => setTheme(getStoredTheme() ?? "system");
    window.addEventListener("cargopilot-theme-change", sync);
    return () => window.removeEventListener("cargopilot-theme-change", sync);
  }, []);

  const notifyTheme = () => window.dispatchEvent(new Event("cargopilot-theme-change"));

  const setLanguage = (lang: string) => {
    i18n.changeLanguage(lang);
    localStorage.setItem("cargopilot-lang", lang);
  };

  return (
    <div className="space-y-6 max-w-lg">
      <div>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{t("settings.title")}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t("settings.intro")}</p>
      </div>

      <div className={`${panelClass} p-5 space-y-5`}>
        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("settings.theme")}</label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t("settings.themeHint")}</p>
          <div className="grid grid-cols-3 gap-2 mt-2">
            {(["light", "dark", "system"] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => {
                  if (option === "system") {
                    applySystemTheme();
                    setTheme("system");
                  } else {
                    applyTheme(option);
                    setTheme(option);
                  }
                  notifyTheme();
                }}
                className={`px-3 py-2.5 rounded-lg text-sm min-h-[44px] border ${
                  theme === option
                    ? "border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-950/50 dark:text-brand-200"
                    : "border-slate-200 dark:border-slate-700"
                }`}
              >
                {t(option === "system" ? "settings.auto" : `theme.${option}`)}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("settings.language")}</label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t("settings.languageHint")}</p>
          <select className={`${inputClass} mt-2`} value={i18n.language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="nl">Nederlands</option>
            <option value="en">English</option>
          </select>
        </div>

        <p className="text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800 pt-3">
          {t("settings.autoDetectNote")}
        </p>
        {version && (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t("settings.version")}: {version}
          </p>
        )}
      </div>
    </div>
  );
}
