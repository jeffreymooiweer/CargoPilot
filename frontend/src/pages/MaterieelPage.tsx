import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, EquipmentItem } from "../api/client";

const inputClass =
  "border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

function PencilIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} aria-hidden>
      <path d="M13.5 3.5l3 3L7 16l-3.5.5L4 13l9.5-9.5Z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} aria-hidden>
      <rect x="7" y="7" width="9" height="9" rx="2" />
      <path d="M13 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} aria-hidden>
      <path d="M4 6h12M8 6V4.5A1.5 1.5 0 0 1 9.5 3h1A1.5 1.5 0 0 1 12 4.5V6m-6 0v9a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CardAction({
  label,
  onClick,
  icon,
  danger,
}: {
  label: string;
  onClick: () => void;
  icon: React.ReactNode;
  danger?: boolean;
}) {
  const tone = danger
    ? "text-slate-500 hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-950/40 dark:hover:text-red-400"
    : "text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100";
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${tone}`}
    >
      {icon}
    </button>
  );
}

function CardRow({ label, children }: { label: string; children: React.ReactNode }) {
  const rowRef = useRef<HTMLDivElement>(null);
  const labelProbeRef = useRef<HTMLSpanElement>(null);
  const valueProbeRef = useRef<HTMLSpanElement>(null);
  const [stacked, setStacked] = useState(false);

  useLayoutEffect(() => {
    const row = rowRef.current;
    const labelProbe = labelProbeRef.current;
    const valueProbe = valueProbeRef.current;
    if (!row || !labelProbe || !valueProbe) return;
    const measure = () => {
      const gap = 16;
      const available = row.clientWidth - labelProbe.offsetWidth - gap;
      setStacked(valueProbe.offsetWidth > available);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(row);
    return () => observer.disconnect();
  }, [label, children]);

  return (
    <div className="border-t border-slate-100 px-4 py-2.5 text-sm first:border-t-0 dark:border-slate-800">
      <div ref={rowRef} className="relative">
        {/* Onzichtbare probes om de natuurlijke breedte op één regel te meten */}
        <span ref={labelProbeRef} aria-hidden className="pointer-events-none invisible absolute left-0 top-0 whitespace-nowrap">
          {label}
        </span>
        <span ref={valueProbeRef} aria-hidden className="pointer-events-none invisible absolute left-0 top-0 whitespace-nowrap font-medium">
          {children}
        </span>
        {stacked ? (
          <div className="flex flex-col gap-1">
            <span className="text-slate-500 dark:text-slate-400">{label}</span>
            <span className="break-words text-right font-medium text-slate-900 dark:text-slate-100">{children}</span>
          </div>
        ) : (
          <div className="flex items-start justify-between gap-4">
            <span className="shrink-0 text-slate-500 dark:text-slate-400">{label}</span>
            <span className="text-right font-medium text-slate-900 dark:text-slate-100">{children}</span>
          </div>
        )}
      </div>
    </div>
  );
}

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
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const duplicate = (item: EquipmentItem) => {
    setEditingId(null);
    setForm({ ...emptyForm(), ...item, id: undefined, aliases: item.aliases || [] });
    window.scrollTo({ top: 0, behavior: "smooth" });
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

      {/* Mobiel: cards */}
      <div className="space-y-3 md:hidden">
        {filtered.map((item) => (
          <div key={item.id} className={`${panelClass} shadow-sm`}>
            <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
              <span className="min-w-0 truncate font-semibold text-slate-900 dark:text-slate-100">
                {item.sap_code || item.specifications}
              </span>
              {item.active === false && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                  {t("materieel.active")}: {t("questions.no")}
                </span>
              )}
              <div className="ml-auto flex items-center gap-0.5">
                <CardAction label={t("materieel.edit")} onClick={() => startEdit(item)} icon={<PencilIcon />} />
                <CardAction label={t("materieel.duplicate")} onClick={() => duplicate(item)} icon={<CopyIcon />} />
                <CardAction label={t("materieel.delete")} onClick={() => remove(item.id!)} icon={<TrashIcon />} danger />
              </div>
            </div>
            <div>
              <CardRow label={t("materieel.specifications")}>{item.specifications}</CardRow>
              {item.sap_code && <CardRow label={t("materieel.sapCode")}>{item.sap_code}</CardRow>}
              <CardRow label={t("materieel.dimensions")}>
                {[item.length_cm, item.width_cm, item.height_cm].filter((v) => v != null).join(" × ") || "—"}
              </CardRow>
              <CardRow label={t("materieel.weight")}>{item.weight_kg} kg</CardRow>
              {item.aliases && item.aliases.length > 0 && (
                <CardRow label={t("materieel.aliases")}>{item.aliases.join(", ")}</CardRow>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Desktop: tabel */}
      <div className={`${panelClass} hidden overflow-x-auto max-h-[32rem] overflow-y-auto md:block`}>
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
