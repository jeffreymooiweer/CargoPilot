/**
 * Editing one goods line, with the whole width of a dialog to do it in.
 *
 * The lines step used to be a table of input fields — thirteen columns of
 * them — and every screen narrower than a large monitor turned into a fight
 * over width: fields squeezed to thirty pixels, columns dropped to make room,
 * a detail panel to reach the ones that had been dropped. The cards behind
 * this dialog now only *show* what a line says; everything you change, you
 * change here, one field per row, at a width that is the same on a phone and
 * on a monitor.
 *
 * Changes apply as you make them, as they did in the table — the wizard
 * recalculates from the lines and there is nothing to submit. So the dialog
 * closes rather than saves, and there is no cancel to promise something this
 * step cannot deliver.
 */
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { LineItem, UnitCatalogue } from "../api/client";
import type { DraftLine } from "./ReviewLinesPanel";
import EquipmentCombobox from "./EquipmentCombobox";
import NumberInput from "./NumberInput";
import UnitSelect from "./UnitSelect";

/**
 * Cross-sections with a wall, where length-width-height does not determine the
 * weight.
 *
 * An 80x80 angle is two legs a few millimetres thick, not a solid bar of
 * 80x80 — a factor of five. For a plate, beam or plank that does not come into
 * play and the field therefore should not be there either.
 */
export const WALL_PROFILE_TYPES = new Set(["angle_profile", "square_tube", "round_tube"]);

/**
 * Round cross-sections. There the width *is* the diameter and there is no
 * height: with a diameter, a length and — for a tube — a wall thickness, the
 * weight is fixed. Asking for a height that adds nothing is only an
 * opportunity to fill in something wrong.
 */
export const ROUND_TYPES = new Set(["round_tube", "round_bar"]);

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const numberClass = `${inputClass} text-right`;
const labelClass = "text-sm font-medium text-slate-800 dark:text-slate-200";

interface Props {
  line: DraftLine;
  /** The computed line, when the wizard has calculated. Decides which fields
   *  apply at all: no cross-section, no wall thickness. */
  result: LineItem | null;
  /** 1-based position, for the heading. */
  position: number;
  catalogue: UnitCatalogue | null;
  onChange: (patch: Partial<DraftLine>) => void;
  onWeightChange?: (field: "weight_each_kg" | "weight_total_kg", value: number | null) => void;
  onClose: () => void;
}

