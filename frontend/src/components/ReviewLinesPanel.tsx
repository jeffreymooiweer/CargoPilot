import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { DgNameCandidate, LineItem, UnitCatalogue, api } from "../api/client";
import EquipmentCombobox from "./EquipmentCombobox";
import ResponsiveRecords, { QuantityWithUnit, RecordColumn } from "./ResponsiveRecords";
import UnitSelect from "./UnitSelect";

export interface DraftLine {
  id: number;
  description: string;
  quantity: number | "";
  unit: string;
  /** The form this commodity travels in: solid, stacked, loose bulk. Determines
   *  how much of a cubic metre is actually material. */
  cargo_form?: string;
  /** Wall thickness in millimetres. Only meaningful with a cross-section that
   *  has a wall — an angle or a hollow section. For a plate or a beam the three
   *  outside measurements already describe the material completely. */
  wall_thickness_mm?: number | "";
  /** Dimensions the user fills in themselves, in centimetres. They no longer
   *  have to be hidden in the description to count. */
  length_cm?: number | "";
  width_cm?: number | "";
  height_cm?: number | "";
  dangerous_goods?: boolean;
  /** UN number the user confirmed from a name suggestion. Carries through to
   *  the DG step so nothing recognised has to be typed again. */
  confirmed_un?: string;
  /** The suggestion was rejected for this line; it must not come back. */
  dg_dismissed?: boolean;
  /** Net content of one package as the description said it ("25 L"); the DG
   *  derivation fills the per-package quantity from it. */
  package_content?: string;
}

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const weightInputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

/**
 * Cross-sections with a wall, where length-width-height does not determine the weight.
 *
 * An 80x80 angle is two legs a few millimetres thick, not a solid bar of 80x80 —
 * a factor of five. For a plate, beam or plank that does not come into play and
 * the field therefore should not be there either.
 */
const WALL_PROFILE_TYPES = new Set(["angle_profile", "square_tube", "round_tube"]);

/**
 * Round cross-sections. There the width *is* the diameter and there is no
 * height: with a diameter, a length and — for a tube — a wall thickness, the
 * weight is fixed. Asking for a height that adds nothing is only an opportunity
 * to fill in something wrong.
 */
const ROUND_TYPES = new Set(["round_tube", "round_bar"]);

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

/** A substance recognised by name, offered for confirmation.
 *
 *  The recognition is a suggestion and looks like one: it names the UN number,
 *  the shipping name and the class, and it asks. One candidate gets a yes/no;
 *  several (two sulphuric acids, differing in the qualifier) get a button per
 *  UN number. Rejecting it puts it away for this line — a suggestion that
 *  keeps coming back is nagging, not helping. */
