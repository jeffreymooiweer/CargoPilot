import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  AssistantStatus,
  InstanceSettings,
  SettingsOptions,
  ThemeChoice,
  UnCardStoreStatus,
  User,
  UserPreferences,
  api,
} from "../api/client";
import SignaturePad from "../components/SignaturePad";
import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES } from "../i18n/language";
import { usePreferences } from "../settings/preferences";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const buttonPrimary =
  "bg-brand-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";
const buttonSecondary =
  "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 min-h-[44px] text-sm inline-flex items-center";

const THEMES: ThemeChoice[] = ["light", "dark", "system"];

/** The settings, grouped the way someone looks for them: how it looks, what a
 *  new shipment starts with, who I am — and, for an administrator, what
 *  applies to the whole installation and the assistant's model. One long
 *  scroll made the personal fields and the instance-wide ones look like one
 *  list, which they are emphatically not. */
const TABS = [
  { key: "appearance", label: "settings.tabAppearance", admin: false },
  { key: "shipment", label: "settings.tabShipment", admin: false },
  { key: "details", label: "settings.tabDetails", admin: false },
  { key: "admin", label: "settings.tabAdmin", admin: true },
  { key: "assistant", label: "settings.tabAssistant", admin: true },
] as const;

type TabKey = (typeof TABS)[number]["key"];

/** The personal tabs share one draft and therefore one save button. */
const PERSONAL_TABS: TabKey[] = ["appearance", "shipment", "details"];

interface Props {
  user: User;
}

