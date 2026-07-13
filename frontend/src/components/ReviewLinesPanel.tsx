import { useTranslation } from "react-i18next";
import { LineItem } from "../api/client";
import EquipmentCombobox from "./EquipmentCombobox";

export interface DraftLine {
  id: number;
  description: string;
  quantity: number | "";
  unit: string;
  dangerous_goods?: boolean;
}

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const weightInputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

interface Props {
  draftLines: DraftLine[];
  resultLines?: LineItem[];
  onDraftChange: (lines: DraftLine[]) => void;
  onRemoveLine: (id: number) => void;
  onDuplicateLine: (id: number) => void;
  onAddLine: () => void;
  onImportClick?: () => void;
  onLineWeightChange?: (lineId: number, field: "weight_each_kg" | "weight_total_kg", value: number | null) => void;
  translateMessage: (msg: string) => string;
}

function statusColor(status: string) {
  if (status === "ok") return "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";
  if (status === "error") return "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
  if (status === "needs_review") return "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300";
  return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300";
}

function ImportIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M10 3a.75.75 0 0 1 .75.75v7.19l2.22-2.22a.75.75 0 1 1 1.06 1.06l-3.5 3.5a.75.75 0 0 1-1.06 0l-3.5-3.5a.75.75 0 1 1 1.06-1.06l2.22 2.22V3.75A.75.75 0 0 1 10 3Z" />
      <path d="M4 14.25a.75.75 0 0 0-1.5 0v1A2.75 2.75 0 0 0 5.25 18h9.5A2.75 2.75 0 0 0 17.5 15.25v-1a.75.75 0 0 0-1.5 0v1c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-1Z" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
      <path d="M10 4v12M4 10h12" strokeLinecap="round" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} aria-hidden>
      <rect x="7" y="7" width="9" height="9" rx="2" />
      <path d="M13 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} aria-hidden>
      <path d="M4 6h12M8 6V4.5A1.5 1.5 0 0 1 9.5 3h1A1.5 1.5 0 0 1 12 4.5V6m-6 0v9a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CardAction({
  label,
  onClick,
  icon,
  danger,
  disabled,
}: {
  label: string;
  onClick: () => void;
  icon: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
}) {
  const tone = danger
    ? "text-slate-500 hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-950/40 dark:hover:text-red-400"
    : "text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors disabled:opacity-40 disabled:pointer-events-none ${tone}`}
    >
      {icon}
    </button>
  );
}

export default function ReviewLinesPanel({
  draftLines,
  resultLines,
  onDraftChange,
  onRemoveLine,
  onDuplicateLine,
  onAddLine,
  onImportClick,
  onLineWeightChange,
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
        {onImportClick && (
          <div className="flex items-center gap-1 self-end sm:self-auto">
            <CardAction label={t("review.importExcel")} onClick={onImportClick} icon={<ImportIcon />} />
          </div>
        )}
      </div>

      <div className="space-y-3 p-4">
        {draftLines.map((draft, index) => {
          const result = computed ? resultLines![index] : null;
          return (
            <div key={draft.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="-mx-4 -mt-4 mb-3 flex items-center gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {index + 1}
                </span>
                {result && (
                  <span className={`px-2 py-0.5 rounded-full text-xs ${statusColor(result.status)}`}>
                    {t(`status.${result.status}` as "status.ok")}
                  </span>
                )}
                <div className="ml-auto flex items-center gap-0.5">
                  <CardAction label={t("review.duplicateLine")} onClick={() => onDuplicateLine(draft.id)} icon={<CopyIcon />} />
                  <CardAction label={t("review.addLine")} onClick={onAddLine} icon={<PlusIcon />} />
                  <CardAction
                    label={t("review.removeLine")}
                    onClick={() => onRemoveLine(draft.id)}
                    icon={<TrashIcon />}
                    danger
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
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
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
                  {result && onLineWeightChange && (
                    <>
                      <div>
                        <label className="text-xs font-medium text-slate-600 dark:text-slate-400">{t("review.weightEach")}</label>
                        <input
                          type="number"
                          step="0.01"
                          className={`${weightInputClass} mt-1`}
                          value={result.weight_each_kg ?? ""}
                          onChange={(e) =>
                            onLineWeightChange(
                              result.line_id,
                              "weight_each_kg",
                              e.target.value === "" ? null : Number(e.target.value),
                            )
                          }
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-slate-600 dark:text-slate-400">{t("review.weightTotal")}</label>
                        <input
                          type="number"
                          step="0.01"
                          className={`${weightInputClass} mt-1`}
                          value={result.weight_total_kg ?? ""}
                          onChange={(e) =>
                            onLineWeightChange(
                              result.line_id,
                              "weight_total_kg",
                              e.target.value === "" ? null : Number(e.target.value),
                            )
                          }
                        />
                      </div>
                    </>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <label className="flex min-h-[32px] cursor-pointer items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={draft.dangerous_goods ?? false}
                      onChange={(e) => updateDraft(draft.id, { dangerous_goods: e.target.checked })}
                      className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                    />
                    {t("review.dangerousGoods")}
                  </label>
                  {result?.dangerous_goods && !draft.dangerous_goods && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                      {t("review.dgDetected")}
                    </span>
                  )}
                </div>
                {result && result.messages.length > 0 && (
                  <p className="text-xs text-amber-700 dark:text-amber-300">
                    {result.messages.map(translateMessage).join(", ")}
                  </p>
                )}
              </div>
            </div>
          );
        })}
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
