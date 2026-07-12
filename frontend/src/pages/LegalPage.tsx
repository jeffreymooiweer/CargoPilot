import { useTranslation } from "react-i18next";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

export default function LegalPage() {
  const { t } = useTranslation();
  const sections = t("legal.sections", { returnObjects: true }) as { heading: string; body: string }[];

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className={`${panelClass} p-5 sm:p-8`}>
        <h2 className="text-xl sm:text-2xl font-semibold text-slate-900 dark:text-slate-100">{t("legal.title")}</h2>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{t("legal.updated")}</p>
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-slate-700 dark:text-slate-300">{t("legal.intro")}</p>
      </div>

      <div className={`${panelClass} divide-y divide-slate-100 dark:divide-slate-800`}>
        {Array.isArray(sections) &&
          sections.map((section, i) => (
            <section key={i} className="p-5 sm:p-6">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">{section.heading}</h3>
              <p className="mt-2 max-w-3xl whitespace-pre-line text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                {section.body}
              </p>
            </section>
          ))}
      </div>
    </div>
  );
}
