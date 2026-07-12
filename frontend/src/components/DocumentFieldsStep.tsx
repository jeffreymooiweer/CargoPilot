import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  DocumentDefinition,
  DocumentField,
  DocumentRegistry,
  DocumentSection,
  FieldStatus,
  LocalizedText,
} from "../api/client";
import InfoTooltip from "./InfoTooltip";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm min-h-[40px]";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

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
}

export default function DocumentFieldsStep({ registry, documents, values, onChange, autoValues }: Props) {
  const { t, i18n } = useTranslation();
  const lang = (i18n.language.startsWith("en") ? "en" : "nl") as "nl" | "en";
  const L = (text?: LocalizedText) => text?.[lang] ?? "";

  const setValue = (key: string, value: string) => onChange({ ...values, [key]: value });

  const { sharedSections, docSections } = useMemo(() => {
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
    return { sharedSections: shared, docSections: perDoc };
  }, [documents, registry]);

  const renderField = (field: DocumentField) => {
    if (field.status === "CONDITIONAL" && field.condition && !conditionMet(field.condition, values)) {
      return null;
    }
    const badge = STATUS_BADGES[field.status];
    const autoValue = field.auto_from ? autoValues?.[field.auto_from] : undefined;
    const value = values[field.key] ?? (autoValue !== undefined && values[field.key] === undefined ? autoValue : "");
    const required = field.status === "USER_REQUIRED";

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
        {field.type === "textarea" ? (
          <textarea
            className={`${inputClass} mt-1 min-h-[64px]`}
            value={value}
            onChange={(e) => setValue(field.key, e.target.value)}
          />
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
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("docfields.title")}</h3>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{t("docfields.intro")}</p>
      </div>

      {sharedSections.map((section) => (
        <section key={section.key} className={`${panelClass} p-4 sm:p-6`}>
          <h4 className="font-semibold text-slate-900 dark:text-slate-100">{L(section.label)}</h4>
          <div className="mt-3 grid gap-3 md:grid-cols-2">{(section.fields ?? []).map(renderField)}</div>
        </section>
      ))}

      {docSections.map(({ doc, sections }) => (
        <section key={doc.key} className={`${panelClass} p-4 sm:p-6`}>
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-semibold text-slate-900 dark:text-slate-100">{L(doc.label)}</h4>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {L(doc.issue_status)}
            </span>
          </div>
          {sections.map((section) => (
            <div key={section.key} className="mt-3">
              <div className="mt-2 grid gap-3 md:grid-cols-2">{(section.fields ?? []).map(renderField)}</div>
            </div>
          ))}
          {doc.signature_note && (
            <p className="mt-4 text-xs italic text-slate-500 dark:text-slate-400">{L(doc.signature_note)}</p>
          )}
        </section>
      ))}
    </div>
  );
}
