interface Step {
  n: number;
  label: string;
}

interface Props {
  steps: Step[];
  currentStep: number;
}

function segmentState(index: number, currentIndex: number): "done" | "active" | "upcoming" {
  if (index < currentIndex) return "done";
  if (index === currentIndex) return "active";
  return "upcoming";
}

function clipPath(index: number, total: number): string {
  const tip = "0.85rem";
  if (total === 1) return "none";
  if (index === 0) {
    return `polygon(0 0, calc(100% - ${tip}) 0, 100% 50%, calc(100% - ${tip}) 100%, 0 100%)`;
  }
  if (index === total - 1) {
    return `polygon(0 0, 100% 0, 100% 100%, 0 100%, ${tip} 50%)`;
  }
  return `polygon(0 0, calc(100% - ${tip}) 0, 100% 50%, calc(100% - ${tip}) 100%, 0 100%, ${tip} 50%)`;
}

function segmentColors(state: "done" | "active" | "upcoming"): string {
  if (state === "active") return "bg-brand-600 text-white";
  if (state === "done") return "bg-brand-500 text-white";
  return "bg-slate-200 text-slate-500 dark:bg-slate-800 dark:text-slate-400";
}

export default function WizardProgress({ steps, currentStep }: Props) {
  const currentIndex = Math.max(
    0,
    steps.findIndex((s) => s.n === currentStep),
  );

  return (
    <nav aria-label="Wizard voortgang" className="w-full">
      <ol className="flex w-full list-none">
        {steps.map((step, index) => {
          const state = segmentState(index, currentIndex);

          return (
            <li
              key={step.n}
              aria-current={state === "active" ? "step" : undefined}
              className={`relative flex min-h-[44px] flex-1 items-center justify-center px-2 py-2.5 text-center text-xs font-semibold sm:px-5 sm:text-sm ${segmentColors(state)} ${
                index > 0 ? "-ml-3 sm:-ml-3.5" : ""
              }`}
              style={{
                clipPath: clipPath(index, steps.length),
                zIndex: steps.length - index,
              }}
            >
              <span className="truncate px-1 sm:px-2">{step.label}</span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
