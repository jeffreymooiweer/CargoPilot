import { useTranslation } from "react-i18next";
import { DocumentDefinition, DocumentRegistry, LocalizedText } from "../api/client";
import { documentLanguage, localised } from "../i18n/language";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

/** Which documents this shipment calls for, in three honest groups.
 *
 * *Required* is reserved for what a read provision carries: with dangerous
 * goods on board, 5.4.1 requires a transport document with the prescribed
 * particulars, and the registry names which document that is per modality.
 * Everything else the app can make is *recommended* (the DG support papers,
 * or the modality's customary transport document) or *possible* — a
 * commercial document is the consignor's choice, and calling it required
 * would be claiming a provision nobody read.
 */
export function buildAdvice(
  registry: DocumentRegistry,
  modality: string,
  needsDg: boolean,
): { required: string[]; recommended: string[]; possible: string[]; preselected: string[] } {
  const modalityDef = registry.modalities.find((m) => m.key === modality);
  const docs = modalityDef?.documents ?? [];
  const dgDoc = registry.dg_transport_documents?.[modality];
  const fallback = registry.modality_defaults?.[modality];
  const required = needsDg && dgDoc && docs.includes(dgDoc) ? [dgDoc] : [];
  const recommended = docs.filter((key) => {
    if (required.includes(key)) return false;
    const doc = registry.documents.find((d) => d.key === key);
    if (!doc) return false;
    if (needsDg && doc.dg_only) return true;
    return key === fallback;
  });
  const possible = docs.filter((key) => !required.includes(key) && !recommended.includes(key));
  return { required, recommended, possible, preselected: [...required, ...recommended] };
}

interface Props {
  registry: DocumentRegistry;
  modality: string;
  needsDg: boolean;
  selected: string[];
  onChange: (selected: string[]) => void;
}

export default function DocumentAdvicePanel({ registry, modality, needsDg, selected, onChange }: Props) {
  const { t, i18n } = useTranslation();
  const lang = documentLanguage(i18n.language);
  const L = (text?: LocalizedText) => localised(text, lang);
  const advice = buildAdvice(registry, modality, needsDg);

  const toggle = (key: string) => {
    onChange(selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key]);
  };

  const groups: { keys: string[]; label: string; note?: string }[] = [
    { keys: advice.required, label: t("advice.required"), note: t("advice.requiredNote") },
    { keys: advice.recommended, label: t("advice.recommended") },
    { keys: advice.possible, label: t("advice.possible") },
  ];

  const docFor = (key: string): DocumentDefinition | undefined =>
    registry.documents.find((d) => d.key === key);

  return (
    <div className={`${panelClass} space-y-3 p-4 sm:p-6`}>
      <div>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("advice.title")}</h3>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{t("advice.intro")}</p>
      </div>
      {groups.map(
        (group) =>
          group.keys.length > 0 && (
            <div key={group.label}>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {group.label}
              </p>
              {group.note && (
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{group.note}</p>
              )}
              <div className="mt-1.5 grid gap-1.5 md:grid-cols-2">
                {group.keys.map((key) => {
                  const doc = docFor(key);
                  if (!doc) return null;
                  const checked = selected.includes(key);
                  return (
                    <label
                      key={key}
                      className={`flex cursor-pointer items-start gap-2.5 rounded-xl border p-2.5 transition ${
                        checked
                          ? "border-brand-500 ring-1 ring-brand-500 dark:border-brand-500"
                          : "border-slate-200 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(key)}
                        className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                      />
                      <span className="min-w-0">
                        <span className="block text-sm font-medium text-slate-900 dark:text-slate-100">
                          {L(doc.label)}
                        </span>
                        <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">
                          {L(doc.issue_status)}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          ),
      )}
    </div>
  );
}
