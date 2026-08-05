import { ReactNode } from "react";

/** Inklapbare kaart met een altijd zichtbare samenvattingsregel.
 *
 * De gevaarlijke-stoffenstap toont veel bevindingen tegelijk; alles uitgeklapt
 * is onleesbaar, alles verstoppen is gevaarlijker. Het compromis: de kop
 * draagt de uitkomst (statuschips, aantallen) en blijft altijd in beeld, de
 * onderbouwing klapt open wanneer de gebruiker die nodig heeft. Wat rood is
 * hoort standaard open te staan — dat bepaalt de aanroeper via `defaultOpen`.
 */
export default function CollapsibleSection({
  title,
  chips,
  defaultOpen = false,
  children,
}: {
  title: ReactNode;
  chips?: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  return (
    <details
      open={defaultOpen}
      className="group rounded-xl border border-slate-200 dark:border-slate-800"
    >
      <summary className="flex cursor-pointer select-none list-none flex-wrap items-center gap-2 rounded-xl px-3 py-2.5 hover:bg-slate-50 dark:hover:bg-slate-800/50 [&::-webkit-details-marker]:hidden">
        <span
          aria-hidden
          className="text-[10px] text-slate-400 transition-transform group-open:rotate-90"
        >
          ▶
        </span>
        <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</span>
        {chips}
      </summary>
      <div className="space-y-2 border-t border-slate-100 px-3 pb-3 pt-2.5 dark:border-slate-800">
        {children}
      </div>
    </details>
  );
}

export function SummaryChip({
  className = "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${className}`}>
      {children}
    </span>
  );
}
