import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, EquipmentItem } from "../api/client";

const inputClass =
  "border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

const emptyForm = (): EquipmentItem => ({
  sap_code: "",
  specifications: "",
  length_cm: null,
  width_cm: null,
  height_cm: null,
  weight_kg: 0,
  aliases: [],
  language_labels: {},
  active: true,
});

export default function MaterieelPage() {
  const { t } = useTranslation();
  const [items, setItems] = useState<EquipmentItem[]>([]);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<EquipmentItem>(emptyForm());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const load = () => api.listEquipment().then(setItems).catch((e) => setError(String(e)));
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => {
      const hay = [
        item.sap_code,
        item.specifications,
        ...(item.aliases || []),
        ...Object.values(item.language_labels || {}),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [items, search]);

  const resetForm = () => {
    setForm(emptyForm());
    setEditingId(null);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const payload = {
      ...form,
      sap_code: form.sap_code || null,
      aliases: (form.aliases as string[] | undefined) || [],
      language_labels: form.language_labels || {},
      weight_kg: Number(form.weight_kg),
      length_cm: form.length_cm ? Number(form.length_cm) : null,
      width_cm: form.width_cm ? Number(form.width_cm) : null,
      height_cm: form.height_cm ? Number(form.height_cm) : null,
    };
    try {
      if (editingId) {
        await api.updateEquipment(editingId, payload);
      } else {
        await api.createEquipment(payload);
      }
      resetForm();
      load();
    } catch (err) {
      setError(String(err));
    }
  };

  const startEdit = (item: EquipmentItem) => {
    setEditingId(item.id!);
    setForm({ ...item, aliases: item.aliases || [] });
  };

  const remove = async (id: number) => {
    if (!confirm(t("materieel.confirmDelete"))) return;
    await api.deleteEquipment(id);
    if (editingId === id) resetForm();
    load();
  };

  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-600 dark:text-slate-400">{t("materieel.intro")}</p>

      <form onSubmit={submit} className={`${panelClass} p-6 grid md:grid-cols-2 gap-3`}>
        <h3 className="md:col-span-2 font-semibold text-slate-900 dark:text-slate-100">
          {editingId ? t("materieel.edit") : t("materieel.add")}
        </h3>
        <input className={inputClass} placeholder={t("materieel.sapCode")} value={form.sap_code ?? ""} onChange={(e) => setForm({ ...form, sap_code: e.target.value })} />
        <input className={inputClass} required placeholder={t("materieel.specifications")} value={form.specifications} onChange={(e) => setForm({ ...form, specifications: e.target.value })} />
        <input className={inputClass} type="number" step="0.1" placeholder={t("materieel.length")} value={form.length_cm ?? ""} onChange={(e) => setForm({ ...form, length_cm: e.target.value ? Number(e.target.value) : null })} />
        <input className={inputClass} type="number" step="0.1" placeholder={t("materieel.width")} value={form.width_cm ?? ""} onChange={(e) => setForm({ ...form, width_cm: e.target.value ? Number(e.target.value) : null })} />
        <input className={inputClass} type="number" step="0.1" placeholder={t("materieel.height")} value={form.height_cm ?? ""} onChange={(e) => setForm({ ...form, height_cm: e.target.value ? Number(e.target.value) : null })} />
        <input className={inputClass} type="number" step="0.1" required placeholder={t("materieel.weight")} value={form.weight_kg || ""} onChange={(e) => setForm({ ...form, weight_kg: Number(e.target.value) })} />
        <input
          className={`${inputClass} md:col-span-2`}
          placeholder={t("materieel.aliases")}
          value={(form.aliases || []).join(", ")}
          onChange={(e) => setForm({ ...form, aliases: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
        />
        <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
          <input type="checkbox" checked={form.active !== false} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
          {t("materieel.active")}
        </label>
        <div className="flex gap-2 md:col-span-2">
          <button type="submit" className="bg-brand-600 text-white rounded-lg px-4 py-2 text-sm">
            {editingId ? t("materieel.save") : t("materieel.create")}
          </button>
          {editingId && (
            <button type="button" onClick={resetForm} className="border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm">
              {t("materieel.cancel")}
            </button>
          )}
        </div>
      </form>

      <div className={`${panelClass} p-4`}>
        <input
          className={`${inputClass} w-full max-w-md`}
          placeholder={t("materieel.search")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
          {t("materieel.count", { count: filtered.length, total: items.length })}
        </p>
      </div>

      <div className={`${panelClass} overflow-x-auto max-h-[32rem] overflow-y-auto`}>
        <table className="w-full text-sm text-slate-800 dark:text-slate-200">
          <thead className="bg-slate-50 dark:bg-slate-800/80 sticky top-0">
            <tr>
              <th className="px-3 py-2 text-left">{t("materieel.sapCode")}</th>
              <th className="px-3 py-2 text-left">{t("materieel.specifications")}</th>
              <th className="px-3 py-2 text-left">L×B×H</th>
              <th className="px-3 py-2 text-left">{t("materieel.weight")}</th>
              <th className="px-3 py-2 text-left"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.id} className="border-t border-slate-100 dark:border-slate-800">
                <td className="px-3 py-2 whitespace-nowrap">{item.sap_code || "—"}</td>
                <td className="px-3 py-2">{item.specifications}</td>
                <td className="px-3 py-2 whitespace-nowrap">
                  {[item.length_cm, item.width_cm, item.height_cm].filter((v) => v != null).join(" × ") || "—"}
                </td>
                <td className="px-3 py-2 whitespace-nowrap">{item.weight_kg} kg</td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <button type="button" className="text-brand-600 dark:text-brand-300 hover:underline mr-3" onClick={() => startEdit(item)}>
                    {t("materieel.edit")}
                  </button>
                  <button type="button" className="text-red-600 dark:text-red-400 hover:underline" onClick={() => remove(item.id!)}>
                    {t("materieel.delete")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {error && <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>}
    </div>
  );
}
