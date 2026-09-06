/**
 * The goods step: one compact line per goods line, edited where it stands.
 *
 * Until v1.192.0 every line was a read-only card and everything changeable
 * lived behind an edit icon, in a dialog. That shape was the right answer to
 * the wrong question. It replaced a table of thirteen input fields — which
 * genuinely did not fit any screen — but it charged three actions and a window
 * for changing a number: the baseline measured five quantity corrections at
 * fifteen actions and five dialogs, none of which was the number itself.
 *
 * What is here now is the middle the two shapes missed. Four things live on the
 * line, because they are what a consignment is made of and what people come
 * back to change: the description, the quantity, the unit, and — read-only —
 * what CargoPilot worked out from them. The thirteen fields are not back:
 * dimensions, wall thickness, cargo form, own weights and the article stay in
 * the detail dialog, one click away, exactly as they were.
 *
 * The row wraps rather than switching layouts. On a phone the description takes
 * the width and the quantity, the unit and the outcome fall underneath it; on a
 * laptop it is one line. One implementation, so the validation, the focus order
 * and the keyboard are the same everywhere — a second layout is a second set of
 * bugs.
 *
 * **Getting a list in.** Pasting from Excel and choosing a file are actions on
 * this panel rather than a dialog to find, and the panel takes a dropped file —
 * see ``GoodsImport``. What came out is said above the list: how many lines are
 * settled, how many want looking at, and a filter that narrows to those. Fifty
 * imported lines with one that needs attention used to be fifty cards of
 * scrolling with nothing pointing at it.
 *
 * **Derived figures while the calculation runs.** Typing clears the result, and
 * the wizard recalculates six-tenths of a second after the typing stops. A line
 * whose own text has not changed keeps showing what was worked out for it,
 * dimmed and marked *to be rechecked*; the line being edited shows no figures at
 * all, because a weight that belongs to the previous description is not a
 * weight. Nothing on this screen shows a number for input it was not computed
 * from.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { LineItem, UnitCatalogue, api, ArticleRef } from "../api/client";
import { useToast } from "../toast/ToastProvider";
import EquipmentCombobox from "./EquipmentCombobox";
import GoodsImport from "./GoodsImport";
import LineEditDialog, { ROUND_TYPES, WALL_PROFILE_TYPES } from "./LineEditDialog";
import NumberInput from "./NumberInput";
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
  /** The library article this line was picked from, if any. Its UN number
   *  travels as `confirmed_un`; the rest seeds the DG product. */
  article?: ArticleRef;
  /** Weight of one item or package the consignor stated themselves, for goods
   *  the catalogue cannot weigh. Never a computed value. */
  weight_each_kg?: number | "";
}

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const fieldClass =
  "border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 " +
  "dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const labelClass = "text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400";

interface Props {
  draftLines: DraftLine[];
  resultLines?: LineItem[];
  onDraftChange: (lines: DraftLine[]) => void;
  onRemoveLine: (id: number) => void;
  onDuplicateLine: (id: number) => void;
  onAddLine: () => void;
  onImport?: (text: string, mode: "append" | "replace") => void;
  onLineWeightChange?: (lineId: number, field: "weight_each_kg" | "weight_total_kg", value: number | null) => void;
  translateMessage: (msg: string) => string;
}

function statusColor(status: string) {
  if (status === "ok") return "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";
  if (status === "error") return "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
  if (status === "needs_review") return "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300";
  return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300";
}

/** A line the calculation could not settle: no weight came out, or it wants
 *  looking at. These are what the filter above the list narrows to. */
function needsAttention(item: LineItem | null): boolean {
  return !!item && item.status !== "ok";
}

/** What a line's derived figures were computed from. Two lines with the same
 *  signature have the same answer; a line whose signature moved has none yet. */
function signatureOf(line: DraftLine): string {
  return JSON.stringify([
    line.description.trim(), line.quantity, line.unit, line.cargo_form ?? "",
    line.length_cm ?? "", line.width_cm ?? "", line.height_cm ?? "", line.wall_thickness_mm ?? "",
  ]);
}

function PlusIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
      <path d="M10 4v12M4 10h12" strokeLinecap="round" />
    </svg>
  );
}

