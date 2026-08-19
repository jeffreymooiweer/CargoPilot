import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  DocumentDefinition,
  DocumentField,
  DocumentRegistry,
  DocumentSection,
  FieldStatus,
  LocalizedText,
} from "../api/client";
import { documentLanguage, localised } from "../i18n/language";
import CarrierConfirmationBox from "./CarrierConfirmationBox";
import {
  AddressTextarea,
  LOCATION_FIELD_KEYS,
  LocationInput,
  MODALITY_LOCATION_TYPES,
} from "./GeoInputs";
import InfoTooltip from "./InfoTooltip";
import SignaturePad from "./SignaturePad";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm min-h-[40px]";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const buttonSecondary =
  "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 min-h-[44px] text-sm";
const buttonPrimary =
  "bg-brand-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";

const STATUS_BADGES: Partial<Record<FieldStatus, { key: string; className: string }>> = {
  CARRIER_PROVIDED: {
    key: "docfields.carrierProvided",
    className: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  },
  OPERATIONAL: {
    key: "docfields.operational",
    className: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  },
  SIGNATURE_REQUIRED: {
    key: "docfields.signatureRequired",
    className: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  },
};

export function conditionMet(condition: string | undefined, values: Record<string, string>): boolean {
  if (!condition) return true;
  const [field, expected] = condition.split("=");
  return (values[field?.trim() ?? ""] ?? "").trim() === (expected ?? "").trim();
}

export function resolveSections(doc: DocumentDefinition, registry: DocumentRegistry): DocumentSection[] {
  const shared = new Map(registry.shared_sections.map((s) => [s.key, s]));
  return doc.sections
    .map((section) => (section.ref ? shared.get(section.ref) : section))
    .filter((s): s is DocumentSection => !!s);
}

interface Props {
  registry: DocumentRegistry;
  documents: DocumentDefinition[];
  values: Record<string, string>;
  onChange: (values: Record<string, string>) => void;
  autoValues?: Record<string, string>;
  modality?: string;
  onBack?: () => void;
  onDone?: () => void;
  signature?: string | null;
  onSignatureChange?: (dataUrl: string | null) => void;
}

type SubStep = { kind: "shared" } | { kind: "doc"; doc: DocumentDefinition; sections: DocumentSection[] };

