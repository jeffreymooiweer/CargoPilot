/**
 * One set of data, one shape: every record is a card, on every screen.
 *
 * This used to be `ResponsiveRecords`, which showed a table on desktop and
 * cards on a phone. The table was the problem it was built to solve and never
 * could: its cells were *input fields*, and a row of thirteen fields does not
 * fit on anything short of a very large monitor. Everything that grew around
 * that — weighing columns against the available width, priorities and groups
 * so the right ones fell away first, a floor width, a detail panel to reach
 * what had fallen away — was machinery to make a shape work that did not fit
 * the content. It is gone.
 *
 * What replaces it is the card that already worked on the phone, now used
 * everywhere:
 *
 * - the heading carries the identifying field on the left and the actions as
 *   icons on the right;
 * - the body is a list of label-value pairs, label small and grey on the left,
 *   value on the right;
 * - two or three fields show while the card is collapsed, the rest opens with
 *   "show more", so several records fit on the screen at once.
 *
 * The values here are read-only by design. Editing happens in a dialog the
 * caller opens from its own action icon, which is what makes one shape at
 * every width possible: text reflows, a row of input fields does not.
 *
 * Based on "Designing User-Friendly Data Tables for Mobile Devices" (Zahra
 * Mohammadi, Bootcamp, July 2025) — a table on a small screen should not be
 * made smaller but should change shape. The conclusion here goes one step
 * further than the article: for a record you *edit*, the card is not the
 * small-screen compromise, it is the better shape at every size.
 */
import { ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";

export interface RecordField<T> {
  key: string;
  /** Sits to the left of the value. */
  label: string;
  render: (row: T, index: number) => ReactNode;
  /** Visible on a collapsed card. Keep two or three of them. */
  primary?: boolean;
}

interface Props<T> {
  rows: T[];
  fields: RecordField<T>[];
  rowKey: (row: T, index: number) => string | number;
  /** The card heading: the field you recognise the record by. */
  cardTitle: (row: T, index: number) => ReactNode;
  /** Icons at the top right of the card heading. */
  actions?: (row: T, index: number) => ReactNode;
  /**
   * Shown under the primary fields whatever the card's state.
   *
   * For something the record needs an *answer* to rather than something it
   * merely holds — the dangerous-goods recognition asking whether it got the
   * substance right. Behind "show more" it would go unanswered by exactly the
   * people who never open the card.
   */
  banner?: (row: T, index: number) => ReactNode;
  empty?: ReactNode;
  /** Below the last card, for example a button to add a record. */
  footer?: ReactNode;
}

const cellText = "text-sm text-slate-800 dark:text-slate-100";
const labelText = "text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400";

export default function RecordCards<T>({
  rows,
  fields,
  rowKey,
  cardTitle,
  actions,
  banner,
  empty,
  footer,
}: Props<T>) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // Without an explicit choice the first two fields are the most important.
  // Better too little on the card than a card that becomes a scrolling problem
  // of its own.
  const marked = fields.filter((field) => field.primary);
  const primary = marked.length > 0 ? marked : fields.slice(0, 2);
  const secondary = fields.filter((field) => !primary.includes(field));

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
    // Capped rather than full width: the shell runs to 1800px with the side
    // menu folded away, and a label on the far left with its value on the far
    // right is two columns you have to travel between rather than one line you
    // read.
    <div className="w-full max-w-4xl space-y-3">
      {rows.map((row, index) => {
        const key = String(rowKey(row, index));
        const isOpen = expanded.has(key);
        const note = banner?.(row, index);
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
              {primary.map((field) => (
                <Row key={field.key} label={field.label}>
                  {field.render(row, index)}
                </Row>
              ))}
              {isOpen &&
                secondary.map((field) => (
                  <Row key={field.key} label={field.label}>
                    {field.render(row, index)}
                  </Row>
                ))}
            </div>

            {note && <div className="border-t border-slate-100 px-3 py-2 dark:border-slate-800">{note}</div>}

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
 * The unit as a small grey addition behind the figure instead of a column of
 * its own: it reads as one piece of data, which is what it is.
 */
export function QuantityWithUnit({ value, unit }: { value: ReactNode; unit?: string | null }) {
  return (
    <span className="tabular-nums">
      {value}
      {unit && <span className="ml-1 text-xs text-slate-500 dark:text-slate-400">{unit}</span>}
    </span>
  );
}

/** An empty value. One dash everywhere rather than a blank that reads as a fault. */
export function NoValue() {
  return <span className="text-slate-400">—</span>;
}
