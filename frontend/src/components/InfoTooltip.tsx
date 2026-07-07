interface Props {
  text: string;
}

export default function InfoTooltip({ text }: Props) {
  if (!text) return null;

  return (
    <span className="relative inline-flex group/info align-middle">
      <button
        type="button"
        tabIndex={0}
        className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-slate-300/80 bg-slate-100 text-[10px] font-bold leading-none text-slate-500 transition-colors hover:border-brand-400 hover:bg-brand-50 hover:text-brand-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-400 dark:hover:border-brand-500 dark:hover:bg-brand-950/60 dark:hover:text-brand-300"
        aria-label={text}
      >
        i
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-[calc(100%+8px)] left-1/2 z-50 w-64 -translate-x-1/2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-xs font-normal leading-relaxed text-slate-700 opacity-0 shadow-xl transition-opacity duration-150 group-hover/info:opacity-100 group-focus-within/info:opacity-100 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:shadow-black/40"
      >
        {text}
        <span
          aria-hidden
          className="absolute left-1/2 top-full -translate-x-1/2 border-[6px] border-transparent border-t-white dark:border-t-slate-800"
        />
        <span
          aria-hidden
          className="absolute left-1/2 top-[calc(100%-1px)] -translate-x-1/2 border-[7px] border-transparent border-t-slate-200 dark:border-t-slate-600"
        />
      </span>
    </span>
  );
}
