import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, AppendixFlags, DgInstructions, LineItem } from "../api/client";

const FLAG_KEYS = [
  "loaded",
  "stackable",
  "rotatable",
  "weapons",
  "conditioned",
  "temperature_c",
  "dangerous_goods",
  "ammunition",
  "itar",
  "tbb",
  "tbb_category",
] as const;

const YN_FLAGS = new Set([
  "loaded",
  "stackable",
  "rotatable",
  "weapons",
  "conditioned",
  "dangerous_goods",
  "ammunition",
  "itar",
  "tbb",
]);

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-2 py-1 text-sm";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

interface Props {
  lines: LineItem[];
  onUpdateFlags: (lineId: number, patch: Partial<AppendixFlags>) => void;
}

export default function AppendixFlagsPanel({ lines, onUpdateFlags }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language.startsWith("en") ? "en" : "nl";
  const [instructions, setInstructions] = useState<DgInstructions | null>(null);

  useEffect(() => {
    api.dgInstructions().then(setInstructions).catch(() => setInstructions(null));
  }, []);

  const included = lines.filter((line) => line.include);
  if (included.length === 0) return null;

  const labelFor = (key: string) => t(`flags.${key}` as "flags.loaded");
  const helpFor = (key: string) => instructions?.a1_flags?.[key]?.[lang] || "";

  return (
    <div className={`${panelClass} p-4 space-y-4`}>
      <div>
        <h3 className="font-semibold text-slate-900 dark:text-slate-100">{t("wizard.flagsTitle")}</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t("wizard.flagsIntro")}</p>
      </div>
      {included.map((line) => {
        const flags = line.appendix_flags || {};
        return (
          <div key={line.line_id} className="border-t border-slate-100 dark:border-slate-800 pt-4 space-y-3">
            <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
              #{line.line_id} — {line.output_description || line.description}
              {line.detected_un_numbers && line.detected_un_numbers.length > 0 && (
                <span className="ml-2 text-xs text-amber-700 dark:text-amber-300">
                  UN {line.detected_un_numbers.join(", ")}
                </span>
              )}
            </p>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {FLAG_KEYS.map((key) => {
                if (key === "temperature_c" && flags.conditioned !== "Y") return null;
                if (key === "tbb_category" && flags.tbb !== "Y") return null;
                const help = helpFor(key);
                if (YN_FLAGS.has(key)) {
                  return (
                    <div key={key}>
                      <label className="text-xs font-medium text-slate-700 dark:text-slate-300" title={help}>
                        {labelFor(key)}
                      </label>
                      {help && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">{help}</p>}
                      <select
                        className={`${inputClass} mt-1`}
                        value={flags[key] ?? "N"}
                        onChange={(e) => onUpdateFlags(line.line_id, { [key]: e.target.value })}
                      >
                        <option value="Y">Y</option>
                        <option value="N">N</option>
                      </select>
                    </div>
                  );
                }
                return (
                  <div key={key}>
                    <label className="text-xs font-medium text-slate-700 dark:text-slate-300" title={help}>
                      {labelFor(key)}
                    </label>
                    {help && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">{help}</p>}
                    <input
                      className={`${inputClass} mt-1`}
                      value={flags[key] ?? ""}
                      onChange={(e) => onUpdateFlags(line.line_id, { [key]: e.target.value || null })}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