function DgSuggestion({
  candidates,
  onConfirm,
  onDismiss,
}: {
  candidates: DgNameCandidate[];
  onConfirm: (un: string) => void;
  onDismiss: () => void;
}) {
  const { t } = useTranslation();
  const chipButton =
    "rounded-md border border-amber-300 bg-white px-2 py-0.5 text-[11px] font-medium text-amber-900 hover:bg-amber-100 dark:border-amber-700 dark:bg-slate-900 dark:text-amber-200 dark:hover:bg-amber-900/40";
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-2 py-1.5 text-[11px] text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-200">
      {candidates.length === 1 ? (
        <>
          <p className="truncate" title={candidates[0].name}>
            {t("review.dgSuggestedOne", {
              un: candidates[0].un,
              class: candidates[0].class,
            })}{" "}
            <span className="font-medium">{candidates[0].name}</span>
          </p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            <button type="button" className={chipButton} onClick={() => onConfirm(candidates[0].un)}>
              {t("review.dgApply")}
            </button>
            <button type="button" className={chipButton} onClick={onDismiss}>
              {t("review.dgDismiss")}
            </button>
          </div>
        </>
      ) : (
        <>
          <p>{t("review.dgSuggestedMany")}</p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {candidates.slice(0, 3).map((candidate) => (
              <button
                key={candidate.un}
                type="button"
                className={chipButton}
                title={candidate.name}
                onClick={() => onConfirm(candidate.un)}
              >
                UN {candidate.un}
              </button>
            ))}
            <button type="button" className={chipButton} onClick={onDismiss}>
              {t("review.dgDismiss")}
            </button>
          </div>
        </>
      )}
    </div>
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

  // The unit catalogue comes from the backend, so the list is maintained in one
  // place. If that fails, UnitSelect falls back to a text field and the step
  // stays usable.
  const [catalogue, setCatalogue] = useState<UnitCatalogue | null>(null);
  useEffect(() => {
    let alive = true;
    api.unitCatalogue()
      .then((result) => alive && setCatalogue(result))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);

  const numberInput = `${weightInputClass} text-right`;

  function resultFor(index: number): LineItem | null {
    return computed ? resultLines![index] : null;
  }

  // Columns are input fields here as well: this is a table you type in, not a
  // table you read. What belongs on a collapsed card is in the user's answer:
  // the description as the heading, quantity and unit as the only line. The rest
  // sits behind "show more".
  const columns: RecordColumn<DraftLine>[] = [
    {
      key: "description",
      header: t("review.description"),
      width: "w-[28%]",
      // What the line *is*. Without it the table says nothing, so it is never
      // the column that falls away.
      priority: 0,
      minPx: 240,
      render: (draft) => (
        <EquipmentCombobox
          value={draft.description}
          onChange={(v) => updateDraft(draft.id, { description: v })}
        />
      ),
    },
    {
      key: "quantity",
      header: t("review.quantity"),
      cardLabel: t("review.quantityAndUnit"),
      primary: true,
      numeric: true,
      width: "w-40",
      priority: 1,
      minPx: 220,
      render: (draft, index) => (
        // Two controls in one cell, and the cell has to reserve room for both.
        // Without the floor the table's auto layout sized this column on the
        // *text* in it — nothing, since both are inputs — and handed the number
        // field 30px and the unit select 28px, which is a field you cannot type
        // in. Note that the `w-20` and `w-24` below do nothing: weightInputClass
        // already carries `w-full`, and that wins whatever order they are
        // written in. The width is the cell's to give.
        <div className="flex min-w-[13rem] items-center justify-end gap-1.5">
          <input
            type="number"
            inputMode="decimal"
            aria-label={t("review.quantity")}
            className={`${numberInput} w-20`}
            value={draft.quantity}
            onChange={(e) =>
              updateDraft(draft.id, { quantity: e.target.value === "" ? "" : Number(e.target.value) })
            }
          />
          <UnitSelect
            value={draft.unit}
            onChange={(unit) => updateDraft(draft.id, { unit })}
            category={resultFor(index)?.material_category}
            catalogue={catalogue}
            aria-label={t("review.unit")}
            className={`${weightInputClass} w-24`}
          />
        </div>
      ),
    },
    {
      key: "cargoForm",
      header: t("review.cargoForm"),
      width: "w-40",
      // Only offered for goods whose stored density describes the material
      // itself, so on many lines it is a dash. Late.
      priority: 9,
      minPx: 130,
      render: (draft, index) => {
        const category = resultFor(index)?.material_category;
        const forms = (category && catalogue?.forms_by_category[category]) || [];
        // No form for gravel, grain or liquids: there the stored density already
        // describes the substance as it is carried.
        if (forms.length === 0) return <span className="text-slate-400">—</span>;
        return (
          <select
            aria-label={t("review.cargoForm")}
            className={`${weightInputClass} w-36`}
            value={draft.cargo_form ?? resultFor(index)?.cargo_form ?? ""}
            onChange={(e) => updateDraft(draft.id, { cargo_form: e.target.value })}
          >
            {forms.map((form) => (
              <option key={form} value={form}>
                {t(`forms.${form}`, form)}
              </option>
            ))}
          </select>
        );
      },
    },
    ...(["length_cm", "width_cm", "height_cm"] as const).map((field) => ({
      key: field,
      // One measurement in three cells: they come and go together.
      group: "dimensions",
      priority: 5,
      minPx: 82,
      header: t(`review.${field}`),
      numeric: true,
      width: "w-24",
      render: (draft: DraftLine, index: number) => {
        const round = ROUND_TYPES.has(resultFor(index)?.product_type ?? "");
        // No height with a round cross-section; the diameter is in the width.
        if (round && field === "height_cm") return <span className="text-slate-400">—</span>;
        // The column heading is the same for every line, so the label "diameter"
        // belongs with the field itself.
        const label = round && field === "width_cm" ? t("review.diameter") : t(`review.${field}`);
        // What the user fills in beats what was read out of the description; if
        // there is nothing, the measurement read is the default value.
        const parsed = resultFor(index)?.[field];
        return (
          <input
            type="number"
            step="0.1"
            inputMode="decimal"
            aria-label={label}
            title={label}
            placeholder={parsed != null ? String(parsed) : ""}
            className={`${numberInput} w-20`}
            value={draft[field] ?? ""}
            onChange={(e) =>
              updateDraft(draft.id, { [field]: e.target.value === "" ? "" : Number(e.target.value) })
            }
          />
        );
      },
    })),
    {
      key: "wall_thickness_mm",
      // Only meaningful for hollow profiles. Last.
      priority: 11,
      minPx: 100,
      header: t("review.wallThickness"),
      numeric: true,
      width: "w-28",
      render: (draft, index) => {
        // Only show it where it means something. A plate or a beam has no wall,
        // and an empty field that never applies is only a distraction.
        const type = resultFor(index)?.product_type;
        if (!type || !WALL_PROFILE_TYPES.has(type)) {
          return <span className="text-slate-400">—</span>;
        }
        const missing = resultFor(index)?.messages.includes("wall_thickness_missing");
        return (
          <input
            type="number"
            step="0.1"
            inputMode="decimal"
            aria-label={t("review.wallThickness")}
            className={`${numberInput} w-20 ${
              missing ? "border-amber-400 dark:border-amber-600" : ""
            }`}
            value={draft.wall_thickness_mm ?? ""}
            onChange={(e) =>
              updateDraft(draft.id, {
                wall_thickness_mm: e.target.value === "" ? "" : Number(e.target.value),
              })
            }
          />
        );
      },
    },
    {
      key: "weightEach",
      priority: 8,
      minPx: 110,
      header: t("review.weightEach"),
      numeric: true,
      width: "w-28",
      render: (_draft, index) => {
        const result = resultFor(index);
        if (!result || !onLineWeightChange) return <span className="text-slate-400">—</span>;
        return (
          <input
            type="number"
            step="0.01"
            aria-label={t("review.weightEach")}
            className={`${numberInput} w-24`}
            value={result.weight_each_kg ?? ""}
            onChange={(e) =>
              onLineWeightChange(result.line_id, "weight_each_kg", e.target.value === "" ? null : Number(e.target.value))
            }
          />
        );
      },
    },
    {
      key: "weightTotal",
      // The figure the whole step is for.
      priority: 2,
      minPx: 115,
      header: t("review.weightTotal"),
      numeric: true,
      width: "w-28",
      render: (_draft, index) => {
        const result = resultFor(index);
        if (!result || !onLineWeightChange) return <span className="text-slate-400">—</span>;
        return (
          <input
            type="number"
            step="0.01"
            aria-label={t("review.weightTotal")}
            className={`${numberInput} w-24`}
            value={result.weight_total_kg ?? ""}
            onChange={(e) =>
              onLineWeightChange(result.line_id, "weight_total_kg", e.target.value === "" ? null : Number(e.target.value))
            }
          />
        );
      },
    },
    {
      key: "volume",
      priority: 10,
      minPx: 95,
      header: t("review.volume"),
      numeric: true,
      width: "w-24",
      render: (_draft, index) => {
        const volume = resultFor(index)?.transport_volume_m3;
        return volume != null ? (
          <QuantityWithUnit value={volume.toFixed(3)} unit="m³" />
        ) : (
          <span className="text-slate-400">—</span>
        );
      },
    },
    {
      key: "dg",
      // A tick that changes the rest of the wizard; worth keeping in view.
      priority: 4,
      minPx: 120,
      header: t("review.dangerousGoods"),
      width: "w-32",
      render: (draft, index) => {
        const result = resultFor(index);
        const candidates = result?.dg_name_candidates ?? [];
        const showSuggestion =
          candidates.length > 0 && !draft.confirmed_un && !draft.dg_dismissed;
        return (
          <div className="space-y-1.5">
            <div className="flex items-center justify-end gap-2 md:justify-start">
              <input
                type="checkbox"
                aria-label={t("review.dangerousGoods")}
                checked={draft.dangerous_goods ?? false}
                onChange={(e) => updateDraft(draft.id, { dangerous_goods: e.target.checked })}
                className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
              />
              {result?.dangerous_goods && !draft.dangerous_goods && (
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                  {t("review.dgDetected")}
                </span>
              )}
              {draft.confirmed_un && (
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                  UN {draft.confirmed_un}
                </span>
              )}
            </div>
            {showSuggestion && (
              <DgSuggestion
                candidates={candidates}
                onConfirm={(un) =>
                  updateDraft(draft.id, { dangerous_goods: true, confirmed_un: un })
                }
                onDismiss={() => updateDraft(draft.id, { dg_dismissed: true })}
              />
            )}
          </div>
        );
      },
    },
    {
      key: "status",
      // Says whether the line is usable at all.
      priority: 3,
      minPx: 130,
      header: t("review.status"),
      width: "w-36",
      render: (_draft, index) => {
        const result = resultFor(index);
        if (!result) return <span className="text-slate-400">—</span>;
        return (
          <div className="space-y-1">
            <span className={`inline-block rounded-full px-2 py-0.5 text-xs ${statusColor(result.status)}`}>
              {t(`status.${result.status}` as "status.ok")}
            </span>
            {result.messages.length > 0 && (
              <p className="text-xs text-amber-700 dark:text-amber-300">
                {result.messages.map(translateMessage).join(", ")}
              </p>
            )}
          </div>
        );
      },
    },
  ];

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

      <div className="p-4">
        <ResponsiveRecords
          rows={draftLines}
          columns={columns}
          // Since v1.55.0 the table drops what does not fit instead of
          // scrolling: the columns are ranked, the ones that fall off are in
          // the detail panel, and the fields keep their width. The floor stays
          // as the last line of defence for the case where even the columns
          // that *are* shown do not fit — a very narrow window with the side
          // menu folded open.
          minWidth="min-w-[720px]"
          fit
          detail
          rowKey={(draft) => draft.id}
          cardTitle={(draft, index) => (
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-600 dark:bg-slate-900 dark:text-slate-300">
                {index + 1}
              </span>
              <span className="min-w-0 flex-1 truncate">
                {draft.description.trim() || t("review.untitledLine")}
              </span>
            </div>
          )}
          actions={(draft) => (
            <>
              <CardAction label={t("review.duplicateLine")} onClick={() => onDuplicateLine(draft.id)} icon={<CopyIcon />} />
              <CardAction
                label={t("review.removeLine")}
                onClick={() => onRemoveLine(draft.id)}
                icon={<TrashIcon />}
                danger
                disabled={!canRemove}
              />
            </>
          )}
          footer={
            <button
              type="button"
              onClick={onAddLine}
              className="mt-3 flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 text-sm font-medium text-slate-600 dark:border-slate-700 dark:text-slate-300"
            >
              <PlusIcon />
              {t("review.addLine")}
            </button>
          }
        />
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
