import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useTranslation } from "react-i18next";
import { usePreferences } from "../settings/preferences";

export const MODALITIES = ["road", "rail", "sea", "inland", "air", "multimodal"] as const;
export type ModalityKey = (typeof MODALITIES)[number];

/** The modalities a user may actually draw up documents for.
 *
 *  Sea and air are built and reachable and *wrong* in ways that do not
 *  announce themselves, and they carry known gaps listed in
 *  `docs/dg-coverage.md`. A half-right document is worse than no document,
 *  because it is signed and handed over — the consignor has no way to see which
 *  half was right.
 *
 *  **Inland waterway was unlocked in v1.63.0.** It went on the lock in v1.60.0
 *  because it answered its separation question with the *road* table and had no
 *  cone data at all. Both are now answered out of the ADN itself: the exemption
 *  from 1.1.3.6.1, the separation in the holds from 7.1.4.3, and the signals the
 *  vessel must show from 7.1.5.0 — each visible in the panel and on the
 *  document.
 *
 *  **Rail was unlocked in v1.122.0**, over the same bar. Its checks are cited
 *  to RID rather than borrowed: the 1.1.3.6 count per wagon or large
 *  container, its own 7.5.2 tables and the 7.5.3 protective distance, CW 28,
 *  the hazard identification number of 5.4.1.1.1 (j) on the CIM, bulk
 *  admission under RID 7.3, and since v1.121.0 the placarding of chapter 5.3
 *  — package wagons for every class, orange plates only via column (20), the
 *  shunting labels of 5.3.4 as the named condition they are. The CIM flow is
 *  verified end to end in the rail archetypes.
 *
 *  This remains a lock and not a hint. It is checked in three places, because
 *  the tile is not the only way in: a bookmark reaches /wizard/sea directly,
 *  and the default-modality preference navigates there without anyone touching
 *  a tile. Guarding only the tiles would guard only the honest route. */
/** Air was unlocked for one demonstration in v1.117.0 and locked again in
 *  v1.118.0, the demonstration over. Nothing about its coverage changed in
 *  between: the IATA quantity tables are still not held, so the Q value
 *  depends on the M a user enters. That is fine to show while someone is
 *  standing next to the screen explaining it, and not fine on a document
 *  someone signs unattended. */
export const AVAILABLE_MODALITIES: readonly ModalityKey[] = ["road", "rail", "inland"];

export function isModalityKey(value: string | undefined): value is ModalityKey {
  return !!value && (MODALITIES as readonly string[]).includes(value);
}

export function isModalityAvailable(value: string | undefined): value is ModalityKey {
  return isModalityKey(value) && AVAILABLE_MODALITIES.includes(value);
}

export default function ModalitySelectPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { preferences, loaded } = usePreferences();

  // Someone who only ever ships by road should not tap the same tile every
  // morning. `?choose=1` switches the tiles back on for one visit — without it,
  // "change transport mode" would land here and bounce straight back.
  const skipDefault = params.get("choose") === "1";
  const preferred = preferences.default_modality;
  useEffect(() => {
    if (!loaded || skipDefault) return;
    // A preference set while a modality was open must not keep opening it after
    // it has been locked. The tiles come back instead, with the reason on them.
    if (isModalityAvailable(preferred)) navigate(`/wizard/${preferred}`, { replace: true });
  }, [loaded, skipDefault, preferred, navigate]);

  return (
    <div className="space-y-5 sm:space-y-6">
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-8">
        <h2 className="text-xl sm:text-2xl font-semibold text-slate-900 dark:text-slate-100">
          {t("modality.title")}
        </h2>
        <p className="mt-2 text-sm sm:text-base text-slate-600 dark:text-slate-300 max-w-2xl">
          {t("modality.intro")}
        </p>
        <p className="mt-2 text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-2xl">
          {t("dashboard.privacy")}
        </p>
      </div>

      <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {MODALITIES.map((key) => {
          const available = isModalityAvailable(key);
          return (
          <button
            key={key}
            type="button"
            disabled={!available}
            aria-disabled={!available}
            onClick={() => available && navigate(`/wizard/${key}`)}
            title={available ? undefined : t("modality.lockedReason")}
            className={`group relative overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-left shadow-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
              available
                ? "hover:border-brand-400 hover:shadow-lg dark:hover:border-brand-500"
                : "cursor-not-allowed opacity-60 grayscale"
            }`}
          >
            <div className="aspect-[3/1] w-full overflow-hidden">
              <img
                src={`/modalities/${key}-light.webp`}
                alt=""
                aria-hidden="true"
                loading="lazy"
                className="h-full w-full object-cover transition duration-300 group-hover:scale-105 dark:hidden"
              />
              <img
                src={`/modalities/${key}-dark.webp`}
                alt=""
                aria-hidden="true"
                loading="lazy"
                className="hidden h-full w-full object-cover transition duration-300 group-hover:scale-105 dark:block"
              />
            </div>
            <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-5 sm:py-4">
              <div className="min-w-0">
                <h3 className="flex flex-wrap items-center gap-2 font-semibold text-slate-900 dark:text-slate-100">
                  {t(`modality.${key}`)}
                  {!available && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
                      {t("modality.locked")}
                    </span>
                  )}
                </h3>
                <p className="mt-0.5 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                  {available ? t(`modality.${key}Desc`) : t("modality.lockedReason")}
                </p>
              </div>
              <span
                aria-hidden="true"
                className="shrink-0 text-slate-300 transition group-hover:translate-x-1 group-hover:text-brand-500 dark:text-slate-600"
              >
                <svg className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </span>
            </div>
          </button>
          );
        })}
      </div>
    </div>
  );
}
