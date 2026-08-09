import { useTranslation } from "react-i18next";

import { ImportAnalysis, ImportMapping } from "../api/client";

interface Props {
  analysis: ImportAnalysis;
  onChange: (mapping: ImportMapping, hasHeader: boolean) => void;
  busy?: boolean;
}

const FIELDS: (keyof ImportMapping)[] = ["description", "quantity", "unit"];

/** What is in a column, short enough for a dropdown.
 *
 * The heading name if it was recognised, otherwise the first values. With a file
 * that has no recognised heading row that is the only handhold the user has —
 * "column 2" says nothing, "Benaming, Stalen hoekprofiel 80x80x8x6000" does.
 */
function describe(column: { header: string; samples: string[] }): string {
  const parts = [column.header, ...column.samples].filter(Boolean);
  const text = parts.join(" · ");
  return text.length > 60 ? `${text.slice(0, 57)}…` : text;
}

export default function ImportColumnMapping({ analysis, onChange, busy }: Props) {
  const { t } = useTranslation();
  if (analysis.columns.length === 0) return null;

  const guessed = analysis.source === "position";

  const set = (field: keyof ImportMapping, value: string) => {
    onChange(
      { ...analysis.mapping, [field]: value === "" ? null : Number(value) },
      analysis.has_header,
    );
  };

  return (
    <div
      className={`rounded-xl border p-3 text-sm ${
        guessed
          ? "border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-900/20"
          : "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50"
      }`}
    >
      <p
        className={
          guessed
            ? "text-amber-800 dark:text-amber-200"
            : "text-slate-600 dark:text-slate-300"
        }
      >
        {guessed ? t("import.guessedColumns") : t("import.recognisedColumns")}
      </p>

      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        {FIELDS.map((field) => (
          <label key={field} className="block text-xs">
            <span className="text-slate-600 dark:text-slate-300">{t(`import.field.${field}`)}</span>
            <select
              value={analysis.mapping[field] ?? ""}
              onChange={(e) => set(field, e.target.value)}
              disabled={busy}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-900 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            >
              <option value="">{t("import.columnNone")}</option>
              {analysis.columns.map((column) => (
                <option key={column.index} value={column.index}>
                  {column.index + 1}. {describe(column)}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>

      {/* Zonder herkende koptekst wordt regel 1 als goederenregel ingelezen.
          Dat is vaak precies wat er misgaat, en de gebruiker ziet het meteen
          in de voorbeeldwaarden hierboven staan. */}
      <label className="mt-3 flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
        <input
          type="checkbox"
          checked={analysis.has_header}
          disabled={busy}
          onChange={(e) => onChange(analysis.mapping, e.target.checked)}
          className="h-4 w-4 rounded border-slate-300 dark:border-slate-600"
        />
        {t("import.firstRowIsHeader")}
      </label>
    </div>
  );
}
