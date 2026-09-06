/**
 * The frame around a shipment.
 *
 * Until this release the wizard's furniture was four strips stacked on top of
 * each other — a modality chip with a link beside it, a row of step segments, a
 * draft line, and then, at the bottom of whichever step was open, that step's
 * own pair of buttons. Every strip was added by the release that needed it and
 * none of them knew about the others, so the first screenful of a shipment was
 * mostly chrome and the button that moves you forward sat wherever the step
 * happened to end.
 *
 * This is one header and one action bar instead:
 *
 * - **The header** says which shipment this is, what has happened to it (the
 *   draft line), where you are in it (the steps) and which transport mode it
 *   is being entered for — the mode as a *switcher*, not a chooser. Choosing
 *   where to begin is `/`, and it stays there; this changes the mode of the
 *   shipment already in front of you.
 * - **The action bar** is `sticky bottom-0`, not `fixed`, and the difference
 *   is worth being exact about because it was measured. A sticky bar is still
 *   in the layout: it takes its own height at the end of the page, so the last
 *   row of a long form — and the error standing next to it — is never left
 *   underneath it. A fixed bar is out of the layout and covers that last row
 *   permanently, with no scroll position that reveals it. What sticky does not
 *   claim is that it never overlaps anything at all: while you are scrolled
 *   above its resting place it floats over what is behind it, the way every
 *   bar of this kind does. That overlap is transient and one scroll away; the
 *   one a fixed bar creates is not.
 *
 * Steps render their buttons through `WizardActions`, which puts them in the
 * bar. Rendered without a shell around it — as the steps' own tests do — it
 * falls back to a plain row in place, so a component stays testable on its own.
 */
import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import WizardProgress, { WizardStepKey } from "./WizardProgress";
import { AirIcon, RailIcon, RoadIcon, SeaIcon } from "./icons";

interface Slot {
  el: HTMLElement | null;
  /** Says whether anything is in the bar, so an empty bar is not drawn. */
  register: (present: boolean) => void;
}

const SlotContext = createContext<Slot | null>(null);

const actionRow = "flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3";

/** A step's buttons, placed in the shell's action bar. */
export function WizardActions({ children }: { children: ReactNode }) {
  const slot = useContext(SlotContext);
  const register = slot?.register;
  useEffect(() => {
    if (!register) return;
    register(true);
    return () => register(false);
  }, [register]);

  if (!slot) return <div className={actionRow}>{children}</div>;
  if (!slot.el) return null;
  return createPortal(<div className={actionRow}>{children}</div>, slot.el);
}

/** The glyph for a transport mode, so the switcher shows what it switches to. */
export function ModalityIcon({ modality, className }: { modality: string; className?: string }) {
  switch (modality) {
    case "rail":
      return <RailIcon className={className} />;
    // One ship for both: a cargo ship is what sails a sea route and what sails
    // an inland one, and drawing a second, subtly different ship would say
    // there is a distinction here that there is not.
    case "sea":
    case "inland":
      return <SeaIcon className={className} />;
    case "air":
      return <AirIcon className={className} />;
    default:
      return <RoadIcon className={className} />;
  }
}

interface Step {
  n: number;
  key: WizardStepKey;
  label: string;
}

interface Props {
  /** What this shipment is called — its reference, or that it is a new one. */
  title: string;
  modality: string;
  /** The modes this installation will draw documents for. */
  modalities: readonly string[];
  onModality: (key: string) => void;
  steps: Step[];
  currentStep: number;
  visited?: WizardStepKey[];
  onGoTo?: (key: WizardStepKey) => void;
  /** The draft line, built by the page that knows what may be stored. */
  draft?: ReactNode;
  /** The assistant's button, which belongs beside the title and nowhere else. */
  aside?: ReactNode;
  /** How many things are waiting to be looked at, counted by the caller. */
  attention?: number;
  children: ReactNode;
}

export default function WizardShell({
  title, modality, modalities, onModality, steps, currentStep, visited, onGoTo,
  draft, aside, attention = 0, children,
}: Props) {
  const { t } = useTranslation();
  const [el, setEl] = useState<HTMLElement | null>(null);
  const [filled, setFilled] = useState(0);
  const register = useCallback((present: boolean) => {
    setFilled((n) => n + (present ? 1 : -1));
  }, []);
  const slot = useMemo<Slot>(() => ({ el, register }), [el, register]);

  const index = Math.max(0, steps.findIndex((s) => s.n === currentStep));

  return (
    <SlotContext.Provider value={slot}>
      <div className="space-y-4 sm:space-y-6">
        <header className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          {/* Two rows at every width, rather than one row that wraps. Wrapping
              put the title in a flex line with the draft state and the mode,
              and on a phone that left the title 20px of it: a shipment called
              "N…". What a shipment is called comes first and gets the width. */}
          <div className="px-3 py-3 sm:px-4">
            <div className="flex items-center gap-2">
              <h2 className="min-w-0 flex-1 truncate text-base font-semibold text-slate-900 sm:text-lg dark:text-slate-100">
                {title}
              </h2>
              {aside}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5">
            {draft}
            <label className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <ModalityIcon modality={modality} className="h-4 w-4 shrink-0" />
              <span className="sr-only sm:not-sr-only">{t("wizard.mode")}</span>
              <select
                value={modality}
                onChange={(e) => onModality(e.target.value)}
                aria-label={t("wizard.mode")}
                className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              >
                {modalities.map((key) => (
                  <option key={key} value={key}>
                    {t(`modality.${key}`)}
                  </option>
                ))}
              </select>
            </label>
            {/* The switcher changes the mode of this shipment; the tiles are
                where a shipment is *begun*, and somebody whose default mode
                takes them straight past them still has to be able to get back
                to them. Without this link `?choose=1` would have no door. */}
            <Link
              to="/?choose=1"
              className="text-xs text-slate-500 hover:underline dark:text-slate-400"
            >
              {t("wizard.changeModality")}
            </Link>
            </div>
          </div>

          <div className="border-t border-slate-200 px-3 py-2.5 sm:px-4 dark:border-slate-800">
            {/* On a phone the segments are icons, which say where you are but
                not how far along. This says it in words, and only there. */}
            <p className="mb-2 text-xs font-medium text-slate-500 sm:hidden dark:text-slate-400">
              {t("wizard.progressStep", { current: index + 1, total: steps.length })}
            </p>
            <WizardProgress
              steps={steps}
              currentStep={currentStep}
              visited={visited}
              onGoTo={onGoTo}
            />
          </div>
        </header>

        <div>{children}</div>

        <div
          className={
            filled > 0
              ? "sticky bottom-0 z-30 -mx-3 border-t border-slate-200 bg-white/95 px-3 py-3 backdrop-blur sm:-mx-4 sm:px-4 dark:border-slate-800 dark:bg-slate-900/95"
              : "hidden"
          }
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
            {attention > 0 ? (
              <p className="text-xs font-medium text-amber-700 dark:text-amber-300">
                {t("wizard.attention", { count: attention })}
              </p>
            ) : (
              <span />
            )}
            <div ref={setEl} className="sm:ml-auto" />
          </div>
        </div>
      </div>
    </SlotContext.Provider>
  );
}
