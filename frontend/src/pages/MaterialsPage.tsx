import { useEffect, useState } from "react";
import { api, Material } from "../api/client";

export default function MaterialsPage() {
  const [items, setItems] = useState<Material[]>([]);

  useEffect(() => {
    api.listMaterials().then(setItems);
  }, []);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left">Naam</th>
            <th className="px-4 py-3 text-left">Categorie</th>
            <th className="px-4 py-3 text-left">Dichtheid kg/m³</th>
          </tr>
        </thead>
        <tbody>
          {items.map((m) => (
            <tr key={m.id} className="border-t">
              <td className="px-4 py-3">{m.canonical_name}</td>
              <td className="px-4 py-3">{m.category}</td>
              <td className="px-4 py-3">{m.density_kg_m3}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
