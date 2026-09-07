/**
 * The first screen for somebody who is continuing rather than starting.
 *
 * **What this is not.** It is not the front door. `/` is the transport-mode
 * chooser and stays exactly where it is, tiles and all, including the redirect
 * that takes somebody with a preferred mode straight into the wizard without a
 * stop. [The usability plan](../../docs/ux-plan.md) says in as many words:
 * recent shipments as templates *without sending somebody with a default mode
 * through a dashboard first*. Putting this on `/` would do precisely that. So
 * it has an address of its own, nothing is moved out of the way for it, and
 * nobody is sent through it.
 *
 * **What it is for.** Four things, in the order somebody arriving in the
 * morning wants them:
 *
 * 1. **Where you left off.** The running draft, with the way back into it. It
 *    was already restored when you opened the wizard — but only if you
 *    remembered which mode it was in, because a draft is per shipment and the
 *    wizard is per mode. Here it says so.
 * 2. **What today has been.** How many shipments were kept and how many trips
 *    were put together, since midnight. Two numbers the server counts, not two
 *    numbers assembled out of a page of results — a total is a total.
 * 3. **Somewhere to begin.** The available modes, as one press each.
 * 4. **What was made before.** The last few shipments, to open or to start
 *    from.
 *
 * Two and four exist only on an installation that keeps its shipments. Where
 * nothing may be stored there is nothing to come back to, and the page says so
 * rather than showing empty boxes.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";

import { api, ShipmentDetail, ShipmentSummary } from "../api/client";
import { ModalityIcon } from "../components/WizardShell";
import { usePreferences } from "../settings/preferences";
import { readSnapshot } from "../wizard/snapshot";
import { AVAILABLE_MODALITIES } from "./ModalitySelectPage";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const buttonPrimary =
  "inline-flex min-h-[44px] items-center rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-700";
const buttonSecondary =
  "inline-flex min-h-[44px] items-center rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800";

/** Midnight this morning and tonight, as the history filters take them. The
 *  server counts by date, so "today" is the browser's day — which is the day
 *  the person reading it is having. */
function today(): { from: string; to: string } {
  const now = new Date();
  const stamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  return { from: stamp, to: stamp };
}

