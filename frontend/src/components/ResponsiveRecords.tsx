/**
 * Eén set gegevens, twee vormen: een tabel op desktop, kaarten op mobiel.
 *
 * Gebaseerd op "Designing User-Friendly Data Tables for Mobile Devices"
 * (Zahra Mohammadi, Bootcamp, juli 2025). De kern van dat stuk is dat een
 * tabel op een telefoon niet kleiner moet worden gemaakt maar van vorm moet
 * veranderen, en dat horizontaal scrollen een laatste redmiddel is en geen
 * oplossing. Wat daar wordt aanbevolen en hier is overgenomen:
 *
 * - Elke rij wordt een kaart. De kop draagt het identificerende veld links en
 *   de acties als iconen rechts.
 * - Het lichaam is een lijst van label-waardeparen: label klein en grijs links,
 *   waarde rechts, met een dunne scheidingslijn ertussen.
 * - Toon twee of drie velden en zet de rest achter "Toon meer", zodat er meer
 *   regels tegelijk op het scherm passen. Dat is hun uitgeklapte kaart.
 * - Zet de eenheid klein achter de waarde in plaats van er een kolom voor te
 *   reserveren: "1 200 (L)", niet een kolom "aantal" en een kolom "eenheid".
 *
 * Het onderdeel is bewust generiek: het weet niets van goederen, alleen van
 * kolommen. Een kolom zegt zelf of hij op een dichtgeklapte kaart hoort.
 */
import { ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";

export interface RecordColumn<T> {
  key: string;
  header: string;
  /** Op mobiel staat dit label links van de waarde; standaard de kolomkop. */
  cardLabel?: string;
  render: (row: T, index: number) => ReactNode;
  /** Zichtbaar op een dichtgeklapte kaart. Houd er twee of drie. */
  primary?: boolean;
  /** Rechts uitlijnen in de tabel — getallen lezen zo beter. */
  numeric?: boolean;
  /** Kolombreedte op desktop, bijvoorbeeld "w-32". */
  width?: string;
}

interface Props<T> {
  rows: T[];
  columns: RecordColumn<T>[];
  rowKey: (row: T, index: number) => string | number;
  /** De kaartkop op mobiel: het veld waaraan je de regel herkent. */
  cardTitle: (row: T, index: number) => ReactNode;
  /** Iconen rechtsboven in de kaartkop, en de laatste kolom van de tabel. */
  actions?: (row: T, index: number) => ReactNode;
  empty?: ReactNode;
  /** Onder de laatste rij, bijvoorbeeld een knop om een regel toe te voegen. */
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

  // Zonder expliciete keuze zijn de eerste twee kolommen de belangrijkste. Dat
  // is het "less is more" van het artikel: liever te weinig op de kaart dan een
  // kaart die zelf weer een scrollprobleem wordt.
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
 * Een waarde met haar eenheid klein erachter: "1 200 L".
 *
 * Het artikel zet de eenheid als kleine grijze toevoeging achter het getal in
 * plaats van er een kolom voor te reserveren. Dat scheelt op een telefoon een
 * hele kolom en leest bovendien als één gegeven, wat het ook is.
 */
export function QuantityWithUnit({ value, unit }: { value: ReactNode; unit?: string | null }) {
  return (
    <span className="tabular-nums">
      {value}
      {unit && <span className="ml-1 text-xs text-slate-500 dark:text-slate-400">{unit}</span>}
    </span>
  );
}
