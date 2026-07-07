import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, AppendixFlags, DgInstructions, LineItem } from "../api/client";
import InfoTooltip from "./InfoTooltip";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const buttonPrimary = "bg-brand-600 text-white px-5 py-2 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50";
const buttonSecondary = "px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800";
const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";

const FLAG_STEPS = [
  { key: "loaded", mode: "all" },
  { key: "stackable", mode: "any" },
  { key: "rotatable", mode: "any" },
  { key: "weapons", mode: "any" },
  { key: "conditioned", mode: "any" },
  { key: "dangerous_goods", mode: "any" },
  { key: "ammunition", mode: "any" },
  { key: "itar", mode: "any" },
  { key: "tbb", mode: "any" },
] as const;

type FlagKey = (typeof FLAG_STEPS)[number]["key"];

export interface FlagAnswer {
  yes: boolean;
  lineIds: number[];
}

export interface AppendixAnswers {
  flags: Partial<Record<FlagKey, FlagAnswer>>;
  temperatureByLine: Record<number, string>;
  tbbCategoryByLine: Record<number, string>;
}

type Screen =
  | { kind: "flag-answer"; flagIndex: number }
  | { kind: "flag-pick"; flagIndex: number }
  | { kind: "extra-temperature"; lineIds: number[] }
  | { kind: "extra-tbb"; lineIds: number[] };

interface Props {
  lines: LineItem[];
  onComplete: (lines: LineItem[]) => void;
  onBack: () => void;
}

function defaultFlags(): AppendixFlags {
  return {
    loaded: "Y",
    stackable: "N",
    rotatable: "N",
    weapons: "N",
    conditioned: "N",
    temperature_c: undefined,
    dangerous_goods: "N",
    ammunition: "N",
    itar: "N",
    tbb: "N",
    tbb_category: undefined,
  };
}

export function applyAppendixAnswers(lines: LineItem[], answers: AppendixAnswers): LineItem[] {
  return lines.map((line) => {
    if (!line.include) return line;
    const flags = defaultFlags();

    for (const step of FLAG_STEPS) {
      const answer = answers.flags[step.key];
      if (!answer) continue;

      if (step.mode === "all") {
        if (answer.yes) {
          flags[step.key] = "Y";
        } else {
          flags[step.key] = answer.lineIds.includes(line.line_id) ? "Y" : "N";
        }
      } else if (answer.yes) {
        flags[step.key] = answer.lineIds.includes(line.line_id) ? "Y" : "N";
      } else {
        flags[step.key] = "N";
      }
    }

    if (flags.conditioned === "Y") {
      flags.temperature_c = answers.temperatureByLine[line.line_id] || undefined;
    }
    if (flags.tbb === "Y") {
      flags.tbb_category = answers.tbbCategoryByLine[line.line_id] || undefined;
    }

    return { ...line, appendix_flags: flags };
  });
}

function initialScreen(): Screen {
  return { kind: "flag-answer", flagIndex: 0 };
}

