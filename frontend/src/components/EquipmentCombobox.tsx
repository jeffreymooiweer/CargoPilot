import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, EquipmentItem } from "../api/client";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";

interface Props {
  value: string;
  onChange: (value: string, equipment?: EquipmentItem | null) => void;
  placeholder?: string;
}

export default function EquipmentCombobox({ value, onChange, placeholder }: Props) {
  const { t } = useTranslation();
  const [equipment, setEquipment] = useState<EquipmentItem[]>([]);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listEquipment().then(setEquipment).catch(() => setEquipment([]));
  }, []);

  useEffect(() => {
    setQuery(value);
  }, [value]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return equipment.filter((e) => e.active !== false).slice(0, 40);
    return equipment
      .filter((e) => e.active !== false)
      .filter((item) => {
        const hay = [item.sap_code, item.specifications, ...(item.aliases || []), ...Object.values(item.language_labels || {})]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return hay.includes(q);
      })
      .slice(0, 40);
  }, [equipment, query]);

  const pick = (item: EquipmentItem | null, label: string) => {
    setQuery(label);
    onChange(label, item);
    setOpen(false);
  };

  return (
    <div ref={wrapRef} className="relative">
      <input
        className={inputClass}
        value={query}
        placeholder={placeholder || t("review.descriptionPlaceholder")}
        onChange={(e) => {
          setQuery(e.target.value);
          onChange(e.target.value, null);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        autoComplete="off"
      />
      {open && (
        <ul className="absolute z-40 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900">
          <li>
            <button
              type="button"
              className="w-full px-3 py-2.5 text-left text-sm text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
              onClick={() => pick(null, query)}
            >
              {t("review.customDescription")}
            </button>
          </li>
          {filtered.map((item) => {
            const label = item.sap_code || item.specifications;
            const sub = item.sap_code ? item.specifications : null;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  className="w-full px-3 py-2.5 text-left hover:bg-brand-50 dark:hover:bg-brand-950/40 border-t border-slate-100 dark:border-slate-800"
                  onClick={() => pick(item, label)}
                >
                  <span className="block text-sm font-medium text-slate-900 dark:text-slate-100">{label}</span>
                  {sub && <span className="block text-xs text-slate-500 dark:text-slate-400 truncate">{sub}</span>}
                  <span className="block text-xs text-slate-400 dark:text-slate-500">{item.weight_kg} kg</span>
                </button>
              </li>
            );
          })}
          {filtered.length === 0 && (
            <li className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">{t("review.noEquipmentMatch")}</li>
          )}
        </ul>
      )}
    </div>
  );
}
