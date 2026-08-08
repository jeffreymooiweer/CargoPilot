import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { LineItem, UnitCatalogue, api } from "../api/client";
import EquipmentCombobox from "./EquipmentCombobox";
import ResponsiveRecords, { QuantityWithUnit, RecordColumn } from "./ResponsiveRecords";
import UnitSelect from "./UnitSelect";

export interface DraftLine {
  id: number;
  description: string;
  quantity: number | "";
  unit: string;
  /** De vorm waarin dit goed reist: massief, gestapeld, los gestort. Bepaalt
   *  hoeveel van een kuub daadwerkelijk materiaal is. */
  cargo_form?: string;
  /** Wanddikte in millimeters. Alleen zinvol bij een doorsnede die een wand
   *  heeft — een hoekprofiel of koker. Bij een plaat of balk beschrijven de drie
   *  buitenmaten het materiaal al volledig. */
  wall_thickness_mm?: number | "";
  /** Afmetingen die de gebruiker zelf invult, in centimeters. Ze hoeven dus
   *  niet meer in de omschrijving te worden verstopt om mee te tellen. */
  length_cm?: number | "";
  width_cm?: number | "";
  height_cm?: number | "";
  dangerous_goods?: boolean;
}

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const weightInputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

/**
 * Doorsneden met een wand, waar lengte-breedte-hoogte het gewicht niet bepaalt.
 *
 * Een hoekprofiel van 80x80 is twee benen van een paar millimeter dik, geen
 * massieve staaf van 80x80 — het scheelt een factor vijf. Bij een plaat, balk of
 * plank speelt dat niet en hoort het veld er dus ook niet te staan.
 */
const WALL_PROFILE_TYPES = new Set(["angle_profile", "square_tube", "round_tube"]);

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

  // De eenhedencatalogus komt van de backend, zodat de lijst op één plek wordt
  // onderhouden. Lukt dat niet, dan valt UnitSelect terug op een tekstveld en
  // blijft de stap bruikbaar.
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

  // Kolommen zijn hier ook invoervelden: dit is een tabel waarin je typt, niet
  // een tabel die je leest. Wat op een dichtgeklapte kaart hoort staat in het
  // antwoord van de gebruiker: de omschrijving als kop, aantal en eenheid als
  // enige regel. De rest zit achter "toon meer".
  const columns: RecordColumn<DraftLine>[] = [
    {
      key: "description",
      header: t("review.description"),
      width: "w-[28%]",
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
      render: (draft, index) => (
        <div className="flex items-center justify-end gap-1.5">
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
      render: (draft, index) => {
        const category = resultFor(index)?.material_category;
        const forms = (category && catalogue?.forms_by_category[category]) || [];
        // Geen vorm bij grind, graan of vloeistoffen: daar beschrijft de
        // opgeslagen dichtheid de stof al zoals hij vervoerd wordt.
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
      header: t(`review.${field}`),
      numeric: true,
      width: "w-24",
      render: (draft: DraftLine, index: number) => {
        // Wat de gebruiker invult wint van wat er uit de omschrijving is
        // gelezen; staat er niets, dan is de gelezen maat de standaardwaarde.
        const parsed = resultFor(index)?.[field];
        return (
          <input
            type="number"
            step="0.1"
            inputMode="decimal"
            aria-label={t(`review.${field}`)}
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
      header: t("review.wallThickness"),
      numeric: true,
      width: "w-28",
      render: (draft, index) => {
        // Alleen tonen waar het iets betekent. Een plaat of een balk heeft geen
        // wand, en een leeg veld dat nooit van toepassing is leidt alleen maar af.
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
      header: t("review.dangerousGoods"),
      width: "w-32",
      render: (draft, index) => {
        const result = resultFor(index);
        return (
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
          </div>
        );
      },
    },
    {
      key: "status",
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
