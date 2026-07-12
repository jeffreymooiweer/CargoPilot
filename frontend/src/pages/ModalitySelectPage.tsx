import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

export const MODALITIES = ["road", "rail", "sea", "inland", "air", "multimodal"] as const;
export type ModalityKey = (typeof MODALITIES)[number];

export function isModalityKey(value: string | undefined): value is ModalityKey {
  return !!value && (MODALITIES as readonly string[]).includes(value);
}

export default function ModalitySelectPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div className="space-y-5 sm:space-y-6">
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-8">
        <h2 className="text-xl sm:text-2xl font-semibold text-slate-900 dark:text-slate-100">
          {t("modality.title")}
        </h2>
        <p className="mt-2 text-sm sm:text-base text-slate-600 dark:text-slate-300 max-w-2xl">
          {t("modality.intro")}
        </p>
        <p className="mt-2 text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-2xl">
          {t("dashboard.privacy")}
        </p>
      </div>

      <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {MODALITIES.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => navigate(`/wizard/${key}`)}
            className="group relative overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-left shadow-sm transition hover:border-brand-400 hover:shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:hover:border-brand-500"
          >
            <div className="aspect-[3/1] w-full overflow-hidden">
              <img
                src={`/modalities/${key}-light.webp`}
                alt=""
                aria-hidden="true"
                loading="lazy"
                className="h-full w-full object-cover transition duration-300 group-hover:scale-105 dark:hidden"
              />
              <img
                src={`/modalities/${key}-dark.webp`}
                alt=""
                aria-hidden="true"
                loading="lazy"
                className="hidden h-full w-full object-cover transition duration-300 group-hover:scale-105 dark:block"
              />
            </div>
            <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-5 sm:py-4">
              <div className="min-w-0">
                <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                  {t(`modality.${key}`)}
                </h3>
                <p className="mt-0.5 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                  {t(`modality.${key}Desc`)}
                </p>
              </div>
              <span
                aria-hidden="true"
                className="shrink-0 text-slate-300 transition group-hover:translate-x-1 group-hover:text-brand-500 dark:text-slate-600"
              >
                <svg className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
