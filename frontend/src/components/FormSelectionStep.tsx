import { useTranslation } from "react-i18next";
import { DocumentDefinition, DocumentRegistry, LocalizedText } from "../api/client";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

interface Props {
  registry: DocumentRegistry;
  modality: string;
  selected: string[];
  onChange: (selected: string[]) => void;
}

const CATEGORY_KEYS: Record<string, string> = {
  internal: "forms.categoryInternal",
  prepared_transport_document: "forms.categoryPrepared",
  declaration: "forms.categoryDeclaration",
  shipping_instructions: "forms.categoryInstructions",
  generated: "forms.categoryGenerated",
};

export default function FormSelectionStep({ registry, modality, selected, onChange }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language.startsWith("en") ? "en" : "nl";
  const L = (text?: LocalizedText) => text?.[lang as "nl" | "en"] ?? "";

  const modalityDef = registry.modalities.find((m) => m.key === modality);
  const documents = (modalityDef?.documents ?? [])
    .map((key) => registry.documents.find((d) => d.key === key))
    .filter((d): d is DocumentDefinition => !!d);

  const toggle = (key: string) => {
    onChange(selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key]);
  };

  return (
    <div className="space-y-4">
      <div className={`${panelClass} p-4 sm:p-6`}>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("forms.title")}</h3>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{t("forms.intro")}</p>
      </div>

      <div className="grid gap-2 sm:gap-3 md:grid-cols-2">
        {documents.map((doc) => {
          const checked = selected.includes(doc.key);
          return (
            <label
              key={doc.key}
              className={`${panelClass} flex cursor-pointer items-start gap-3 p-4 transition ${
                checked
                  ? "border-brand-500 ring-1 ring-brand-500 dark:border-brand-500"
                  : "hover:border-slate-300 dark:hover:border-slate-700"
              }`}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggle(doc.key)}
                className="mt-1 h-4 w-4 shrink-0 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              />
              <span className="min-w-0">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-900 dark:text-slate-100">{L(doc.label)}</span>
                  {doc.output_format === "pdf" && (
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                      {t("forms.officialPdf")}
                    </span>
                  )}
                  {doc.dg_only && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                      {t("forms.dgOnly")}
                    </span>
                  )}
                </span>
                <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">
                  {t(CATEGORY_KEYS[doc.category] ?? "forms.categoryGenerated")}
                </span>
                <span className="mt-1 block text-xs text-slate-600 dark:text-slate-300">{L(doc.issue_status)}</span>
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