export default function SettingsPage({ user }: Props) {
  const { t } = useTranslation();
  const { preferences, save, loaded } = usePreferences();
  const [draft, setDraft] = useState<UserPreferences>(preferences);
  const [options, setOptions] = useState<SettingsOptions | null>(null);
  const [version, setVersion] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [tab_, setTab] = useState<TabKey>("appearance");

  useEffect(() => setDraft(preferences), [preferences]);

  useEffect(() => {
    api.health().then((h) => setVersion(h.version)).catch(() => {});
    api.settingsOptions().then(setOptions).catch(() => {});
  }, []);

  const dirty = useMemo(
    () => JSON.stringify(draft) !== JSON.stringify(preferences),
    [draft, preferences],
  );

  const set = <K extends keyof UserPreferences>(key: K, value: UserPreferences[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setSaved(false);
  };

  /** The theme and the language take effect the moment they are picked — they
   *  always did, and having to press Save to see a dark screen would be a step
   *  backwards. Everything else waits for the button. */
  const setAndApply = async (values: Partial<UserPreferences>) => {
    const next = { ...draft, ...values };
    setDraft(next);
    setError("");
    try {
      await save(next);
    } catch (e) {
      setError(String(e));
    }
  };

  const submit = async () => {
    setSaving(true);
    setError("");
    try {
      await save(draft);
      setSaved(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const tabs = TABS.filter((tab) => !tab.admin || user.role === "admin");
  const active = tabs.some((tab) => tab.key === tab_) ? tab_ : "appearance";

  return (
    <div className="space-y-6 max-w-2xl pb-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{t("settings.title")}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t("settings.intro")}</p>
      </div>

      {/* On a phone a row of tabs would either wrap or scroll out of sight;
          a dropdown says which group you are in and holds the rest one tap
          away. From the medium breakpoint the tabs themselves fit. */}
      <div className="md:hidden">
        <label htmlFor="settings-tab" className="sr-only">
          {t("settings.tabPick")}
        </label>
        <select
          id="settings-tab"
          className={inputClass}
          value={active}
          onChange={(event) => setTab(event.target.value as TabKey)}
        >
          {tabs.map((tab) => (
            <option key={tab.key} value={tab.key}>
              {t(tab.label as "settings.tabAppearance")}
            </option>
          ))}
        </select>
      </div>

      <div
        role="tablist"
        aria-label={t("settings.title")}
        className="hidden md:flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-800"
      >
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={active === tab.key}
            onClick={() => setTab(tab.key)}
            className={`-mb-px rounded-t-lg border-b-2 px-4 py-2.5 text-sm font-medium transition ${
              active === tab.key
                ? "border-brand-600 text-brand-700 dark:border-brand-400 dark:text-brand-300"
                : "border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            {t(tab.label as "settings.tabAppearance")}
          </button>
        ))}
      </div>

      {active === "appearance" && (
      <section className={`${panelClass} p-5 space-y-5`}>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("settings.appearance")}
        </h3>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("settings.theme")}</label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t("settings.themeHint")}</p>
          <div className="grid grid-cols-3 gap-2 mt-2">
            {THEMES.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => void setAndApply({ theme: option })}
                className={`px-3 py-2.5 rounded-lg text-sm min-h-[44px] border ${
                  draft.theme === option
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
          <select
            className={`${inputClass} mt-2`}
            value={draft.language || ""}
            onChange={(e) => void setAndApply({ language: e.target.value })}
          >
            {SUPPORTED_LANGUAGES.map((language) => (
              <option key={language} value={language}>
                {LANGUAGE_NAMES[language]}
              </option>
            ))}
          </select>
        </div>

        <p className="text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800 pt-3">
          {t("settings.autoDetectNote")}
        </p>
      </section>
      )}

      {active === "shipment" && (
      <section className={`${panelClass} p-5 space-y-5`}>
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("settings.shipmentDefaults")}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t("settings.shipmentDefaultsHint")}</p>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("settings.defaultModality")}</label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t("settings.defaultModalityHint")}</p>
          <select
            className={`${inputClass} mt-2`}
            value={draft.default_modality}
            onChange={(e) => set("default_modality", e.target.value)}
          >
            <option value="">{t("settings.askEveryTime")}</option>
            {(options?.modalities ?? []).map((modality) => (
              <option key={modality} value={modality}>
                {t(`modality.${modality}`)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("settings.defaultUnit")}</label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t("settings.defaultUnitHint")}</p>
          <select
            className={`${inputClass} mt-2`}
            value={draft.default_unit}
            onChange={(e) => set("default_unit", e.target.value)}
          >
            {(options?.units ?? []).map((unit) => (
              <option key={unit.code} value={unit.code}>
                {t(`units.name.${unit.code}`, { defaultValue: `${unit.code} (${unit.symbol})` })}
              </option>
            ))}
          </select>
        </div>

        <Toggle
          label={t("settings.prefillDocuments")}
          hint={t("settings.prefillDocumentsHint")}
          checked={draft.prefill_documents}
          onChange={(value) => set("prefill_documents", value)}
        />
      </section>
      )}

      {active === "details" && (
      <section className={`${panelClass} p-5 space-y-4`}>
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("settings.myDetails")}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t("settings.myDetailsHint")}</p>
        </div>

        <Field
          label={t("settings.consignorName")}
          value={draft.consignor_name}
          onChange={(value) => set("consignor_name", value)}
        />
        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {t("settings.consignorAddress")}
          </label>
          <textarea
            className={`${inputClass} mt-1 min-h-[80px]`}
            value={draft.consignor_address}
            onChange={(e) => set("consignor_address", e.target.value)}
          />
        </div>
        <Field
          label={t("settings.consignorContact")}
          value={draft.consignor_contact}
          onChange={(value) => set("consignor_contact", value)}
        />
        <Field
          label={t("settings.carrierName")}
          value={draft.carrier_name}
          onChange={(value) => set("carrier_name", value)}
        />
        <Field
          label={t("settings.loadingPoint")}
          value={draft.loading_point}
          onChange={(value) => set("loading_point", value)}
        />
        <Field
          label={t("settings.emergencyContact")}
          hint={t("settings.emergencyContactHint")}
          value={draft.emergency_contact}
          onChange={(value) => set("emergency_contact", value)}
        />
      </section>
      )}

      {active === "details" && (
        <div className="space-y-2">
          <p className="text-xs text-slate-500 dark:text-slate-400">{t("settings.signatureHint")}</p>
          <SignaturePad
            value={draft.signature_image || null}
            onChange={(dataUrl) => set("signature_image", dataUrl ?? "")}
          />
        </div>
      )}

      {/* One draft across the personal tabs, so one save button — switching
          tabs never loses what was typed on another. */}
      {PERSONAL_TABS.includes(active) && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" onClick={submit} disabled={saving || !dirty} className={buttonPrimary}>
              {saving ? t("settings.saving") : t("settings.save")}
            </button>
            {saved && !dirty && (
              <span className="text-sm text-emerald-600 dark:text-emerald-400">{t("settings.saved")}</span>
            )}
            {!loaded && <span className="text-sm text-slate-500 dark:text-slate-400">{t("wizard.loading")}</span>}
          </div>

          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        </>
      )}

      {active === "admin" && user.role === "admin" && <AdminSettings />}
      {active === "assistant" && user.role === "admin" && <AssistantAdmin />}

      {version && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {t("settings.version")}: {version}
        </p>
      )}
    </div>
  );
}