export default function LineEditDialog({
  line,
  result,
  position,
  catalogue,
  onChange,
  onWeightChange,
  onClose,
}: Props) {
  const { t } = useTranslation();
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Focus moves into the dialog, so a keyboard user is not left behind it.
  useEffect(() => {
    panel.current?.focus();
  }, []);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  const round = ROUND_TYPES.has(result?.product_type ?? "");
  const productType = result?.product_type;
  const showWall = Boolean(productType && WALL_PROFILE_TYPES.has(productType));
  const wallMissing = result?.messages.includes("wall_thickness_missing");
  const forms = (result?.material_category && catalogue?.forms_by_category[result.material_category]) || [];

  const number = (field: "length_cm" | "width_cm" | "height_cm" | "wall_thickness_mm") =>
    (event: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ [field]: event.target.value === "" ? "" : Number(event.target.value) });

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4">
      <button
        type="button"
        aria-label={t("review.closeEdit")}
        onClick={onClose}
        className="absolute inset-0 bg-slate-900/40"
      />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={t("review.editTitle", { number: position })}
        tabIndex={-1}
        className="relative flex max-h-[92vh] w-full max-w-2xl flex-col rounded-t-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900 sm:rounded-2xl"
      >
        <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3 dark:border-slate-800 sm:px-5">
          <div className="min-w-0">
            <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {t("review.editTitle", { number: position })}
            </p>
            <p className="mt-0.5 truncate text-sm font-medium text-slate-900 dark:text-slate-100">
              {line.description.trim() || t("review.untitledLine")}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("review.closeEdit")}
            className="-mr-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
          >
            <span className="text-xl leading-none">×</span>
          </button>
        </header>

        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:px-5">
          <div>
            <label className={labelClass} htmlFor="line-description">
              {t("review.description")}
            </label>
            <div className="mt-1">
              <EquipmentCombobox
                value={line.description}
                onChange={(value) => onChange({ description: value })}
              />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className={labelClass} htmlFor="line-quantity">
                {t("review.quantity")}
              </label>
              <NumberInput
                id="line-quantity"
                inputMode="decimal"
                className={`${numberClass} mt-1`}
                value={line.quantity}
                onChange={(event) =>
                  onChange({ quantity: event.target.value === "" ? "" : Number(event.target.value) })
                }
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="line-unit">
                {t("review.unit")}
              </label>
              <div className="mt-1">
                <UnitSelect
                  value={line.unit}
                  onChange={(unit) => onChange({ unit })}
                  category={result?.material_category}
                  catalogue={catalogue}
                  aria-label={t("review.unit")}
                  className={inputClass}
                />
              </div>
            </div>
          </div>

          {/* Only for goods whose stored density describes the material itself;
              for gravel, grain or a liquid the density already describes it as
              it is carried. */}
          {forms.length > 0 && (
            <div>
              <label className={labelClass} htmlFor="line-cargo-form">
                {t("review.cargoForm")}
              </label>
              <select
                id="line-cargo-form"
                className={`${inputClass} mt-1`}
                value={line.cargo_form ?? result?.cargo_form ?? ""}
                onChange={(event) => onChange({ cargo_form: event.target.value })}
              >
                {forms.map((form) => (
                  <option key={form} value={form}>
                    {t(`forms.${form}`, form)}
                  </option>
                ))}
              </select>
            </div>
          )}

          <fieldset>
            <legend className={labelClass}>{t("review.dimensions")}</legend>
            <div className={`mt-1 grid gap-3 ${round ? "sm:grid-cols-2" : "sm:grid-cols-3"}`}>
              <Measure
                label={t("review.length_cm")}
                id="line-length"
                value={line.length_cm ?? ""}
                placeholder={result?.length_cm}
                onChange={number("length_cm")}
              />
              <Measure
                // With a round cross-section the width *is* the diameter, and
                // the field says so rather than the heading having to.
                label={round ? t("review.diameter") : t("review.width_cm")}
                id="line-width"
                value={line.width_cm ?? ""}
                placeholder={result?.width_cm}
                onChange={number("width_cm")}
              />
              {!round && (
                <Measure
                  label={t("review.height_cm")}
                  id="line-height"
                  value={line.height_cm ?? ""}
                  placeholder={result?.height_cm}
                  onChange={number("height_cm")}
                />
              )}
            </div>
          </fieldset>

          {showWall && (
            <div>
              <label className={labelClass} htmlFor="line-wall">
                {t("review.wallThickness")}
              </label>
              <NumberInput
                id="line-wall"
                step="0.1"
                inputMode="decimal"
                className={`${numberClass} mt-1 ${wallMissing ? "border-amber-400 dark:border-amber-600" : ""}`}
                value={line.wall_thickness_mm ?? ""}
                onChange={number("wall_thickness_mm")}
              />
            </div>
          )}

          {result && onWeightChange && (
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className={labelClass} htmlFor="line-weight-each">
                  {t("review.weightEach")}
                </label>
                <NumberInput
                  id="line-weight-each"
                  step="0.01"
                  inputMode="decimal"
                  className={`${numberClass} mt-1`}
                  value={result.weight_each_kg ?? ""}
                  onChange={(event) =>
                    onWeightChange(
                      "weight_each_kg",
                      event.target.value === "" ? null : Number(event.target.value),
                    )
                  }
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="line-weight-total">
                  {t("review.weightTotal")}
                </label>
                <NumberInput
                  id="line-weight-total"
                  step="0.01"
                  inputMode="decimal"
                  className={`${numberClass} mt-1`}
                  value={result.weight_total_kg ?? ""}
                  onChange={(event) =>
                    onWeightChange(
                      "weight_total_kg",
                      event.target.value === "" ? null : Number(event.target.value),
                    )
                  }
                />
              </div>
            </div>
          )}

          <label className="flex items-center gap-2.5 rounded-lg border border-slate-200 px-3 py-2.5 dark:border-slate-700">
            <input
              type="checkbox"
              checked={line.dangerous_goods ?? false}
              onChange={(event) => onChange({ dangerous_goods: event.target.checked })}
              className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
            />
            <span className={labelClass}>{t("review.dangerousGoods")}</span>
            {line.confirmed_un && (
              <span className="ml-auto rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                UN {line.confirmed_un}
              </span>
            )}
          </label>
        </div>

        <footer className="border-t border-slate-200 px-4 py-3 dark:border-slate-800 sm:px-5">
          <button
            type="button"
            onClick={onClose}
            className="min-h-[44px] w-full rounded-lg bg-brand-600 px-5 text-sm font-medium text-white hover:bg-brand-700 sm:w-auto"
          >
            {t("review.doneEditing")}
          </button>
        </footer>
      </div>
    </div>
  );
}

function Measure({
  label,
  id,
  value,
  placeholder,
  onChange,
}: {
  label: string;
  id: string;
  value: number | "";
  /** What was read out of the description; what the user fills in beats it. */
  placeholder?: number | null;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <div>
      <label className="text-xs text-slate-500 dark:text-slate-400" htmlFor={id}>
        {label}
      </label>
      <NumberInput
        id={id}
        step="0.1"
        inputMode="decimal"
        aria-label={label}
        placeholder={placeholder != null ? String(placeholder) : ""}
        className={`${numberClass} mt-0.5`}
        value={value}
        onChange={onChange}
      />
    </div>
  );
}
