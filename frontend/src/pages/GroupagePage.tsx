/** Groupage: several consignments on one vehicle, judged as one load.
 *
 *  Every other screen reasons about a consignment, because a consignment is
 *  what somebody fills in. The ADR looks at what is on the vehicle, and three
 *  of its rules cannot be settled per consignment however carefully each one is
 *  completed: the 1.1.3.6 points, the mixed loading of 7.5.2, and the
 *  limited-quantities marking of 3.4.13.
 *
 *  The consignments come in as the shipment exports the export step already
 *  writes (`cargopilot.shipment`). That is deliberate: this application stores
 *  no shipment history, so there is no list to pick from, and inventing one
 *  would break the privacy stance the rest of it keeps. A file the planner
 *  already has is the honest input.
 *
 *  Nothing here is saved. The trip lives in this page and in the request, and
 *  reloading loses it — which is the correct behaviour, not a shortcoming.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../api/client";
import type { TripResult } from "../api/client";
import { useToast } from "../toast/ToastProvider";

type Loaded = {
  name: string;
  entries: Record<string, unknown>[];
  profiles: string[];
  fileName: string;
};

/** The export's own name for the consignment, or the file's, or nothing. */
function nameOf(payload: Record<string, any>, fileName: string): string {
  const values = (payload?.consignment ?? {}) as Record<string, string>;
  return (
    values.shipment_reference ||
    values.consignor_name ||
    values.consignee_name ||
    fileName.replace(/\.json$/i, "")
  );
}

