import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, Job } from "../api/client";

export default function DashboardPage() {
  const { t } = useTranslation();
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    api.listJobs().then(setJobs).catch(() => setJobs([]));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">{t("nav.dashboard")}</h2>
        <Link to="/wizard" className="bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-700">
          {t("nav.new")}
        </Link>
      </div>
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Titel</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">{t("wizard.totalWeight")}</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id} className="border-t border-slate-100">
                <td className="px-4 py-3">{job.id}</td>
                <td className="px-4 py-3">{job.title}</td>
                <td className="px-4 py-3">{job.status}</td>
                <td className="px-4 py-3">{job.totals?.total_weight_kg ?? "-"} kg</td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-500">Geen jobs</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
