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

interface Props {
  draftLines: DraftLine[];
  resultLines?: LineItem[];
  onDraftChange: (lines: DraftLine[]) => void;
  onRemoveLine: (id: number) => void;
  onAddLine: () => void;
  onImportClick?: () => void;
  translateMessage: (msg: string) => string;
}

function statusColor(status: string) {
  if (status === "ok") return "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";
  if (status === "error") return "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
  if (status === "needs_review") return "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300";
  return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300";
}

function IconButton({
  label,
  onClick,
  variant,
  disabled,
}: {
  label: string;
  onClick: () => void;
  variant: "add" | "remove";
  disabled?: boolean;
}) {
  const base =
    "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-lg font-medium transition-colors disabled:opacity-40 disabled:pointer-events-none";
  const styles =
    variant === "add"
      ? "border-brand-200 bg-brand-50 text-brand-700 hover:bg-brand-100 dark:border-brand-800 dark:bg-brand-950/40 dark:text-brand-200 dark:hover:bg-brand-900/50"
      : "border-slate-200 bg-white text-slate-500 hover:border-red-200 hover:bg-red-50 hover:text-red-600 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-red-900 dark:hover:bg-red-950/40 dark:hover:text-red-400";

  return (
    <button type="button" onClick={onClick} disabled={disabled} className={`${base} ${styles}`} aria-label={label}>
      {variant === "add" ? "+" : "−"}
    </button>
  );
}

function ImportIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M10 3a.75.75 0 0 1 .75.75v7.19l2.22-2.22a.75.75 0 1 1 1.06 1.06l-3.5 3.5a.75.75 0 0 1-1.06 0l-3.5-3.5a.75.75 0 1 1 1.06-1.06l2.22 2.22V3.75A.75.75 0 0 1 10 3Z" />
      <path d="M4 14.25a.75.75 0 0 0-1.5 0v1A2.75 2.75 0 0 0 5.25 18h9.5A2.75 2.75 0 0 0 17.5 15.25v-1a.75.75 0 0 0-1.5 0v1c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-1Z" />
    </svg>
  );
}

export default function ReviewLinesPanel({
  draftLines,
  resultLines,
  onDraftChange,
  onRemoveLine,
  onAddLine,
  onImportClick,
  translateMessage,
}: Props) {
  const { t } = useTranslation();
  const computed = resultLines && resultLines.length > 0;
  const canRemove = draftLines.length > 1;

  const updateDraft = (id: number, patch: Partial<DraftLine>) => {
    onDraftChange(draftLines.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  return (
    <div className={`${panelClass} overflow-hidden`}>
      <div className="flex flex-col gap-3 border-b border-slate-100 px-4 py-4 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("review.linesTitle")}</h3>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{t("review.intro")}</p>
        </div>
        <div className="flex items-center gap-2 self-end sm:self-auto">
          {onImportClick && (
            <button
              type="button"
              onClick={onImportClick}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-800 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-200 dark:hover:border-brand-700 dark:hover:bg-brand-950/40 dark:hover:text-brand-200"
            >
              <ImportIcon />
              {t("review.importExcel")}
            </button>
          )}
          <IconButton label={t("review.addLine")} onClick={onAddLine} variant="add" />
        </div>
      </div>

      {/* Mobiel: kaarten */}
      <div className="space-y-3 p-4 md:hidden">
        {draftLines.map((draft, index) => {
          const result = computed ? resultLines![index] : null;
          return (
            <div key={draft.id} className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-800 dark:bg-slate-800/30">
              <div className="mb-3 flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-600 shadow-sm dark:bg-slate-900 dark:text-slate-300">
                  {index + 1}
                </span>
                {result && (
                  <span className={`px-2 py-0.5 rounded-full text-xs ${statusColor(result.status)}`}>
                    {t(`status.${result.status}` as "status.ok")}
                  </span>
                )}
                <div className="ml-auto">
                  <IconButton
                    label={t("review.removeLine")}
                    onClick={() => onRemoveLine(draft.id)}
                    variant="remove"
                    disabled={!canRemove}
                  />
                </div>
              </div>
              <div className="space-y-3">
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
                  <div className="grid grid-cols-2 gap-2 border-t border-slate-200 pt-3 text-sm dark:border-slate-700">
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
            </div>
          );
        })}
      </div>

      {/* Desktop: tabel */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[800px] text-sm text-slate-800 dark:text-slate-200">
          <thead className="bg-slate-50/80 dark:bg-slate-800/50">
            <tr>
              <th className="w-12 px-3 py-2.5 text-left">#</th>
              {computed && <th className="px-3 py-2.5 text-left">{t("review.status")}</th>}
              <th className="min-w-[280px] px-3 py-2.5 text-left">{t("review.description")}</th>
              <th className="w-24 px-3 py-2.5 text-left">{t("review.quantity")}</th>
              <th className="w-24 px-3 py-2.5 text-left">{t("review.unit")}</th>
              {computed && (
                <>
                  <th className="px-3 py-2.5 text-left">{t("review.weightEach")}</th>
                  <th className="px-3 py-2.5 text-left">{t("wizard.totalWeight")}</th>
                </>
              )}
              <th className="w-14 px-3 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {draftLines.map((draft, index) => {
              const result = computed ? resultLines![index] : null;
              return (
                <tr key={draft.id} className="border-t border-slate-100 align-top dark:border-slate-800">
                  <td className="px-3 py-3">
                    <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                      {index + 1}
                    </span>
                  </td>
                  {computed && (
                    <td className="px-3 py-3">
                      {result && (
                        <span className={`rounded-full px-2 py-0.5 text-xs ${statusColor(result.status)}`}>
                          {t(`status.${result.status}` as "status.ok")}
                        </span>
                      )}
                    </td>
                  )}
                  <td className="px-3 py-3">
                    <EquipmentCombobox value={draft.description} onChange={(v) => updateDraft(draft.id, { description: v })} />
                    {result && result.messages.length > 0 && (
                      <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">{result.messages.map(translateMessage).join(", ")}</p>
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
                    <IconButton
                      label={t("review.removeLine")}
                      onClick={() => onRemoveLine(draft.id)}
                      variant="remove"
                      disabled={!canRemove}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
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