export default function DocumentFieldsStep({
  registry,
  documents,
  values,
  onChange,
  autoValues,
  modality,
  onBack,
  onDone,
  signature,
  onSignatureChange,
}: Props) {
  const { t, i18n } = useTranslation();
  const lang = documentLanguage(i18n.language);
  const L = (text?: LocalizedText) => localised(text, lang);
  const [subIndex, setSubIndex] = useState(0);

  const setValue = (key: string, value: string) => onChange({ ...values, [key]: value });

  const { sharedSections, docSections, docsWithoutOwnFields } = useMemo(() => {
    const sharedKeys: string[] = [];
    for (const doc of documents) {
      for (const section of doc.sections) {
        if (section.ref && !sharedKeys.includes(section.ref)) sharedKeys.push(section.ref);
      }
    }
    const shared = registry.shared_sections.filter((s) => s.key && sharedKeys.includes(s.key));
    const perDoc = documents
      .map((doc) => ({
        doc,
        sections: doc.sections.filter((s): s is DocumentSection => !s.ref && !!s.fields?.length),
      }))
      .filter((entry) => entry.sections.length > 0);
    const covered = documents.filter((doc) => !perDoc.some((entry) => entry.doc.key === doc.key));
    return { sharedSections: shared, docSections: perDoc, docsWithoutOwnFields: covered };
  }, [documents, registry]);

  const subSteps: SubStep[] = useMemo(
    () => [{ kind: "shared" as const }, ...docSections.map((entry) => ({ kind: "doc" as const, ...entry }))],
    [docSections],
  );
  const current = subSteps[Math.min(subIndex, subSteps.length - 1)];

  const missingRequired = (sections: DocumentSection[]): number => {
    let count = 0;
    for (const section of sections) {
      for (const field of section.fields ?? []) {
        if (field.status !== "USER_REQUIRED") continue;
        if (field.condition && !conditionMet(field.condition, values)) continue;
        const autoValue = field.auto_from ? autoValues?.[field.auto_from] : undefined;
        if (!(values[field.key] ?? autoValue ?? "").trim()) count += 1;
      }
    }
    return count;
  };

  const subStepLabel = (step: SubStep) => (step.kind === "shared" ? t("docfields.sharedShort") : L(step.doc.label));
  const subStepMissing = (step: SubStep) =>
    step.kind === "shared" ? missingRequired(sharedSections) : missingRequired(step.sections);

  const goNext = () => {
    if (subIndex < subSteps.length - 1) setSubIndex(subIndex + 1);
    else onDone?.();
  };
  const goBack = () => {
    if (subIndex > 0) setSubIndex(subIndex - 1);
    else onBack?.();
  };

  const renderField = (field: DocumentField) => {
    if (field.status === "CONDITIONAL" && field.condition && !conditionMet(field.condition, values)) {
      return null;
    }
    const badge = STATUS_BADGES[field.status];
    const autoValue = field.auto_from ? autoValues?.[field.auto_from] : undefined;
    const value = values[field.key] ?? (autoValue !== undefined && values[field.key] === undefined ? autoValue : "");
    const required = field.status === "USER_REQUIRED";
    const isAddress = field.type === "textarea" && field.key.endsWith("_address");
    const isLocation = field.type === "text" && LOCATION_FIELD_KEYS.has(field.key);
    const locationTypes = MODALITY_LOCATION_TYPES[modality ?? ""] ?? ["airport", "port", "station"];

    return (
      <div key={field.key} className={field.type === "textarea" ? "md:col-span-2" : ""}>
        <div className="flex flex-wrap items-center gap-1.5">
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {L(field.label)}
            {required && <span className="text-red-500"> *</span>}
          </label>
          {field.help && <InfoTooltip text={L(field.help)} />}
          {badge && (
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${badge.className}`}>
              {t(badge.key)}
            </span>
          )}
        </div>
        {isAddress ? (
          <div className="mt-1">
            <AddressTextarea
              value={value}
              onChange={(v) => setValue(field.key, v)}
              textareaClassName={`${inputClass} min-h-[64px]`}
            />
          </div>
        ) : field.type === "textarea" ? (
          <textarea
            className={`${inputClass} mt-1 min-h-[64px]`}
            value={value}
            onChange={(e) => setValue(field.key, e.target.value)}
          />
        ) : isLocation ? (
          <div className="mt-1">
            <LocationInput
              value={value}
              onChange={(v) => setValue(field.key, v)}
              types={locationTypes}
              includeAddresses={modality === "road" || modality === "multimodal"}
            />
          </div>
        ) : field.type === "select" ? (
          <select className={`${inputClass} mt-1`} value={value} onChange={(e) => setValue(field.key, e.target.value)}>
            <option value="">{t("docfields.choose")}</option>
            {(field.options ?? []).map((option) => (
              <option key={option.value} value={option.value}>
                {L(option.label)}
              </option>
            ))}
          </select>
        ) : field.type === "checkbox" ? (
          <label className="mt-1.5 flex min-h-[40px] items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={value === "true"}
              onChange={(e) => setValue(field.key, e.target.checked ? "true" : "")}
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            />
            {field.status === "SIGNATURE_REQUIRED" ? t("docfields.confirmExplicit") : t("docfields.yes")}
          </label>
        ) : (
          <input
            type={field.type === "number" ? "number" : field.type === "date" ? "date" : "text"}
            step={field.type === "number" ? "0.01" : undefined}
            className={`${inputClass} mt-1`}
            value={value}
            onChange={(e) => setValue(field.key, e.target.value)}
          />
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <div className={`${panelClass} p-4 sm:p-6`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            {current.kind === "shared"
              ? t("docfields.sharedTitle")
              : t("docfields.formStep", {
                  index: subIndex,
                  total: subSteps.length - 1,
                  name: L(current.doc.label),
                })}
          </h3>
        </div>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          {current.kind === "shared" ? t("docfields.sharedIntro") : t("docfields.formIntro")}
        </p>
        {subSteps.length > 1 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {subSteps.map((step, index) => {
              const active = index === subIndex;
              const missing = subStepMissing(step);
              return (
                <button
                  key={step.kind === "shared" ? "shared" : step.doc.key}
                  type="button"
                  onClick={() => setSubIndex(index)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition ${
                    active
                      ? "border-brand-600 bg-brand-600 text-white"
                      : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      missing === 0 ? "bg-emerald-500" : active ? "bg-white/70" : "bg-amber-400"
                    }`}
                  />
                  {subStepLabel(step)}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {current.kind === "shared" && (
        <>
          {/* Offered where the references live: pasting the carrier's booking
              confirmation fills the still-empty reference fields. */}
          {sharedSections.some((section) => section.key === "references") && (
            <CarrierConfirmationBox values={values} onChange={onChange} />
          )}
          {sharedSections.map((section) => (
            <section key={section.key} className={`${panelClass} p-4 sm:p-6`}>
              <h4 className="font-semibold text-slate-900 dark:text-slate-100">{L(section.label)}</h4>
              <div className="mt-3 grid gap-3 md:grid-cols-2">{(section.fields ?? []).map(renderField)}</div>
            </section>
          ))}
          {onSignatureChange && <SignaturePad value={signature ?? null} onChange={onSignatureChange} />}
          {docsWithoutOwnFields.length > 0 && (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t("docfields.coveredByShared", {
                forms: docsWithoutOwnFields.map((doc) => L(doc.label)).join(", "),
              })}
            </p>
          )}
        </>
      )}

      {current.kind === "doc" && (
        <section className={`${panelClass} p-4 sm:p-6`}>
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-semibold text-slate-900 dark:text-slate-100">{L(current.doc.label)}</h4>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {L(current.doc.issue_status)}
            </span>
          </div>
          {current.sections.map((section) => (
            <div key={section.key} className="mt-3">
              <div className="mt-2 grid gap-3 md:grid-cols-2">{(section.fields ?? []).map(renderField)}</div>
            </div>
          ))}
          {current.doc.signature_note && (
            <p className="mt-4 text-xs italic text-slate-500 dark:text-slate-400">{L(current.doc.signature_note)}</p>
          )}
        </section>
      )}

      <div className="flex flex-col gap-2 sm:flex-row">
        <button type="button" onClick={goBack} className={buttonSecondary}>
          {t("wizard.back")}
        </button>
        <button type="button" onClick={goNext} className={`${buttonPrimary} sm:ml-auto`}>
          {subIndex < subSteps.length - 1 ? t("wizard.next") : t("wizard.toExport")}
        </button>
      </div>
    </div>
  );
}
