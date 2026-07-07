import { useEffect, useState } from "react";
import { api, Profile } from "../api/client";

export default function ProfilesPage() {
  const [items, setItems] = useState<Profile[]>([]);

  useEffect(() => {
    api.listProfiles().then(setItems);
  }, []);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left">Type</th>
            <th className="px-4 py-3 text-left">Maat</th>
            <th className="px-4 py-3 text-left">kg/m</th>
          </tr>
        </thead>
        <tbody>
          {items.map((p) => (
            <tr key={p.id} className="border-t">
              <td className="px-4 py-3">{p.profile_type}</td>
              <td className="px-4 py-3">{p.size_label}</td>
              <td className="px-4 py-3">{p.kg_per_meter}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