/**
 * The instance-wide settings, for administrators.
 *
 * Separate from the block above in more than looks: these apply to everyone, and
 * two of them decide whether this installation talks to the internet at all. The
 * server enforces that with `require_admin`; hiding the section here only keeps
 * it out of the way of people who cannot change it anyway.
 */
function AdminSettings() {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<InstanceSettings | null>(null);
  const [draft, setDraft] = useState<InstanceSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .instanceSettings()
      .then((values) => {
        setSettings(values);
        setDraft(values);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (!draft || !settings) {
    return error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null;
  }

  const dirty = JSON.stringify(draft) !== JSON.stringify(settings);

  const set = <K extends keyof InstanceSettings>(key: K, value: InstanceSettings[K]) => {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
    setSaved(false);
  };

  const submit = async () => {
    setSaving(true);
    setError("");
    try {
      const stored = await api.saveInstanceSettings(draft);
      setSettings(stored);
      setDraft(stored);
      setSaved(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-900/50 dark:bg-amber-900/20">
        <h3 className="text-sm font-semibold text-amber-900 dark:text-amber-200">{t("settings.adminTitle")}</h3>
        <p className="text-xs text-amber-800 dark:text-amber-300 mt-1">{t("settings.adminIntro")}</p>
      </div>

      <section className={`${panelClass} p-5 space-y-5`}>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("settings.adminNewUsers")}
        </h4>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {t("settings.adminDefaultLanguage")}
          </label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {t("settings.adminDefaultLanguageHint")}
          </p>
          <select
            className={`${inputClass} mt-2`}
            value={draft.default_language}
            onChange={(e) => set("default_language", e.target.value)}
          >
            {SUPPORTED_LANGUAGES.map((language) => (
              <option key={language} value={language}>
                {LANGUAGE_NAMES[language]}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {t("settings.adminDefaultTheme")}
          </label>
          <select
            className={`${inputClass} mt-2`}
            value={draft.default_theme}
            onChange={(e) => set("default_theme", e.target.value as ThemeChoice)}
          >
            {THEMES.map((option) => (
              <option key={option} value={option}>
                {t(option === "system" ? "settings.auto" : `theme.${option}`)}
              </option>
            ))}
          </select>
        </div>

        <Field
          label={t("settings.organisationName")}
          hint={t("settings.organisationHint")}
          value={draft.organisation_name}
          onChange={(value) => set("organisation_name", value)}
        />
        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {t("settings.organisationAddress")}
          </label>
          <textarea
            className={`${inputClass} mt-1 min-h-[80px]`}
            value={draft.organisation_address}
            onChange={(e) => set("organisation_address", e.target.value)}
          />
        </div>
      </section>

      <section className={`${panelClass} p-5 space-y-5`}>
        <div>
          <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("settings.adminNetwork")}
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t("settings.adminNetworkHint")}</p>
        </div>

        <Toggle
          label={t("settings.addressLookup")}
          hint={t("settings.addressLookupHint")}
          checked={draft.address_lookup_enabled}
          onChange={(value) => set("address_lookup_enabled", value)}
        />
        {draft.address_lookup_enabled && (
          <>
            <Field
              label={t("settings.addressApiUrl")}
              hint={t("settings.addressApiUrlHint")}
              value={draft.address_api_url}
              onChange={(value) => set("address_api_url", value)}
            />
            <div>
              <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
                {t("settings.addressTimeout")}
              </label>
              <input
                type="number"
                min={1}
                max={60}
                step={0.5}
                className={`${inputClass} mt-1`}
                value={draft.address_timeout_seconds}
                onChange={(e) => set("address_timeout_seconds", Number(e.target.value))}
              />
            </div>
          </>
        )}

        <Toggle
          label={t("settings.catalogAutoSync")}
          hint={t("settings.catalogAutoSyncHint")}
          checked={draft.catalog_auto_sync}
          onChange={(value) => set("catalog_auto_sync", value)}
        />

        <Toggle
          label={t("settings.updateCheck")}
          hint={t("settings.updateCheckHint")}
          checked={draft.update_check_enabled}
          onChange={(value) => set("update_check_enabled", value)}
        />
      </section>

      <section className={`${panelClass} p-5 space-y-3`}>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("settings.adminUpdates")}
        </h4>
        <p className="text-sm text-slate-700 dark:text-slate-300">{t("settings.updateExplain")}</p>
        <p className="text-sm text-slate-700 dark:text-slate-300">{t("settings.updateCompose")}</p>
        <pre className="overflow-x-auto rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-800 dark:bg-slate-800 dark:text-slate-200">
          docker compose pull && docker compose up -d
        </pre>
        <p className="text-sm text-slate-700 dark:text-slate-300">{t("settings.updateAuto")}</p>
      </section>

      <UnCardsAdminPanel />

      <section className={`${panelClass} p-5 space-y-5`}>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("settings.adminFeatures")}
        </h4>

        <Toggle
          label={t("settings.unCardsEnabled")}
          hint={t("settings.unCardsEnabledHint")}
          checked={draft.un_cards_enabled}
          onChange={(value) => set("un_cards_enabled", value)}
        />

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {t("settings.sessionTimeout")}
          </label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t("settings.sessionTimeoutHint")}</p>
          <input
            type="number"
            min={15}
            max={10080}
            step={15}
            className={`${inputClass} mt-1`}
            value={draft.session_timeout_minutes}
            onChange={(e) => set("session_timeout_minutes", Number(e.target.value))}
          />
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <button type="button" onClick={submit} disabled={saving || !dirty} className={buttonPrimary}>
          {saving ? t("settings.saving") : t("settings.saveAdmin")}
        </button>
        {saved && !dirty && (
          <span className="text-sm text-emerald-600 dark:text-emerald-400">{t("settings.saved")}</span>
        )}
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}

function Field({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{label}</label>
      {hint && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{hint}</p>}
      <input className={`${inputClass} mt-1`} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function Toggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-3 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
      />
      <span className="min-w-0">
        <span className="block text-sm font-medium text-slate-800 dark:text-slate-200">{label}</span>
        {hint && <span className="block text-xs text-slate-500 dark:text-slate-400 mt-0.5">{hint}</span>}
      </span>
    </label>
  );
}

/**
 * The local AI model: an opt-in download, never part of the image.
 *
 * The assistant always works — without a model it runs its deterministic
 * chain. What this block installs is flexibility only: a small local model
 * that reads free text. The download is the assistant's single external
 * fetch, verified against the SHA-256 pinned in the repository, into
 * /data/assistant; while the sources are unpinned the button stays off.
 */
function AssistantAdmin() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<AssistantStatus | null>(null);
  const [error, setError] = useState("");

  const refresh = () =>
    api.assistantStatus().then(setStatus).catch((e) => setError(String(e)));

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (status?.download.state !== "downloading") return;
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status?.download.state]);

  if (!status) {
    return error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null;
  }

  const act = async (action: "download" | "remove") => {
    setError("");
    try {
      await api.assistantModel(action);
      await refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <section className={`${panelClass} p-5 space-y-4`}>
      <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {t("settings.assistantTitle")}
      </h4>
      <p className="text-sm text-slate-600 dark:text-slate-400">{t("settings.assistantIntro")}</p>
      <ul className="space-y-1 text-sm text-slate-700 dark:text-slate-300">
        <li>
          {t("settings.assistantMode")}:{" "}
          <span className="font-medium">
            {status.mode === "model" ? status.model : t("settings.assistantDeterministic")}
          </span>
        </li>
        {status.download.state === "downloading" && (
          <li className="text-amber-700 dark:text-amber-300">
            {t("settings.assistantDownloading")} ({status.download.detail})
          </li>
        )}
        {status.download.state === "error" && (
          <li className="text-red-600 dark:text-red-400">{status.download.detail}</li>
        )}
      </ul>
      <div className="flex flex-wrap gap-2">
        {!status.installed && (
          <button
            type="button"
            disabled={!status.installable || status.download.state === "downloading"}
            onClick={() => void act("download")}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {t("settings.assistantInstall")}
          </button>
        )}
        {status.installed && (
          <button
            type="button"
            onClick={() => void act("remove")}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {t("settings.assistantRemove")}
          </button>
        )}
      </div>
      {!status.installable && !status.installed && (
        <p className="text-xs text-slate-500 dark:text-slate-400">{t("settings.assistantUnpinned")}</p>
      )}
      <p className="text-xs text-slate-500 dark:text-slate-400">{t("settings.assistantFootprint")}</p>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </section>
  );
}

