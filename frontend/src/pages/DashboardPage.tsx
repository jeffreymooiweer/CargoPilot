import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function DashboardPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-8">
        <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">{t("dashboard.welcome")}</h2>
        <p className="mt-3 text-slate-600 dark:text-slate-300 max-w-2xl">{t("dashboard.intro")}</p>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-2xl">{t("dashboard.privacy")}</p>
        <Link
          to="/wizard"
          className="inline-flex mt-6 bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-lg text-sm font-medium"
        >
          {t("nav.new")}
        </Link>
      </div>
    </div>
  );
}
