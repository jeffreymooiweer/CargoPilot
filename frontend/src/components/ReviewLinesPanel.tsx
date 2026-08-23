import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { LineItem, UnitCatalogue, api } from "../api/client";
import { useToast } from "../toast/ToastProvider";
import LineEditDialog, { ROUND_TYPES, WALL_PROFILE_TYPES } from "./LineEditDialog";
import RecordCards, { NoValue, QuantityWithUnit, RecordField } from "./RecordCards";
import { ImportIcon } from "./icons";

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
  /** Weight of one item or package the consignor stated themselves, for goods
   *  the catalogue cannot weigh. Never a computed value. */
  weight_each_kg?: number | "";
}

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

function PlusIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
      <path d="M10 4v12M4 10h12" strokeLinecap="round" />
    </svg>
  );
}

function PencilIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} aria-hidden>
      <path d="M13.5 3.5a1.77 1.77 0 0 1 2.5 2.5L7 15l-3.5 1L4.5 12.5Z" strokeLinecap="round" strokeLinejoin="round" />
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
  const toast = useToast();
  const computed = resultLines && resultLines.length > 0;
  const canRemove = draftLines.length > 1;

  // Held by id rather than by index: a line can be removed or duplicated while
  // the dialog is open, and an index would then quietly point at another line.
  const [editingId, setEditingId] = useState<number | null>(null);

  const updateDraft = (id: number, patch: Partial<DraftLine>) => {
    onDraftChange(draftLines.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  // A toast button is pressed long after the render that created it, so it
  // must not patch the lines as they were then. This ref is what "the lines"
  // means at the moment the user answers.
  const latest = useRef({ draftLines, onDraftChange });
  latest.current = { draftLines, onDraftChange };

  const patchLine = (id: number, patch: Partial<DraftLine>) => {
    const { draftLines: lines, onDraftChange: change } = latest.current;
    change(lines.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  /**
   * The name recognition, asked as a snackbar rather than shown on the card.
   *
   * It is the one thing on a line that asks the user a *question* — "this
   * looks like UN 1203, shall I take it?" — and a question belongs in the one
   * place the application asks things. It is a `question` toast, so it never
   * dismisses itself: four seconds is not an answer. Closing it with the × is
   * an answer, and a final one — the same "no, not this line" the reject chip
   * used to mean.
   *
   * Offered once per recognition, keyed by line *and* candidates: re-running
   * the calculation must not ask again, but changing the description into a
   * different substance is a new question and gets asked.
   *
   * The set only remembers questions that are still open, and is pruned to
   * those on every run. Remembering them forever looked equivalent and was
   * not: an import that replaces the lines starts numbering at 1 again, so
   * line 1 with the same substance produced the same key as the line the user
   * had already answered — and the new consignment's first line was never
   * asked about at all. What marks a line as answered is the answer on the
   * line itself; this set exists only to stop a second toast while one is
   * still standing.
   */
  const offered = useRef(new Set<string>());
  useEffect(() => {
    if (!resultLines) return;
    const open = new Set<string>();
    draftLines.forEach((draft, index) => {
      const candidates = resultLines[index]?.dg_name_candidates ?? [];
      if (candidates.length === 0 || draft.confirmed_un || draft.dg_dismissed) return;
      const key = `${draft.id}:${candidates.map((one) => one.un).join(",")}`;
      open.add(key);
      if (offered.current.has(key)) return;
      offered.current.add(key);

      // Accepting and rejecting are the same slot: whichever comes first is
      // the answer, and closing the toast afterwards must not overrule it.
      let answered = false;
      const once = (fn: () => void) => () => {
        if (answered) return;
        answered = true;
        fn();
      };
      const single = candidates.length === 1;
      const id: number = toast.ask(
        single
          ? t("review.dgToastOne", {
              number: index + 1,
              un: candidates[0].un,
              class: candidates[0].class,
              name: candidates[0].name,
            })
          : t("review.dgToastMany", { number: index + 1 }),
        {
          actions: (single ? candidates : candidates.slice(0, 3)).map((candidate) => ({
            label: single ? t("review.dgApply") : `UN ${candidate.un}`,
            run: once(() => {
              patchLine(draft.id, { dangerous_goods: true, confirmed_un: candidate.un });
              toast.dismiss(id);
            }),
          })),
          onDismiss: once(() => patchLine(draft.id, { dg_dismissed: true })),
        },
      );
    });
    offered.current = open;
    // patchLine and toast are stable enough to leave out: what decides whether
    // to ask is the lines and their recognition, and the guard above makes a
    // repeat run harmless.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftLines, resultLines, t]);

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

  function resultFor(index: number): LineItem | null {
    return computed ? resultLines![index] : null;
  }

  /** What the user filled in beats what was read out of the description. */
  function measure(draft: DraftLine, result: LineItem | null, field: "length_cm" | "width_cm" | "height_cm") {
    const own = draft[field];
    if (own !== undefined && own !== "") return own;
    return result?.[field] ?? null;
  }

  // Read-only, all of them: the card says what the line holds and the dialog is
  // where it changes. That is what lets one shape work at every width — text
  // reflows, a row of input fields does not.
  const fields: RecordField<DraftLine>[] = [
    {
      key: "quantity",
      label: t("review.quantityAndUnit"),
      primary: true,
      render: (draft) =>
        draft.quantity === "" ? <NoValue /> : <QuantityWithUnit value={draft.quantity} unit={draft.unit} />,
    },
    {
      key: "weightTotal",
      label: t("review.weightTotal"),
      primary: true,
      render: (_draft, index) => {
        const weight = resultFor(index)?.weight_total_kg;
        return weight != null ? <QuantityWithUnit value={weight} unit="kg" /> : <NoValue />;
      },
    },
    {
      key: "status",
      label: t("review.status"),
      primary: true,
      render: (_draft, index) => {
        const result = resultFor(index);
        if (!result) return <NoValue />;
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
    {
      key: "dangerousGoods",
      label: t("review.dangerousGoods"),
      render: (draft, index) => {
        const result = resultFor(index);
        return (
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            <span>{draft.dangerous_goods ? t("review.dgYes") : t("review.dgNo")}</span>
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
        );
      },
    },
    {
      key: "dimensions",
      // One measurement, one line: three cells for length, width and height was
      // a table's way of putting it, not a reader's.
      label: t("review.dimensions"),
      render: (draft, index) => {
        const result = resultFor(index);
        const round = ROUND_TYPES.has(result?.product_type ?? "");
        const length = measure(draft, result, "length_cm");
        const width = measure(draft, result, "width_cm");
        const height = round ? null : measure(draft, result, "height_cm");
        if (length == null && width == null && height == null) return <NoValue />;
        const show = (value: number | null) => (value == null ? "?" : String(value));
        const text = round
          ? `${show(length)} × ⌀ ${show(width)}`
          : [length, width, height].map(show).join(" × ");
        return <QuantityWithUnit value={text} unit="cm" />;
      },
    },
    {
      key: "weightEach",
      label: t("review.weightEach"),
      render: (_draft, index) => {
        const weight = resultFor(index)?.weight_each_kg;
        return weight != null ? <QuantityWithUnit value={weight} unit="kg" /> : <NoValue />;
      },
    },
    {
      key: "volume",
      label: t("review.volume"),
      render: (_draft, index) => {
        const volume = resultFor(index)?.transport_volume_m3;
        return volume != null ? <QuantityWithUnit value={volume.toFixed(3)} unit="m³" /> : <NoValue />;
      },
    },
    {
      key: "cargoForm",
      label: t("review.cargoForm"),
      render: (draft, index) => {
        const result = resultFor(index);
        const form = draft.cargo_form ?? result?.cargo_form;
        // No form for gravel, grain or liquids: there the stored density
        // already describes the substance as it is carried.
        if (!form) return <NoValue />;
        return <>{t(`forms.${form}`, form)}</>;
      },
    },
    {
      key: "wallThickness",
      label: t("review.wallThickness"),
      render: (draft, index) => {
        const result = resultFor(index);
        const type = result?.product_type;
        // Only where it means something: a plate or a beam has no wall.
        if (!type || !WALL_PROFILE_TYPES.has(type)) return <NoValue />;
        const value = draft.wall_thickness_mm;
        if (value === undefined || value === "") {
          return result.messages.includes("wall_thickness_missing") ? (
            <span className="text-amber-700 dark:text-amber-300">{translateMessage("wall_thickness_missing")}</span>
          ) : (
            <NoValue />
          );
        }
        return <QuantityWithUnit value={value} unit="mm" />;
      },
    },
  ];

  const editingIndex = draftLines.findIndex((line) => line.id === editingId);
  const editing = editingIndex >= 0 ? draftLines[editingIndex] : null;

  return (
    <div className={`${panelClass} overflow-hidden`}>
      {/* The action sits on the heading's own line, at every width. It used to
          drop below the text on a phone — a column layout with the button
          pushed to the right — which cost a whole empty band of screen above
          the first line, on the screen where space is scarcest. And it carries
          its name rather than only an icon: the sentence underneath points at
          it by that name, and a phone has no hover to reveal a title. */}
      <div className="border-b border-slate-100 px-4 py-4 dark:border-slate-800 sm:px-5">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("review.linesTitle")}</h3>
          {onImportClick && (
            <button
              type="button"
              onClick={onImportClick}
              className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <ImportIcon />
              {t("review.importExcel")}
            </button>
          )}
        </div>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t("review.intro")}</p>
      </div>

      <div className="p-4">
        <RecordCards
          rows={draftLines}
          fields={fields}
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
              <CardAction label={t("review.editLine")} onClick={() => setEditingId(draft.id)} icon={<PencilIcon />} />
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

      {editing && (
        <LineEditDialog
          line={editing}
          result={resultFor(editingIndex)}
          position={editingIndex + 1}
          catalogue={catalogue}
          onChange={(patch) => updateDraft(editing.id, patch)}
          onWeightChange={
            onLineWeightChange && resultFor(editingIndex)
              ? (field, value) => onLineWeightChange(resultFor(editingIndex)!.line_id, field, value)
              : undefined
          }
          onClose={() => setEditingId(null)}
        />
      )}
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