/** The UN card store: what is installed, and the two ways to fill it.
 *
 *  The cards left the Docker image in v1.129.0 — thousands of generated PDFs
 *  live in a GitHub Release instead, and this panel is where an administrator
 *  pulls them in. Checking the remote feed happens only on the button, never
 *  on page load: an admin opening settings is not consent for an outbound
 *  request. The upload path exists for installations that cannot reach
 *  GitHub; both run the same server-side verification.
 */
function UnCardsAdminPanel() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<UnCardStoreStatus | null>(null);
  const [busy, setBusy] = useState<"" | "check" | "download" | "import" | "remove">("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const refresh = (remote = false) =>
    api
      .unCardStoreStatus(remote)
      .then(setStatus)
      .catch((e) => setError(String(e)));

  useEffect(() => {
    void refresh(false);
  }, []);

  const run = async (
    kind: "check" | "download" | "import" | "remove",
    action: () => Promise<unknown>,
    done: string,
  ) => {
    setBusy(kind);
    setMessage("");
    setError("");
    try {
      await action();
      if (done) setMessage(done);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy("");
    }
  };

  const local = status?.local;
  const remote = status?.remote;
  const sizeMb = local?.total_size ? (local.total_size / 1e6).toFixed(0) : null;

  return (
    <section className={`${panelClass} p-5 space-y-4`}>
      <div>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("settings.unCardsStoreTitle")}
        </h4>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t("settings.unCardsStoreIntro")}</p>
      </div>

      {local && !local.installed && (
        <p className="text-sm text-slate-700 dark:text-slate-300">{t("settings.unCardsNone")}</p>
      )}
      {local && local.installed && (
        <div className="space-y-1 text-sm text-slate-700 dark:text-slate-300">
          <p>
            {t("settings.unCardsInstalled", {
              count: local.total_cards ?? 0,
              generated: local.generated_at ?? "?",
            })}
            {sizeMb ? ` (${sizeMb} MB)` : ""}
          </p>
          {local.imported_at && (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {t("settings.unCardsImportedAt", { date: local.imported_at })} · {local.location}
            </p>
          )}
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {Object.entries(local.counts ?? {})
              .map(([modality, count]) => `${modality}: ${count} (${local.editions?.[modality] ?? "?"})`)
              .join(" · ")}
          </p>
        </div>
      )}

      {remote && (
        <p className="text-sm text-slate-700 dark:text-slate-300">
          {remote.reachable === false
            ? t("settings.unCardsRemoteUnreachable")
            : !remote.available
              ? t("settings.unCardsNoRelease")
              : remote.update_available
                ? t("settings.unCardsUpdateAvailable", { tag: remote.tag ?? "" })
                : t("settings.unCardsUpToDate", { tag: remote.tag ?? "" })}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className={buttonSecondary}
          disabled={busy !== ""}
          onClick={() => run("check", () => refresh(true), "")}
        >
          {busy === "check" ? t("settings.unCardsChecking") : t("settings.unCardsCheck")}
        </button>
        <button
          type="button"
          className={buttonPrimary}
          disabled={busy !== ""}
          onClick={() =>
            run(
              "download",
              async () => {
                await api.unCardStoreDownloadLatest();
                await refresh(false);
              },
              t("settings.unCardsImportDone"),
            )
          }
        >
          {busy === "download" ? t("settings.unCardsDownloading") : t("settings.unCardsDownload")}
        </button>
        <label className={`${buttonSecondary} cursor-pointer`}>
          {busy === "import" ? t("settings.unCardsImporting") : t("settings.unCardsImportZip")}
          <input
            type="file"
            accept=".zip"
            className="hidden"
            disabled={busy !== ""}
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (!file) return;
              void run(
                "import",
                async () => {
                  await api.unCardStoreImport(file);
                  await refresh(false);
                },
                t("settings.unCardsImportDone"),
              );
            }}
          />
        </label>
        {local?.installed && (
          <button
            type="button"
            className={buttonSecondary}
            disabled={busy !== ""}
            onClick={() => {
              if (!confirm(t("settings.unCardsRemoveConfirm"))) return;
              void run(
                "remove",
                async () => {
                  await api.unCardStoreRemove();
                  await refresh(false);
                },
                t("settings.unCardsRemoved"),
              );
            }}
          >
            {t("settings.unCardsRemove")}
          </button>
        )}
      </div>

      {message && <p className="text-sm text-emerald-700 dark:text-emerald-400">{message}</p>}
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </section>
  );
}
