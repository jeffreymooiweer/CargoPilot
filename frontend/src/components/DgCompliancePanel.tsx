import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ComplianceWarning, DgComplianceResult, DgEntry } from "../api/client";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

interface Props {
  entries: DgEntry[];
  profiles: string[];
}

const STATUS_STYLES: Record<string, string> = {
  exempt_possible: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  above_threshold: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  not_exempt: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  incomplete: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
};

export default function DgCompliancePanel({ entries, profiles }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language.startsWith("en") ? "en" : "nl";
  const [result, setResult] = useState<DgComplianceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = useCallback(async () => {
    if (entries.length === 0 || profiles.length === 0) return;
    setLoading(true);
    setError("");
    try {
      setResult(await api.dgCompliance(entries, profiles, lang));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [entries, profiles, lang]);

  useEffect(() => {
    run();
    // Alleen bij mount en profielwissel automatisch; daarna via de knop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profiles.join(",")]);

  if (entries.length === 0 || profiles.length === 0) return null;

  const adr = result?.adr_points;
  const warnings: ComplianceWarning[] = [
    ...(result?.adr_mixed_loading ?? []),
    ...(result?.iata_segregation ?? []),
  ];

  return (
    <div className={`${panelClass} space-y-4 p-4 sm:p-6`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-semibold text-slate-900 dark:text-slate-100">{t("compliance.title")}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t("compliance.intro", { profiles: profiles.join(", ") })}
          </p>
        </div>
        <button
          type="button"
          onClick={run}
          disabled={loading}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          {loading ? t("compliance.checking") : t("compliance.recheck")}
        </button>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      {adr && (
        <section className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {t("compliance.adrPointsTitle")}
            </h4>
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_STYLES[adr.status]}`}>
              {t(`compliance.status.${adr.status}`)}
            </span>
            <span className="text-sm text-slate-600 dark:text-slate-300">
              {t("compliance.totalPoints", { total: adr.total_points, threshold: adr.threshold })}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[480px] text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400">
                  <th className="py-1.5 pr-2 font-medium">{t("compliance.colProduct")}</th>
                  <th className="py-1.5 pr-2 font-medium">{t("compliance.colCategory")}</th>
                  <th className="py-1.5 pr-2 font-medium">{t("compliance.colQuantity")}</th>
                  <th className="py-1.5 pr-2 font-medium">{t("compliance.colFactor")}</th>
                  <th className="py-1.5 font-medium">{t("compliance.colPoints")}</th>
                </tr>
              </thead>
              <tbody className="text-slate-700 dark:text-slate-300">
                {adr.rows.map((row, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-1.5 pr-2">{row.product}</td>
                    <td className="py-1.5 pr-2">{row.transport_category ?? "—"}</td>
                    <td className="py-1.5 pr-2">{row.quantity ?? "—"}</td>
                    <td className="py-1.5 pr-2">{row.factor != null ? `×${row.factor}` : "—"}</td>
                    <td className="py-1.5 font-medium">{row.points ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {adr.status === "incomplete" && (
            <p className="text-xs text-amber-600 dark:text-amber-300">
              {t("compliance.incompleteHint", { products: adr.incomplete_products.join(", ") })}
            </p>
          )}
          {adr.status === "not_exempt" && (
            <p className="text-xs text-red-600 dark:text-red-400">
              {t("compliance.category0Hint", { products: adr.category0_products.join(", ") })}
            </p>
          )}
          <p className="text-[11px] text-slate-500 dark:text-slate-400">{adr.quantity_units_note}</p>

          {adr.status === "exempt_possible" && (
            <details className="text-xs text-slate-600 dark:text-slate-300">
              <summary className="cursor-pointer font-medium">{t("compliance.exemptDetails")}</summary>
              <p className="mt-1 font-medium">{t("compliance.exemptFrom")}</p>
              <ul className="ml-4 list-disc">{adr.exempt_provisions.map((x, i) => <li key={i}>{x}</li>)}</ul>
              <p className="mt-1 font-medium">{t("compliance.stillRequired")}</p>
              <ul className="ml-4 list-disc">{adr.still_required.map((x, i) => <li key={i}>{x}</li>)}</ul>
            </details>
          )}
          {adr.status === "above_threshold" && (
            <p className="text-xs text-amber-700 dark:text-amber-300">{t("compliance.aboveThresholdHint")}</p>
          )}
        </section>
      )}

      {warnings.length > 0 && (
        <section className="space-y-2">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {t("compliance.segregationTitle")}
          </h4>
          {warnings.map((w, i) => (
            <div
              key={i}
              className={`rounded-lg border px-3 py-2 text-xs ${
                w.severity === "error"
                  ? "border-red-200 bg-red-50 text-red-800 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300"
                  : "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-300"
              }`}
            >
              <p className="font-semibold">{w.rule}</p>
              <p className="mt-0.5">{w.message}</p>
              <p className="mt-0.5 opacity-80">{w.products}</p>
            </div>
          ))}
        </section>
      )}
      {result && warnings.length === 0 && (result.adr_mixed_loading || result.iata_segregation) && (
        <p className="text-xs text-emerald-700 dark:text-emerald-300">{t("compliance.noSegregationIssues")}</p>
      )}

      {(result?.q_values?.length ?? 0) > 0 && (
        <section className="space-y-2">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("compliance.qTitle")}</h4>
          {result!.q_values!.map((q, i) => (
            <div
              key={i}
              className={`rounded-lg border px-3 py-2 text-xs ${
                q.exceeded
                  ? "border-red-200 bg-red-50 text-red-800 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300"
                  : "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-900/20 dark:text-emerald-300"
              }`}
            >
              <p className="font-semibold">
                {t("compliance.qValueFor", { position: String(q.position), value: q.q_value })}
                {q.exceeded ? ` — ${t("compliance.qExceeded")}` : ""}
              </p>
              <p className="mt-0.5 opacity-80">
                {q.components.map((c) => `${c.product}: ${c.net_quantity}/${c.max_per_package}`).join("  ·  ")}
              </p>
            </div>
          ))}
          <p className="text-[11px] text-slate-500 dark:text-slate-400">{result!.q_values![0].note}</p>
        </section>
      )}

      {(result?.cargo_aircraft_only_products?.length ?? 0) > 0 && (
        <p className="text-xs text-amber-700 dark:text-amber-300">
          {t("compliance.caoHint", { products: result!.cargo_aircraft_only_products!.join(", ") })}
        </p>
      )}

      <p className="text-[11px] italic text-slate-400 dark:text-slate-500">{t("compliance.disclaimer")}</p>
    </div>
  );
}
