import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, CatalogSyncStatus, Material, User } from "../api/client";

interface LayoutContext {
  user: User;
}

export default function MaterialsPage() {
  const { user } = useOutletContext<LayoutContext>();
  const { t } = useTranslation();
  const [items, setItems] = useState<Material[]>([]);
  const [syncStatus, setSyncStatus] = useState<CatalogSyncStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    const [materials, status] = await Promise.all([api.listMaterials(), api.catalogSyncStatus()]);
    setItems(materials);
    setSyncStatus(status);
  };

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      const status = await api.catalogSync();
      setSyncStatus(status);
      setItems(await api.listMaterials());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync mislukt");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{t("catalog.materialsTitle")}</h2>
          <p className="text-sm text-slate-500">{t("catalog.materialsIntro")}</p>
          {syncStatus?.last_run_at && (
            <p className="text-xs text-slate-400 mt-1">
              {t("catalog.lastSync")}: {new Date(syncStatus.last_run_at).toLocaleString()}
              {" · "}
              {syncStatus.material_count} {t("catalog.items")}
            </p>
          )}
        </div>
        {user.role === "admin" && (
          <button
            onClick={handleSync}
            disabled={syncing}
            className="px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
          >
            {syncing ? t("catalog.syncing") : t("catalog.syncNow")}
          </button>
        )}
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left">{t("catalog.name")}</th>
              <th className="px-4 py-3 text-left">{t("catalog.category")}</th>
              <th className="px-4 py-3 text-left">{t("catalog.density")}</th>
              <th className="px-4 py-3 text-left">{t("catalog.source")}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((m) => (
              <tr key={m.id} className="border-t">
                <td className="px-4 py-3">{m.language_labels?.nl || m.canonical_name}</td>
                <td className="px-4 py-3">{m.category}</td>
                <td className="px-4 py-3">{m.density_kg_m3}</td>
                <td className="px-4 py-3 text-xs text-slate-500">{m.source || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
