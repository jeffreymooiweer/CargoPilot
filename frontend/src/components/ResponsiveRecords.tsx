/**
 * One set of data, two shapes: a table on desktop, cards on mobile.
 *
 * Based on "Designing User-Friendly Data Tables for Mobile Devices" (Zahra
 * Mohammadi, Bootcamp, July 2025). The core of that piece is that a table on a
 * phone should not be made smaller but should change shape, and that horizontal
 * scrolling is a last resort and not a solution. What it recommends and is
 * adopted here:
 *
 * - Every row becomes a card. The heading carries the identifying field on the
 *   left and the actions as icons on the right.
 * - The body is a list of label-value pairs: label small and grey on the left,
 *   value on the right, with a thin dividing line between them.
 * - Show two or three fields and put the rest behind "Show more", so more lines
 *   fit on the screen at once. That is their expanded card.
 * - Put the unit small behind the value instead of reserving a column for it:
 *   "1 200 (L)", not a column "quantity" and a column "unit".
 *
 * The component is deliberately generic: it knows nothing about goods, only
 * about columns. A column says for itself whether it belongs on a collapsed card.
 */
import { ReactNode, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

export interface RecordColumn<T> {
  key: string;
  header: string;
  /** On mobile this label sits to the left of the value; the column heading by default. */
  cardLabel?: string;
  render: (row: T, index: number) => ReactNode;
  /** Visible on a collapsed card. Keep two or three of them. */
  primary?: boolean;
  /** Right-align in the table — figures read better that way. */
  numeric?: boolean;
  /** Column width on desktop, for example "w-32". */
  width?: string;
}

interface Props<T> {
  rows: T[];
  columns: RecordColumn<T>[];
  rowKey: (row: T, index: number) => string | number;
  /** The card heading on mobile: the field you recognise the line by. */
  cardTitle: (row: T, index: number) => ReactNode;
  /** Icons at the top right of the card heading, and the last column of the table. */
  actions?: (row: T, index: number) => ReactNode;
  empty?: ReactNode;
  /** Below the last row, for example a button to add a line. */
  footer?: ReactNode;
  /**
   * A floor for the desktop table, for example "min-w-[1620px]".
   *
   * Without one the table is `w-full` and can never be wider than its
   * container, so `overflow-x-auto` never engages and the browser squeezes the
   * cells instead. On a reading table that is fine — text wraps. On a table you
   * *type* in it is not: the lines step gave its 80px quantity field 30px and
   * its unit select 28px, which is a field you cannot enter anything in.
   *
   * With a floor the table keeps the width its inputs need and scrolls when the
   * screen is too small for it. A scrollbar is a nuisance; a 30px number field
   * is a dead end.
   */
  minWidth?: string;
  /**
   * A detail button per row, opening a panel from the right with every column
   * under each other.
   *
   * The lines table has thirteen columns of input fields and wants 1,620px, so
   * on anything narrower than a large monitor something has to give: either the
   * table scrolls sideways or the fields get squeezed. This is the third way
   * out — the row you are working on gets the full width of a panel, one field
   * per line, and the table can stay as wide or as narrow as it likes.
   *
   * It is the same shape as the mobile card, which is why it lives here: the
   * component already knows how to lay a row out as label-and-value pairs.
   * Desktop only, because on a phone the card *is* that view.
   */
  detail?: boolean;
}

const cellText = "text-sm text-slate-800 dark:text-slate-100";
const labelText = "text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400";

export default function ResponsiveRecords<T>({
  rows,
  columns,
  rowKey,
  cardTitle,
  actions,
  empty,
  footer,
  minWidth,
  detail = false,
}: Props<T>) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  // The row is held by its key rather than its index: a line can be deleted or
  // duplicated while the panel is open, and an index would then point at a
  // different row without anything looking wrong.
  const [detailKey, setDetailKey] = useState<string | null>(null);
  // Two states, because the panel has to be in the DOM *before* it slides: a
  // node that is mounted and moved in the same frame simply appears.
  const [slidIn, setSlidIn] = useState(false);
  const closing = useRef<number | undefined>(undefined);
  const opener = useRef<HTMLElement | null>(null);
  const panel = useRef<HTMLDivElement | null>(null);

  const detailIndex = rows.findIndex((row, index) => String(rowKey(row, index)) === detailKey);
  const detailRow = detailIndex >= 0 ? rows[detailIndex] : null;

  function openDetail(key: string, button: HTMLElement) {
    window.clearTimeout(closing.current);
    opener.current = button;
    setDetailKey(key);
  }

  function closeDetail() {
    setSlidIn(false);
    // Unmount only once it has slid out, otherwise the panel vanishes instead
    // of leaving.
    closing.current = window.setTimeout(() => setDetailKey(null), 300);
    opener.current?.focus();
  }

  useEffect(() => {
    if (detailKey === null) return undefined;
    const frame = requestAnimationFrame(() => setSlidIn(true));
    return () => cancelAnimationFrame(frame);
  }, [detailKey]);

  // A row that disappears under the panel — deleted from the table behind it —
  // takes the panel with it rather than leaving an empty one.
  useEffect(() => {
    if (detailKey !== null && detailIndex < 0) setDetailKey(null);
  }, [detailKey, detailIndex]);

  useEffect(() => {
    if (detailKey === null) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeDetail();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [detailKey]);

  // Focus moves into the panel on open and back to the button that opened it on
  // close, so a keyboard user is not left where the panel is not.
  useEffect(() => {
    if (detailKey !== null) panel.current?.focus();
  }, [detailKey]);

  useEffect(() => {
    if (detailKey === null) return undefined;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [detailKey]);

  useEffect(() => () => window.clearTimeout(closing.current), []);

  // A table with a floor can scroll sideways, and then the actions — including
  // the button that opens the panel and makes the scrolling unnecessary — end
  // up off the right-hand edge. Pinning that column keeps them in reach. It
  // needs its own background, or the cells sliding under it show through.
  const stickyActions = minWidth
    ? "sticky right-0 bg-white pl-2 dark:bg-slate-900 before:absolute before:inset-y-0 before:left-0 before:w-px before:bg-slate-200 dark:before:bg-slate-700"
    : "";

  // Without an explicit choice the first two columns are the most important.
  // That is the article's "less is more": better too little on the card than a
  // card that becomes a scrolling problem of its own.
  const marked = columns.filter((column) => column.primary);
  const primary = marked.length > 0 ? marked : columns.slice(0, 2);
  const secondary = columns.filter((column) => !primary.includes(column));

  function toggle(key: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  if (rows.length === 0 && empty) {
    return <div className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">{empty}</div>;
  }

  return (
    <>
      {/* Desktop: een gewone tabel. Daar is de ruimte er wel voor, en een tabel
          laat je rijen met elkaar vergelijken zoals een kaart dat nooit kan. */}
      <div className="hidden md:block overflow-x-auto">
        <table className={`w-full text-left ${minWidth ?? ""}`}>
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className={`py-2 pr-3 text-xs font-medium text-slate-500 dark:text-slate-400 ${
                    column.numeric ? "text-right" : ""
                  } ${column.width ?? ""}`}
                >
                  {column.header}
                </th>
              ))}
              {(actions || detail) && (
                <th
                  scope="col"
                  className={`${detail ? "w-32" : "w-24"} py-2 text-right text-xs font-medium text-slate-500 dark:text-slate-400 ${stickyActions}`}
                >
                  {t("records.actions")}
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={rowKey(row, index)} className="border-b border-slate-100 align-top dark:border-slate-800">
                {columns.map((column) => (
                  <td key={column.key} className={`py-2 pr-3 ${cellText} ${column.numeric ? "text-right tabular-nums" : ""}`}>
                    {column.render(row, index)}
                  </td>
                ))}
                {(actions || detail) && (
                  // Side by side rather than stacked. They used to wrap because
                  // the cell was too narrow for two 36px buttons; with the
                  // panel taking the pressure off the table there is room.
                  <td className={`py-2 ${stickyActions}`}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">
                      {detail && (
                        <button
                          type="button"
                          onClick={(event) =>
                            openDetail(String(rowKey(row, index)), event.currentTarget)
                          }
                          aria-label={t("records.showDetail")}
                          title={t("records.showDetail")}
                          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                        >
                          <DetailIcon />
                        </button>
                      )}
                      {actions?.(row, index)}
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobiel: kaarten. */}
      <div className="space-y-3 md:hidden">
        {rows.map((row, index) => {
          const key = String(rowKey(row, index));
          const isOpen = expanded.has(key);
          return (
            <article
              key={key}
              className={`overflow-hidden rounded-xl border transition-shadow ${
                isOpen
                  ? "border-blue-300 shadow-sm dark:border-blue-800"
                  : "border-slate-200 dark:border-slate-700"
              }`}
            >
              <header className="flex items-center justify-between gap-2 bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
                <div className="min-w-0 flex-1 truncate text-sm font-medium text-slate-900 dark:text-slate-100">
                  {cardTitle(row, index)}
                </div>
                {actions && <div className="flex shrink-0 items-center gap-1">{actions(row, index)}</div>}
              </header>

              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {primary.map((column) => (
                  <Row key={column.key} label={column.cardLabel ?? column.header}>
                    {column.render(row, index)}
                  </Row>
                ))}
                {isOpen &&
                  secondary.map((column) => (
                    <Row key={column.key} label={column.cardLabel ?? column.header}>
                      {column.render(row, index)}
                    </Row>
                  ))}
              </div>

              {secondary.length > 0 && (
                <button
                  type="button"
                  onClick={() => toggle(key)}
                  aria-expanded={isOpen}
                  className="flex min-h-[44px] w-full items-center justify-center gap-1 border-t border-slate-100 text-sm font-medium text-blue-700 dark:border-slate-800 dark:text-blue-300"
                >
                  {isOpen ? t("records.viewLess") : t("records.viewMore")}
                  <Chevron open={isOpen} />
                </button>
              )}
            </article>
          );
        })}
        {footer}
      </div>

      <div className="hidden md:block">{footer}</div>

      {/* The detail panel. Every column under each other, in the order the table
          has them, with the same controls — so it is a place to *work*, not a
          preview you have to close again to change anything. */}
      {detailRow !== null && (
        <div className="fixed inset-0 z-50 hidden md:block" role="presentation">
          <button
            type="button"
            aria-label={t("records.closeDetail")}
            onClick={closeDetail}
            className={`absolute inset-0 bg-slate-900/30 transition-opacity duration-300 motion-reduce:transition-none ${
              slidIn ? "opacity-100" : "opacity-0"
            }`}
          />
          <div
            ref={panel}
            role="dialog"
            aria-modal="true"
            aria-label={t("records.detailTitle")}
            tabIndex={-1}
            className={`absolute inset-y-0 right-0 flex w-[min(100%,32rem)] flex-col border-l border-slate-200 bg-white shadow-2xl transition-transform duration-300 ease-out motion-reduce:transition-none dark:border-slate-800 dark:bg-slate-900 ${
              slidIn ? "translate-x-0" : "translate-x-full"
            }`}
          >
            <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3 dark:border-slate-800">
              <div className="min-w-0">
                <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  {t("records.detailTitle")}
                </p>
                <div className="mt-0.5 text-sm font-medium text-slate-900 dark:text-slate-100">
                  {cardTitle(detailRow, detailIndex)}
                </div>
              </div>
              <button
                type="button"
                onClick={closeDetail}
                aria-label={t("records.closeDetail")}
                className="-mr-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
              >
                <CloseIcon />
              </button>
            </header>

            <div className="flex-1 overflow-y-auto px-4 py-2">
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {columns.map((column) => (
                  <div key={column.key} className="py-2.5">
                    <p className={labelText}>{column.cardLabel ?? column.header}</p>
                    <div className={`mt-1 ${cellText}`}>{column.render(detailRow, detailIndex)}</div>
                  </div>
                ))}
              </div>
            </div>

            {actions && (
              <footer className="flex items-center justify-end gap-1 border-t border-slate-200 px-4 py-3 dark:border-slate-800">
                {actions(detailRow, detailIndex)}
              </footer>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function DetailIcon() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <rect x="2" y="3.5" width="5.5" height="5.5" rx="1.6" />
      <rect x="2" y="9.25" width="5.5" height="5.5" rx="1.6" />
      <rect x="2" y="15" width="5.5" height="5.5" rx="1.6" />
      <rect x="9.75" y="4.9" width="12.25" height="2.7" rx="1.35" />
      <rect x="9.75" y="10.65" width="12.25" height="2.7" rx="1.35" />
      <rect x="9.75" y="16.4" width="12.25" height="2.7" rx="1.35" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
      <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
    </svg>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 px-3 py-2">
      <span className={`${labelText} shrink-0`}>{label}</span>
      <span className={`${cellText} min-w-0 flex-1 text-right`}>{children}</span>
    </div>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      aria-hidden
    >
      <path d="M6 8l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * A value with its unit small behind it: "1 200 L".
 *
 * The article puts the unit as a small grey addition behind the figure instead
 * of reserving a column for it. On a phone that saves a whole column and it
 * reads as one piece of data, which is what it is.
 */
export function QuantityWithUnit({ value, unit }: { value: ReactNode; unit?: string | null }) {
  return (
    <span className="tabular-nums">
      {value}
      {unit && <span className="ml-1 text-xs text-slate-500 dark:text-slate-400">{unit}</span>}
    </span>
  );
}