export default function OverviewPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { publicSettings } = usePreferences();
  const history = !!publicSettings?.history_enabled;

  const [draft, setDraft] = useState<ShipmentDetail | null>(null);
  const [recent, setRecent] = useState<ShipmentSummary[]>([]);
  const [counts, setCounts] = useState<{ shipments: number; trips: number } | null>(null);

  useEffect(() => {
    if (!history) return;
    let alive = true;
    const day = today();
    // Four answers, none of which blocks the others: a page that shows three
    // of its four boxes while the fourth is still coming is better than a
    // page that shows nothing until all four are in.
    api.runningDraft().then((d) => alive && setDraft(d)).catch(() => undefined);
    api
      .shipments({ per_page: 5, page: 1 })
      .then((page) => alive && setRecent(page.items.filter((item) => !item.is_draft)))
      .catch(() => undefined);
    Promise.all([
      api.shipments({ date_from: day.from, date_to: day.to, per_page: 1 }),
      api.trips({ date_from: day.from, date_to: day.to, per_page: 1 }),
    ])
      .then(([shipments, trips]) => alive && setCounts({ shipments: shipments.total, trips: trips.total }))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [history]);

  const draftModality = draft ? readSnapshot(draft.snapshot)?.modality || draft.modality : "";
  const draftTime = draft
    ? new Date(draft.updated_at).toLocaleTimeString(i18n.language, { timeStyle: "short" })
    : "";

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className={`${panelClass} p-5 sm:p-6`}>
        <h2 className="text-xl font-semibold text-slate-900 sm:text-2xl dark:text-slate-100">
          {t("overview.title")}
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-600 dark:text-slate-300">
          {history ? t("overview.intro") : t("overview.introNoHistory")}
        </p>
      </div>

      {draft && (
        <div className={`${panelClass} flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6`}>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {t("overview.resumeTitle")}
            </h3>
            <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-600 dark:text-slate-300">
              <span className="font-medium text-slate-900 dark:text-slate-100">
                {draft.reference || draft.consignee_name || t("wizard.newShipment")}
              </span>
              {draftModality && (
                <span className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                  <ModalityIcon modality={draftModality} className="h-3.5 w-3.5" />
                  {t(`modality.${draftModality}`)}
                </span>
              )}
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {t("draft.savedAt", { time: draftTime })}
              </span>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className={buttonPrimary} to={`/wizard/${draftModality || "road"}`}>
              {t("overview.resume")}
            </Link>
            <button
              type="button"
              className={buttonSecondary}
              onClick={() => {
                void api.discardDraft().catch(() => undefined);
                setDraft(null);
              }}
            >
              {t("draft.discard")}
            </button>
          </div>
        </div>
      )}

      {history && (
        <div className={`${panelClass} p-5 sm:p-6`}>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {t("overview.todayTitle")}
          </h3>
          <div className="mt-3 grid grid-cols-2 gap-4 sm:max-w-md">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {t("overview.todayShipments")}
              </p>
              <p className="mt-0.5 text-2xl font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {counts ? counts.shipments : "—"}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {t("overview.todayTrips")}
              </p>
              <p className="mt-0.5 text-2xl font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {counts ? counts.trips : "—"}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className={`${panelClass} p-5 sm:p-6`}>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {t("overview.startTitle")}
          </h3>
          {/* The tiles, with their pictures and their reasons, are still at
              `/`. This is the short way in for somebody who already knows
              which mode they want. */}
          <Link to="/?choose=1" className="text-xs text-slate-500 hover:underline dark:text-slate-400">
            {t("wizard.changeModality")}
          </Link>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {AVAILABLE_MODALITIES.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => navigate(`/wizard/${key}`)}
              className="inline-flex min-h-[44px] items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:border-brand-400 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <ModalityIcon modality={key} className="h-4 w-4" />
              {t(`modality.${key}`)}
            </button>
          ))}
        </div>
      </div>

      {history && (
        <div className={panelClass}>
          <div className="flex flex-wrap items-baseline justify-between gap-2 px-5 pt-5 sm:px-6 sm:pt-6">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {t("overview.recentTitle")}
            </h3>
            <Link to="/shipments" className="text-xs text-slate-500 hover:underline dark:text-slate-400">
              {t("overview.allShipments")}
            </Link>
          </div>
          {recent.length === 0 ? (
            <p className="px-5 pb-5 pt-2 text-sm text-slate-500 sm:px-6 sm:pb-6 dark:text-slate-400">
              {t("overview.recentEmpty")}
            </p>
          ) : (
            <ul className="mt-2 divide-y divide-slate-100 dark:divide-slate-800">
              {recent.map((shipment) => (
                <li
                  key={shipment.id}
                  className="flex flex-col gap-2 px-5 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">
                      {shipment.reference || shipment.consignee_name || `#${shipment.id}`}
                    </p>
                    <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-slate-500 dark:text-slate-400">
                      <span className="inline-flex items-center gap-1">
                        <ModalityIcon modality={shipment.modality} className="h-3.5 w-3.5" />
                        {t(`modality.${shipment.modality}`)}
                      </span>
                      <span>{new Date(shipment.created_at).toLocaleDateString(i18n.language)}</span>
                      {shipment.has_dangerous_goods && (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                          {t("overview.dg")}
                        </span>
                      )}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <Link
                      className={buttonSecondary}
                      to={`/wizard/${shipment.modality || "road"}?shipment=${shipment.id}`}
                    >
                      {t("overview.open")}
                    </Link>
                    <Link
                      className={buttonSecondary}
                      to={`/wizard/${shipment.modality || "road"}?template=${shipment.id}`}
                    >
                      {t("overview.asTemplate")}
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
