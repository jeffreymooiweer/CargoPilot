import { useTranslation } from "react-i18next";
import { LineItem } from "../api/client";
import EquipmentCombobox from "./EquipmentCombobox";

export interface DraftLine {
  id: number;
  description: string;
  quantity: number | "";
  unit: string;
}

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const buttonSecondary = "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 min-h-[44px] text-sm";

interface Props {
  draftLines: DraftLine[];
  resultLines?: LineItem[];
  onDraftChange: (lines: DraftLine[]) => void;
  onRemoveLine: (id: number) => void;
  onAddLine: () => void;
  translateMessage: (msg: string) => string;
}

function statusColor(status: string) {
  if (status === "ok") return "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";
  if (status === "error") return "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
  if (status === "needs_review") return "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300";
  return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300";
}

export default function ReviewLinesPanel({
  draftLines,
  resultLines,
  onDraftChange,
  onRemoveLine,
  onAddLine,
  translateMessage,
}: Props) {
  const { t } = useTranslation();
  const computed = resultLines && resultLines.length > 0;

  const updateDraft = (id: number, patch: Partial<DraftLine>) => {
    onDraftChange(draftLines.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  return (
    <div className="space-y-3">
      {/* Mobiel: kaarten */}
      <div className="md:hidden space-y-3">
        {draftLines.map((draft, index) => {
          const result = computed ? resultLines![index] : null;
          return (
            <div key={draft.id} className={`${panelClass} p-4 space-y-3`}>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">#{index + 1}</span>
                {result && (
                  <span className={`px-2 py-0.5 rounded-full text-xs ${statusColor(result.status)}`}>
                    {t(`status.${result.status}` as "status.ok")}
                  </span>
                )}
                {draftLines.length > 1 && (
                  <button type="button" className="text-xs text-red-600 dark:text-red-400" onClick={() => onRemoveLine(draft.id)}>
                    {t("review.removeLine")}
                  </button>
                )}
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">{t("review.description")}</label>
                <div className="mt-1">
                  <EquipmentCombobox
                    value={draft.description}
                    onChange={(v) => updateDraft(draft.id, { description: v })}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400">{t("review.quantity")}</label>
                  <input
                    type="number"
                    className={`${inputClass} mt-1`}
                    value={draft.quantity}
                    onChange={(e) => updateDraft(draft.id, { quantity: e.target.value === "" ? "" : Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400">{t("review.unit")}</label>
                  <input className={`${inputClass} mt-1`} value={draft.unit} onChange={(e) => updateDraft(draft.id, { unit: e.target.value })} />
                </div>
              </div>
              {result && (
                <div className="grid grid-cols-2 gap-2 text-sm pt-2 border-t border-slate-100 dark:border-slate-800">
                  <div>
                    <span className="text-slate-500 dark:text-slate-400">{t("wizard.totalWeight")}</span>
                    <p className="font-medium">{result.weight_total_kg ?? "—"} kg</p>
                  </div>
                  <div>
                    <span className="text-slate-500 dark:text-slate-400">{t("review.weightEach")}</span>
                    <p className="font-medium">{result.weight_each_kg ?? "—"} kg</p>
                  </div>
                  {result.messages.length > 0 && (
                    <p className="col-span-2 text-xs text-amber-700 dark:text-amber-300">
                      {result.messages.map(translateMessage).join(", ")}
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Desktop: tabel */}
      <div className={`${panelClass} overflow-x-auto hidden md:block`}>
        <table className="w-full text-sm text-slate-800 dark:text-slate-200 min-w-[800px]">
          <thead className="bg-slate-50 dark:bg-slate-800/80">
            <tr>
              <th className="px-3 py-2 text-left w-10">#</th>
              {computed && <th className="px-3 py-2 text-left">{t("review.status")}</th>}
              <th className="px-3 py-2 text-left min-w-[280px]">{t("review.description")}</th>
              <th className="px-3 py-2 text-left w-24">{t("review.quantity")}</th>
              <th className="px-3 py-2 text-left w-24">{t("review.unit")}</th>
              {computed && (
                <>
                  <th className="px-3 py-2 text-left">{t("review.weightEach")}</th>
                  <th className="px-3 py-2 text-left">{t("wizard.totalWeight")}</th>
                </>
              )}
              <th className="px-3 py-2 w-10" />
            </tr>
          </thead>
          <tbody>
            {draftLines.map((draft, index) => {
              const result = computed ? resultLines![index] : null;
              return (
                <tr key={draft.id} className="border-t border-slate-100 dark:border-slate-800 align-top">
                  <td className="px-3 py-3">{index + 1}</td>
                  {computed && (
                    <td className="px-3 py-3">
                      {result && (
                        <span className={`px-2 py-0.5 rounded-full text-xs ${statusColor(result.status)}`}>
                          {t(`status.${result.status}` as "status.ok")}
                        </span>
                      )}
                    </td>
                  )}
                  <td className="px-3 py-3">
                    <EquipmentCombobox value={draft.description} onChange={(v) => updateDraft(draft.id, { description: v })} />
                    {result && result.messages.length > 0 && (
                      <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">{result.messages.map(translateMessage).join(", ")}</p>
                    )}
                  </td>
                  <td className="px-3 py-3">
                    <input
                      type="number"
                      className={inputClass}
                      value={draft.quantity}
                      onChange={(e) => updateDraft(draft.id, { quantity: e.target.value === "" ? "" : Number(e.target.value) })}
                    />
                  </td>
                  <td className="px-3 py-3">
                    <input className={inputClass} value={draft.unit} onChange={(e) => updateDraft(draft.id, { unit: e.target.value })} />
                  </td>
                  {computed && (
                    <>
                      <td className="px-3 py-3">{result?.weight_each_kg ?? "—"}</td>
                      <td className="px-3 py-3">{result?.weight_total_kg ?? "—"}</td>
                    </>
                  )}
                  <td className="px-3 py-3">
                    {draftLines.length > 1 && (
                      <button type="button" className="text-red-600 dark:text-red-400 text-xs" onClick={() => onRemoveLine(draft.id)}>
                        ×
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <button type="button" onClick={onAddLine} className={buttonSecondary}>
        + {t("review.addLine")}
      </button>
    </div>
  );
}

export function draftToText(lines: DraftLine[]): string {
  return lines
    .filter((l) => l.description.trim())
    .map((l) => `${l.description.trim()} | ${l.quantity || 1} | ${l.unit || "stuks"}`)
    .join("\n");
}

export function textToDraftLines(text: string, startId = 1): DraftLine[] {
  const rows = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (rows.length === 0) return [{ id: startId, description: "", quantity: 1, unit: "stuks" }];
  return rows.map((row, i) => {
    const parts = row.split(/[|\t]/).map((p) => p.trim());
    return {
      id: startId + i,
      description: parts[0] || row,
      quantity: parts[1] ? Number(parts[1]) || 1 : 1,
      unit: parts[2] || "stuks",
    };
  });
}
