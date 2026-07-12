export type WizardStepKey = "forms" | "lines" | "questions" | "dg" | "details" | "export";

interface Step {
  n: number;
  key: WizardStepKey;
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

function StepIcon({ stepKey }: { stepKey: WizardStepKey }) {
  const common = {
    className: "h-4 w-4 shrink-0 sm:h-[1.125rem] sm:w-[1.125rem]",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    viewBox: "0 0 24 24",
    "aria-hidden": true as const,
  };

  switch (stepKey) {
    case "forms":
      return (
        <svg {...common}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
        </svg>
      );
    case "lines":
      return (
        <svg {...common}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 10h16M4 14h10M4 18h8" />
        </svg>
      );
    case "questions":
      return (
        <svg {...common}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    case "dg":
      return (
        <svg {...common}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      );
    case "details":
      return (
        <svg {...common}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      );
    case "export":
      return (
        <svg {...common}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
      );
  }
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
              aria-label={step.label}
              title={step.label}
              className={`relative flex min-h-[40px] flex-1 items-center justify-center px-1 py-2 text-center text-xs font-semibold sm:min-h-[44px] sm:px-5 sm:py-2.5 sm:text-sm ${segmentColors(state)} ${
                index > 0 ? "-ml-2.5 sm:-ml-3.5" : ""
              }`}
              style={{
                clipPath: clipPath(index, steps.length),
                zIndex: steps.length - index,
              }}
            >
              <span className="sm:hidden">
                <StepIcon stepKey={step.key} />
              </span>
              <span className="hidden truncate px-1 sm:inline sm:px-2">{step.label}</span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