function DetailsIcon() {
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

function RowAction({ label, onClick, icon, danger, disabled }: {
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
  onImport,
  onLineWeightChange,
  translateMessage,
}: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const canRemove = draftLines.length > 1;

  // Held by id rather than by index: a line can be removed or duplicated while
  // the dialog is open, and an index would then quietly point at another line.
  const [editingId, setEditingId] = useState<number | null>(null);
  // A file dropped on the panel, handed to the import; and whether something is
  // being dragged over it, so the panel can say it will take it.
  const [dropped, setDropped] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  // Fifty imported lines with one that needs looking at is fifty cards of
  // scrolling to find it. This narrows the list to those, and says how many.
  const [onlyAttention, setOnlyAttention] = useState(false);
  const hasLines = draftLines.some((line) => line.description.trim());

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
   * The name recognition, asked as a snackbar rather than shown on the line.
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

  // What was last worked out per line, and for which text. Kept so that the
  // figures do not blink away on every keystroke; only shown for a line whose
  // own signature has not moved since.
  const computed = useRef(new Map<number, { signature: string; item: LineItem }>());
  if (resultLines && resultLines.length > 0) {
    const next = new Map<number, { signature: string; item: LineItem }>();
    draftLines.forEach((line, index) => {
      const item = resultLines[index];
      if (item) next.set(line.id, { signature: signatureOf(line), item });
    });
    computed.current = next;
  }

  function outcomeFor(line: DraftLine, index: number): { item: LineItem | null; stale: boolean } {
    const fresh = resultLines?.[index];
    if (fresh) return { item: fresh, stale: false };
    const remembered = computed.current.get(line.id);
    if (remembered && remembered.signature === signatureOf(line)) {
      return { item: remembered.item, stale: true };
    }
    return { item: null, stale: true };
  }

  // A new line gets the cursor. Detected here rather than passed in, because
  // adding is the wizard's action and focusing is this panel's business: the
  // one id that was not there a render ago is the one to type in.
  const seen = useRef<number[]>(draftLines.map((line) => line.id));
  const inputs = useRef(new Map<number, HTMLInputElement>());
  useEffect(() => {
    const ids = draftLines.map((line) => line.id);
    const added = ids.filter((id) => !seen.current.includes(id));
    seen.current = ids;
    // Exactly one new line is somebody adding or duplicating one. A handful at
    // once is an import, and an import should not drag the page to its last row.
    if (added.length === 1) {
      const input = inputs.current.get(added[0]);
      input?.focus();
      // jsdom has no layout, so it has no scrollIntoView either.
      input?.scrollIntoView?.({ block: "nearest" });
    }
  }, [draftLines]);

  function onFieldKeyDown(event: React.KeyboardEvent, index: number) {
    if (event.key !== "Enter") return;
    event.preventDefault();
    if (index === draftLines.length - 1) {
      onAddLine();
      return;
    }
    inputs.current.get(draftLines[index + 1].id)?.focus();
  }

  const editingIndex = draftLines.findIndex((line) => line.id === editingId);
  const editing = editingIndex >= 0 ? draftLines[editingIndex] : null;
  const editingOutcome = editing ? outcomeFor(editing, editingIndex) : null;

  // How the calculation judged the lines, for the summary above the list. A
  // line still being rechecked is neither settled nor a problem yet.
  const { settled, attention } = useMemo(() => {
    let settledCount = 0;
    let attentionCount = 0;
    draftLines.forEach((line, index) => {
      const { item, stale } = outcomeFor(line, index);
      if (!item || stale) return;
      settledCount += 1;
      if (needsAttention(item)) attentionCount += 1;
    });
    return { settled: settledCount, attention: attentionCount };
    // outcomeFor reads the refs, which change with the results.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftLines, resultLines]);

  // Nothing to narrow to any more: leaving the filter on would show an empty
  // list and look like the lines had gone.
  useEffect(() => {
    if (attention === 0 && onlyAttention) setOnlyAttention(false);
  }, [attention, onlyAttention]);

  const anyStale = useMemo(
    () => draftLines.some((line, index) => outcomeFor(line, index).stale && line.description.trim()),
    // outcomeFor reads the refs, which change with the results.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [draftLines, resultLines],
  );

  return (
    <div
      className={`${panelClass} overflow-hidden ${dragging ? "ring-2 ring-brand-400" : ""}`}
      onDragOver={onImport ? (event) => {
        if (!event.dataTransfer.types.includes("Files")) return;
        event.preventDefault();
        setDragging(true);
      } : undefined}
      onDragLeave={onImport ? (event) => {
        if (event.currentTarget.contains(event.relatedTarget as Node)) return;
        setDragging(false);
      } : undefined}
      onDrop={onImport ? (event) => {
        const file = event.dataTransfer.files?.[0];
        if (!file) return;
        event.preventDefault();
        setDragging(false);
        setDropped(file);
      } : undefined}
    >
      <div className="border-b border-slate-100 px-4 py-4 dark:border-slate-800 sm:px-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("review.linesTitle")}</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t("review.intro")}</p>
          </div>
          {onImport && (
            <div className="shrink-0">
              <GoodsImport
                hasLines={hasLines}
                onImport={onImport}
                dropped={dropped}
                onDroppedHandled={() => setDropped(null)}
              />
            </div>
          )}
        </div>
        {dragging && (
          <p className="mt-2 rounded-lg border border-dashed border-brand-300 bg-brand-50 px-3 py-2 text-xs text-brand-800 dark:border-brand-700 dark:bg-brand-950/40 dark:text-brand-200">
            {t("review.importDrop")}
          </p>
        )}
      </div>

      <div className="p-3 sm:p-4">
        {/* Column names for the row below, on the widths where the row is one
            line. Every control carries its own name for a screen reader, so
            this is the sighted reader's half of the same labelling. */}
        <div className="hidden gap-2 px-2 pb-1 lg:flex">
          <span className="w-6" />
          <span className={`${labelClass} min-w-[14rem] flex-1`}>{t("review.description")}</span>
          <span className={`${labelClass} w-20`}>{t("review.quantity")}</span>
          <span className={`${labelClass} w-32`}>{t("review.unit")}</span>
          <span className={`${labelClass} w-28 text-right`}>{t("review.weightTotal")}</span>
          <span className={`${labelClass} w-28`}>{t("review.status")}</span>
          <span className="w-[7.5rem]" />
        </div>

        {attention > 0 && (
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 dark:border-amber-900/50 dark:bg-amber-950/30">
            <span className="text-xs text-amber-900 dark:text-amber-200">
              {t("review.attentionSummary", { ok: settled - attention, attention })}
            </span>
            <button
              type="button"
              onClick={() => setOnlyAttention((on) => !on)}
              className="rounded-lg border border-amber-300 px-2.5 py-1 text-xs font-medium text-amber-900 dark:border-amber-800 dark:text-amber-200"
            >
              {onlyAttention ? t("review.showAllLines") : t("review.onlyAttention")}
            </button>
          </div>
        )}

        <ul className="space-y-2">
          {draftLines.map((line, index) => {
            const { item, stale } = outcomeFor(line, index);
            if (onlyAttention && !needsAttention(item)) return null;
            return (
              <li
                key={line.id}
                className="rounded-xl border border-slate-200 px-2 py-2 dark:border-slate-700"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    {index + 1}
                  </span>
                  <div className="min-w-[14rem] flex-1">
                    <EquipmentCombobox
                      value={line.description}
                      onChange={(value) => updateDraft(line.id, { description: value })}
                      inputRef={(element) => {
                        if (element) inputs.current.set(line.id, element);
                        else inputs.current.delete(line.id);
                      }}
                      onKeyDown={(event) => onFieldKeyDown(event, index)}
                      aria-label={t("review.descriptionOfLine", { number: index + 1 })}
                    />
                  </div>
                  <NumberInput
                    className={`${fieldClass} w-20`}
                    inputMode="decimal"
                    value={line.quantity}
                    aria-label={t("review.quantityOfLine", { number: index + 1 })}
                    onKeyDown={(event) => onFieldKeyDown(event, index)}
                    onChange={(event) =>
                      updateDraft(line.id, {
                        quantity: event.target.value === "" ? "" : Number(event.target.value),
                      })
                    }
                  />
                  <div className="w-32">
                    <UnitSelect
                      value={line.unit}
                      onChange={(unit) => updateDraft(line.id, { unit })}
                      category={item?.material_category}
                      catalogue={catalogue}
                      className={`${fieldClass} w-full`}
                      aria-label={t("review.unitOfLine", { number: index + 1 })}
                    />
                  </div>
                  <div
                    className={`w-28 text-right text-sm tabular-nums ${
                      stale ? "text-slate-400 dark:text-slate-500" : "text-slate-800 dark:text-slate-100"
                    }`}
                  >
                    {item?.weight_total_kg != null ? (
                      <>
                        {item.weight_total_kg}
                        <span className="ml-1 text-xs text-slate-500 dark:text-slate-400">kg</span>
                      </>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </div>
                  <div className="w-28">
                    {stale ? (
                      <span className="inline-block rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                        {t("review.toBeRechecked")}
                      </span>
                    ) : item ? (
                      <span className={`inline-block rounded-full px-2 py-0.5 text-xs ${statusColor(item.status)}`}>
                        {t(`status.${item.status}` as "status.ok")}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <RowAction label={t("review.lineDetails")} onClick={() => setEditingId(line.id)} icon={<DetailsIcon />} />
                    <RowAction label={t("review.duplicateLine")} onClick={() => onDuplicateLine(line.id)} icon={<CopyIcon />} />
                    <RowAction
                      label={t("review.removeLine")}
                      onClick={() => onRemoveLine(line.id)}
                      icon={<TrashIcon />}
                      danger
                      disabled={!canRemove}
                    />
                  </div>
                </div>
                <Derived
                  line={line}
                  item={item}
                  stale={stale}
                  translateMessage={translateMessage}
                />
              </li>
            );
          })}
        </ul>

        <button
          type="button"
          onClick={onAddLine}
          className="mt-3 flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 text-sm font-medium text-slate-600 dark:border-slate-700 dark:text-slate-300"
        >
          <PlusIcon />
          {t("review.addLine")}
        </button>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
          {anyStale ? t("review.recheckingHint") : t("review.keyboardHint")}
        </p>
      </div>

      {editing && (
        <LineEditDialog
          line={editing}
          result={editingOutcome?.item ?? null}
          position={editingIndex + 1}
          catalogue={catalogue}
          onChange={(patch) => updateDraft(editing.id, patch)}
          onWeightChange={
            onLineWeightChange && editingOutcome?.item
              ? (field, value) => onLineWeightChange(editingOutcome.item!.line_id, field, value)
              : undefined
          }
          onClose={() => setEditingId(null)}
        />
      )}
    </div>
  );
}

/**
 * Under the row: what was worked out and what is worth knowing about the line,
 * as text rather than as fields. This is where the card's "show more" went —
 * the same facts, without a second tap to reach them.
 */
function Derived({ line, item, stale, translateMessage }: {
  line: DraftLine;
  item: LineItem | null;
  stale: boolean;
  translateMessage: (msg: string) => string;
}) {
  const { t } = useTranslation();
  const parts: string[] = [];

  const measure = (field: "length_cm" | "width_cm" | "height_cm") => {
    const own = line[field];
    if (own !== undefined && own !== "") return own;
    return item?.[field] ?? null;
  };
  const round = ROUND_TYPES.has(item?.product_type ?? "");
  const length = measure("length_cm");
  const width = measure("width_cm");
  const height = round ? null : measure("height_cm");
  if (length != null || width != null || height != null) {
    const show = (value: number | null) => (value == null ? "?" : String(value));
    parts.push(round
      ? `${show(length)} × ⌀ ${show(width)} cm`
      : `${[length, width, height].map(show).join(" × ")} cm`);
  }
  if (item?.weight_each_kg != null) parts.push(`${item.weight_each_kg} kg/${t("review.each")}`);
  if (item?.transport_volume_m3 != null) parts.push(`${item.transport_volume_m3.toFixed(3)} m³`);
  const form = line.cargo_form ?? item?.cargo_form;
  if (form) parts.push(t(`forms.${form}`, form));
  const type = item?.product_type;
  if (type && WALL_PROFILE_TYPES.has(type) && line.wall_thickness_mm !== undefined && line.wall_thickness_mm !== "") {
    parts.push(`${line.wall_thickness_mm} mm`);
  }

  const messages = item?.messages ?? [];
  const chips = (
    <>
      {item?.dangerous_goods && !line.dangerous_goods && (
        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
          {t("review.dgDetected")}
        </span>
      )}
      {line.dangerous_goods && !line.confirmed_un && (
        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
          {t("review.dgYes")}
        </span>
      )}
      {line.confirmed_un && (
        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
          UN {line.confirmed_un}
        </span>
      )}
      {line.article?.code && (
        <span
          className="rounded-full bg-sky-100 px-2 py-0.5 text-[11px] font-medium text-sky-800 dark:bg-sky-900/40 dark:text-sky-300"
          title={t("articles.onLine")}
        >
          {line.article.code}
        </span>
      )}
    </>
  );

  if (parts.length === 0 && messages.length === 0 && !line.confirmed_un && !line.dangerous_goods
      && !line.article?.code && !item?.dangerous_goods) {
    return null;
  }

  return (
    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 pl-8 pr-2">
      {parts.length > 0 && (
        <span className={`text-xs ${stale ? "text-slate-400 dark:text-slate-500" : "text-slate-500 dark:text-slate-400"}`}>
          {parts.join(" · ")}
        </span>
      )}
      {chips}
      {messages.length > 0 && (
        <span className="text-xs text-amber-700 dark:text-amber-300">
          {messages.map(translateMessage).join(", ")}
        </span>
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