export default function GroupagePage() {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const [loaded, setLoaded] = useState<Loaded[]>([]);
  const [unitMass, setUnitMass] = useState("");
  const [result, setResult] = useState<TripResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function addFiles(files: FileList | null) {
    if (!files?.length) return;
    const added: Loaded[] = [];
    for (const file of Array.from(files)) {
      try {
        const payload = JSON.parse(await file.text());
        // A file that is not a shipment export is refused by name rather than
        // half-read: a trip built from the wrong half of somebody's disk would
        // produce a confident answer about goods that are not on the vehicle.
        if (payload?.format !== "cargopilot.shipment") {
          toast.error(t("groupage.notAnExport", { file: file.name }));
          continue;
        }
        const entries = Array.isArray(payload.dangerous_goods) ? payload.dangerous_goods : [];
        if (!entries.length) {
          toast.error(t("groupage.noDangerousGoods", { file: file.name }));
          continue;
        }
        added.push({
          name: nameOf(payload, file.name),
          entries,
          profiles: Array.isArray(payload.regulations) ? payload.regulations : [],
          fileName: file.name,
        });
      } catch {
        toast.error(t("groupage.unreadable", { file: file.name }));
      }
    }
    if (added.length) {
      setLoaded((current) => [...current, ...added]);
      setResult(null);
    }
  }

  function rename(index: number, name: string) {
    setLoaded((current) => current.map((c, i) => (i === index ? { ...c, name } : c)));
    setResult(null);
  }

  function remove(index: number) {
    setLoaded((current) => current.filter((_, i) => i !== index));
    setResult(null);
  }

  const profiles = [...new Set(loaded.flatMap((c) => c.profiles))];

  async function assess() {
    setBusy(true);
    try {
      const mass = unitMass.trim() === "" ? null : Number(unitMass);
      setResult(
        await api.dgTrip({
          consignments: loaded.map((c) => ({ name: c.name, entries: c.entries })),
          profiles,
          language: i18n.language,
          unit_max_mass_tonnes: Number.isFinite(mass as number) ? (mass as number) : null,
        }),
      );
    } catch {
      toast.error(t("groupage.failed"));
    } finally {
      setBusy(false);
    }
  }

  const card = "rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900";
  const input =
    "rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800";

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-4">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
          {t("groupage.title")}
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{t("groupage.intro")}</p>
      </header>

      <section className={card}>
        <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
          {t("groupage.addConsignments")}
        </label>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          {t("groupage.addHint")}
        </p>
        <input
          type="file"
          accept="application/json,.json"
          multiple
          className="mt-2 block w-full text-sm"
          onChange={(e) => {
            void addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </section>

      {loaded.length > 0 && (
        <section className={`${card} space-y-3`}>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("groupage.onTheVehicle", { count: loaded.length })}
          </h2>
          {loaded.map((c, index) => (
            <div key={`${c.fileName}-${index}`} className="flex items-center gap-2">
              <input
                className={`${input} flex-1`}
                value={c.name}
                aria-label={t("groupage.consignmentName")}
                onChange={(e) => rename(index, e.target.value)}
              />
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {t("groupage.positions", {
                  count: c.entries.reduce(
                    (n, e: any) => n + ((e?.products?.length as number) ?? 0),
                    0,
                  ),
                })}
              </span>
              <button
                type="button"
                className="rounded-lg px-2 py-1 text-sm text-slate-500 hover:text-red-600"
                onClick={() => remove(index)}
              >
                {t("common.remove")}
              </button>
            </div>
          ))}

          <div>
            <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
              {t("groupage.unitMass")}
            </label>
            {/* 3.4.13 turns on the vehicle's permitted maximum mass, which is
                the one thing about the load the application cannot derive.
                Optional, and its absence is reported rather than guessed. */}
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              {t("groupage.unitMassHint")}
            </p>
            <input
              className={`${input} mt-1 w-32`}
              inputMode="decimal"
              value={unitMass}
              onChange={(e) => setUnitMass(e.target.value)}
              placeholder="18"
            />
          </div>

          <button
            type="button"
            disabled={busy || loaded.length < 2}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            onClick={() => void assess()}
          >
            {busy ? t("groupage.assessing") : t("groupage.assess")}
          </button>
          {loaded.length < 2 && (
            <p className="text-xs text-slate-500 dark:text-slate-400">{t("groupage.needTwo")}</p>
          )}
        </section>
      )}

      {result && (
        <section className="space-y-4">
          {result.exemption_lost && (
            <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-100">
              <p className="font-semibold">{t("groupage.exemptionLost")}</p>
              <p className="mt-1">{result.exemption_lost.message}</p>
            </div>
          )}

          <div className={card}>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {t("groupage.apartAndTogether")}
            </h2>
            <table className="mt-2 w-full text-sm">
              <tbody>
                {result.consignments.map((c) => (
                  <tr key={c.name} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-1 text-slate-800 dark:text-slate-200">{c.name}</td>
                    <td className="py-1 text-right tabular-nums">{c.points ?? "—"}</td>
                    <td className="py-1 pl-3 text-right text-xs text-slate-500 dark:text-slate-400">
                      {c.exempt === true
                        ? t("groupage.exempt")
                        : c.exempt === false
                          ? t("groupage.notExempt")
                          : t("groupage.incomplete")}
                    </td>
                  </tr>
                ))}
                <tr className="font-semibold">
                  <td className="py-1">{t("groupage.together")}</td>
                  <td className="py-1 text-right tabular-nums">
                    {result.adr_points.total_points}
                  </td>
                  <td className="py-1 pl-3 text-right text-xs">
                    {t("groupage.threshold", { value: result.adr_points.threshold })}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {result.mixed_loading.length > 0 && (
            <div className={card}>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {t("groupage.mixedLoading")}
              </h2>
              <ul className="mt-2 space-y-2 text-sm">
                {result.mixed_loading.map((w, i) => (
                  <li key={i} className="text-slate-700 dark:text-slate-300">
                    {w.message}
                    {w.products && (
                      <span className="block text-xs text-slate-500 dark:text-slate-400">
                        {w.products}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className={card}>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {result.lq_marking.rule}
            </h2>
            <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">
              {result.lq_marking.message}
            </p>
          </div>

          <p className="text-xs text-slate-500 dark:text-slate-400">{t("groupage.notStored")}</p>
        </section>
      )}
    </div>
  );
}
