import { useTranslation } from "react-i18next";

interface Step {
  n: number;
  label: string;
}

interface Props {
  steps: Step[];
  currentStep: number;
}

export default function WizardProgress({ steps, currentStep }: Props) {
  const { t } = useTranslation();
  const currentIndex = Math.max(
    0,
    steps.findIndex((s) => s.n === currentStep),
  );
  const progressPercent = ((currentIndex + 1) / steps.length) * 100;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 sm:p-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("wizard.progressStep", { current: currentIndex + 1, total: steps.length })}
          </p>
          <p className="mt-0.5 text-sm font-semibold text-slate-900 dark:text-slate-100 sm:text-base">
            {steps[currentIndex]?.label}
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700 dark:bg-brand-950/50 dark:text-brand-200">
          {Math.round(progressPercent)}%
        </span>
      </div>

      <div className="h-2.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-brand-500 via-brand-600 to-brand-500 transition-all duration-500 ease-out"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      <div className="mt-3 hidden gap-2 sm:grid" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}>
        {steps.map((step, index) => {
          const done = index < currentIndex;
          const active = index === currentIndex;
          return (
            <div key={step.n} className="flex flex-col items-center gap-1.5 text-center">
              <div
                className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                  active
                    ? "bg-brand-600 text-white shadow-md shadow-brand-600/30"
                    : done
                      ? "bg-brand-100 text-brand-700 dark:bg-brand-900/60 dark:text-brand-200"
                      : "bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500"
                }`}
              >
                {done ? "✓" : index + 1}
              </div>
              <span
                className={`max-w-[7rem] text-[10px] leading-tight ${
                  active ? "font-semibold text-brand-700 dark:text-brand-200" : "text-slate-500 dark:text-slate-400"
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
