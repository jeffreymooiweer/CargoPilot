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
import { ReactNode, useState } from "react";
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
}: Props<T>) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

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
        <table className="w-full text-left">
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
              {actions && <th scope="col" className="w-24 py-2 text-right text-xs font-medium text-slate-500 dark:text-slate-400">{t("records.actions")}</th>}
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
                {actions && <td className="py-2 text-right">{actions(row, index)}</td>}
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
    </>
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
