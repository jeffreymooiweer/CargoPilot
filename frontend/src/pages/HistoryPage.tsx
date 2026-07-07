import { useEffect, useState } from "react";
import { api, Job } from "../api/client";

export default function HistoryPage() {
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    api.listJobs().then(setJobs);
  }, []);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left">ID</th>
            <th className="px-4 py-3 text-left">Titel</th>
            <th className="px-4 py-3 text-left">Status</th>
            <th className="px-4 py-3 text-left">Datum</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => (
            <tr key={j.id} className="border-t">
              <td className="px-4 py-3">{j.id}</td>
              <td className="px-4 py-3">{j.title}</td>
              <td className="px-4 py-3">{j.status}</td>
              <td className="px-4 py-3">{j.created_at?.slice(0, 10)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