export default function AppendixQuestionsWizard({ lines, onComplete, onBack }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language.startsWith("en") ? "en" : "nl";
  const included = useMemo(() => lines.filter((line) => line.include), [lines]);

  const [instructions, setInstructions] = useState<DgInstructions | null>(null);
  const [screen, setScreen] = useState<Screen>(initialScreen);
  const [history, setHistory] = useState<Screen[]>([]);
  const [answers, setAnswers] = useState<AppendixAnswers>({
    flags: {},
    temperatureByLine: {},
    tbbCategoryByLine: {},
  });
  const [pickSelection, setPickSelection] = useState<number[]>([]);

  useEffect(() => {
    api.dgInstructions().then(setInstructions).catch(() => setInstructions(null));
  }, []);

  useEffect(() => {
    if (screen.kind !== "flag-pick") return;
    const key = FLAG_STEPS[screen.flagIndex].key;
    const existing = answers.flags[key]?.lineIds;
    if (existing?.length) {
      setPickSelection(existing);
      return;
    }
    if (key === "dangerous_goods") {
      setPickSelection(
        included.filter((line) => line.detected_un_numbers && line.detected_un_numbers.length > 0).map((line) => line.line_id),
      );
      return;
    }
    setPickSelection([]);
  }, [screen, included, answers.flags]);

  const helpFor = (key: string) => instructions?.a1_flags?.[key]?.[lang] || "";

  const progress = useMemo(() => {
    const total = FLAG_STEPS.length + 2;
    let current = 0;
    if (screen.kind === "flag-answer" || screen.kind === "flag-pick") {
      current = screen.flagIndex + (screen.kind === "flag-pick" ? 0.5 : 0);
    } else if (screen.kind === "extra-temperature") {
      current = FLAG_STEPS.findIndex((s) => s.key === "conditioned") + 1;
    } else {
      current = FLAG_STEPS.length + 1;
    }
    return { current: Math.min(current + 1, total), total };
  }, [screen]);

  const goTo = (next: Screen) => {
    setHistory((h) => [...h, screen]);
    setScreen(next);
  };

  const goBack = () => {
    const prev = history[history.length - 1];
    if (!prev) {
      onBack();
      return;
    }
    setHistory((h) => h.slice(0, -1));
    setScreen(prev);
  };

  const afterFlagResolved = (flagIndex: number, answer: FlagAnswer) => {
    const key = FLAG_STEPS[flagIndex].key;
    const nextAnswers: AppendixAnswers = {
      ...answers,
      flags: { ...answers.flags, [key]: answer },
    };
    setAnswers(nextAnswers);

    if (key === "conditioned" && answer.yes && answer.lineIds.length > 0) {
      goTo({ kind: "extra-temperature", lineIds: answer.lineIds });
      return;
    }
    if (flagIndex >= FLAG_STEPS.length - 1) {
      if (key === "tbb" && answer.yes && answer.lineIds.length > 0) {
        goTo({ kind: "extra-tbb", lineIds: answer.lineIds });
        return;
      }
      onComplete(applyAppendixAnswers(lines, nextAnswers));
      return;
    }
    goTo({ kind: "flag-answer", flagIndex: flagIndex + 1 });
  };

  const handleYesNo = (yes: boolean) => {
    if (screen.kind !== "flag-answer") return;
    const step = FLAG_STEPS[screen.flagIndex];

    if (step.mode === "all") {
      if (yes) {
        afterFlagResolved(screen.flagIndex, { yes: true, lineIds: included.map((l) => l.line_id) });
      } else {
        goTo({ kind: "flag-pick", flagIndex: screen.flagIndex });
      }
      return;
    }

    if (yes) {
      goTo({ kind: "flag-pick", flagIndex: screen.flagIndex });
    } else {
      afterFlagResolved(screen.flagIndex, { yes: false, lineIds: [] });
    }
  };

  const confirmPick = () => {
    if (screen.kind !== "flag-pick") return;
    const step = FLAG_STEPS[screen.flagIndex];
    const answer: FlagAnswer = {
      yes: step.mode === "all" ? false : true,
      lineIds: [...pickSelection],
    };
    if (step.mode !== "all" && pickSelection.length === 0) return;
    afterFlagResolved(screen.flagIndex, answer);
  };

  const togglePick = (lineId: number) => {
    setPickSelection((prev) => (prev.includes(lineId) ? prev.filter((id) => id !== lineId) : [...prev, lineId]));
  };

  const confirmTemperature = () => {
    if (screen.kind !== "extra-temperature") return;
    const conditionedIndex = FLAG_STEPS.findIndex((s) => s.key === "conditioned");
    goTo({ kind: "flag-answer", flagIndex: conditionedIndex + 1 });
  };

  const confirmTbb = () => {
    onComplete(applyAppendixAnswers(lines, answers));
  };

  const currentFlag = screen.kind === "flag-answer" || screen.kind === "flag-pick" ? FLAG_STEPS[screen.flagIndex] : null;
  const detectedDgLines = included.filter((l) => l.detected_un_numbers?.length);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm text-slate-500 dark:text-slate-400">
        <span>{t("questions.progress", { current: progress.current, total: progress.total })}</span>
      </div>

      {screen.kind === "flag-answer" && currentFlag && (
        <div className={`${panelClass} p-6 space-y-6 max-w-2xl`}>
          <div>
            <div className="flex items-start gap-2">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                {t(`questions.${currentFlag.key}` as "questions.loaded")}
              </h3>
              <InfoTooltip text={helpFor(currentFlag.key)} />
            </div>
            {currentFlag.key === "dangerous_goods" && detectedDgLines.length > 0 && (
              <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">
                {t("questions.dgDetected", { lines: detectedDgLines.map((l) => `#${l.line_id}`).join(", ") })}
              </p>
            )}
          </div>
          <div className="flex gap-3">
            <button type="button" onClick={() => handleYesNo(true)} className={`${buttonPrimary} flex-1`}>
              {t("questions.yes")}
            </button>
            <button type="button" onClick={() => handleYesNo(false)} className={`${buttonSecondary} flex-1`}>
              {t("questions.no")}
            </button>
          </div>
        </div>
      )}

      {screen.kind === "flag-pick" && currentFlag && (
        <div className={`${panelClass} p-6 space-y-4 max-w-2xl`}>
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {t(`questions.${currentFlag.key}Pick` as "questions.loadedPick")}
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t("questions.selectHint")}</p>
          </div>
          <div className="space-y-2">
            {included.map((line) => (
              <label
                key={line.line_id}
                className="flex items-start gap-3 p-3 rounded-lg border border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={pickSelection.includes(line.line_id)}
                  onChange={() => togglePick(line.line_id)}
                />
                <span className="text-sm text-slate-800 dark:text-slate-200">
                  <span className="font-medium">#{line.line_id}</span> — {line.output_description || line.description}
                  {line.detected_un_numbers && line.detected_un_numbers.length > 0 && (
                    <span className="ml-2 text-xs text-amber-700 dark:text-amber-300">UN {line.detected_un_numbers.join(", ")}</span>
                  )}
                </span>
              </label>
            ))}
          </div>
          <button
            type="button"
            onClick={confirmPick}
            disabled={currentFlag.mode !== "all" && pickSelection.length === 0}
            className={`${buttonPrimary} w-full`}
          >
            {t("questions.next")}
          </button>
        </div>
      )}

      {screen.kind === "extra-temperature" && (
        <div className={`${panelClass} p-6 space-y-4 max-w-2xl`}>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("questions.temperatureTitle")}</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">{t("questions.temperatureHint")}</p>
          {screen.lineIds.map((lineId) => {
            const line = included.find((l) => l.line_id === lineId);
            if (!line) return null;
            return (
              <div key={lineId}>
                <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
                  #{lineId} — {line.output_description || line.description}
                </label>
                <input
                  className={`${inputClass} mt-1`}
                  placeholder={t("questions.temperaturePlaceholder")}
                  value={answers.temperatureByLine[lineId] ?? ""}
                  onChange={(e) =>
                    setAnswers((a) => ({
                      ...a,
                      temperatureByLine: { ...a.temperatureByLine, [lineId]: e.target.value },
                    }))
                  }
                />
              </div>
            );
          })}
          <button type="button" onClick={confirmTemperature} className={`${buttonPrimary} w-full`}>
            {t("questions.next")}
          </button>
        </div>
      )}

      {screen.kind === "extra-tbb" && (
        <div className={`${panelClass} p-6 space-y-4 max-w-2xl`}>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("questions.tbbTitle")}</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">{t("questions.tbbHint")}</p>
          {screen.lineIds.map((lineId) => {
            const line = included.find((l) => l.line_id === lineId);
            if (!line) return null;
            return (
              <div key={lineId}>
                <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
                  #{lineId} — {line.output_description || line.description}
                </label>
                <input
                  className={`${inputClass} mt-1`}
                  placeholder={t("questions.tbbPlaceholder")}
                  value={answers.tbbCategoryByLine[lineId] ?? ""}
                  onChange={(e) =>
                    setAnswers((a) => ({
                      ...a,
                      tbbCategoryByLine: { ...a.tbbCategoryByLine, [lineId]: e.target.value },
                    }))
                  }
                />
              </div>
            );
          })}
          <button type="button" onClick={confirmTbb} className={`${buttonPrimary} w-full`}>
            {t("questions.finish")}
          </button>
        </div>
      )}

      <div>
        <button type="button" onClick={goBack} className={buttonSecondary}>
          {t("wizard.back")}
        </button>
      </div>
    </div>
  );
}
