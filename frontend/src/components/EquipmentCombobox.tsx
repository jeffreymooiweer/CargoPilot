import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { api, CatalogSearchHit, EquipmentItem } from "../api/client";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";

const MIN_SEARCH_LEN = 2;
const DEBOUNCE_MS = 280;

interface Props {
  value: string;
  onChange: (value: string, equipment?: EquipmentItem | null) => void;
  placeholder?: string;
}

export default function EquipmentCombobox({ value, onChange, placeholder }: Props) {
  const { t } = useTranslation();
  const [equipment, setEquipment] = useState<EquipmentItem[]>([]);
  const [results, setResults] = useState<CatalogSearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value);
  const [menuPos, setMenuPos] = useState<{ left: number; top: number; width: number; maxHeight: number } | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLUListElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    api.listEquipment().then(setEquipment).catch(() => setEquipment([]));
  }, []);

  useEffect(() => {
    setQuery(value);
  }, [value]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      const target = e.target as Node;
      if (wrapRef.current?.contains(target)) return;
      if (menuRef.current?.contains(target)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const updatePosition = useCallback(() => {
    const el = inputRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const gap = 4;
    const menuMax = 224;
    const spaceBelow = window.innerHeight - rect.bottom - gap;
    const spaceAbove = rect.top - gap;
    let top: number;
    let maxHeight: number;
    if (spaceBelow >= 160 || spaceBelow >= spaceAbove) {
      top = rect.bottom + gap;
      maxHeight = Math.max(120, Math.min(menuMax, spaceBelow));
    } else {
      maxHeight = Math.max(120, Math.min(menuMax, spaceAbove));
      top = rect.top - gap - maxHeight;
    }
    setMenuPos({ left: rect.left, top, width: rect.width, maxHeight });
  }, []);

  useEffect(() => {
    if (!open) return;
    updatePosition();
    const handler = () => updatePosition();
    window.addEventListener("resize", handler);
    window.addEventListener("scroll", handler, true);
    return () => {
      window.removeEventListener("resize", handler);
      window.removeEventListener("scroll", handler, true);
    };
  }, [open, updatePosition]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    const q = query.trim();
    if (q.length < MIN_SEARCH_LEN) {
      setResults([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    debounceRef.current = setTimeout(() => {
      api
        .catalogSearch(q)
        .then((res) => setResults(res.results))
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const browseEquipment = useMemo(() => {
    if (query.trim().length >= MIN_SEARCH_LEN) return [];
    return equipment.filter((e) => e.active !== false).slice(0, 40);
  }, [equipment, query]);

  const sourceLabel = (source: CatalogSearchHit["source"]) => t(`review.catalogSource.${source}` as "review.catalogSource.equipment");

  const pickValue = (label: string, item?: EquipmentItem | null) => {
    setQuery(label);
    onChange(label, item ?? null);
    setOpen(false);
  };

  const showCatalog = query.trim().length >= MIN_SEARCH_LEN;

  return (
    <div ref={wrapRef} className="relative">
      <input
        ref={inputRef}
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
      {open && menuPos && createPortal(
        <ul
          ref={menuRef}
          className="fixed z-50 overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900"
          style={{ left: menuPos.left, top: menuPos.top, width: menuPos.width, maxHeight: menuPos.maxHeight }}
        >
          <li>
            <button
              type="button"
              className="w-full px-3 py-2.5 text-left text-sm text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
              onClick={() => pickValue(query)}
            >
              {t("review.customDescription")}
            </button>
          </li>

          {showCatalog && loading && (
            <li className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">{t("review.catalogSearching")}</li>
          )}

          {showCatalog &&
            !loading &&
            results.map((hit) => (
              <li key={hit.id}>
                <button
                  type="button"
                  className="w-full px-3 py-2.5 text-left hover:bg-brand-50 dark:hover:bg-brand-950/40 border-t border-slate-100 dark:border-slate-800"
                  onClick={() => pickValue(hit.value)}
                >
                  <span className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{hit.label}</span>
                    <span className="text-[10px] uppercase tracking-wide text-slate-400 dark:text-slate-500">{sourceLabel(hit.source)}</span>
                  </span>
                  {hit.sublabel && (
                    <span className="block text-xs text-slate-500 dark:text-slate-400 truncate">{hit.sublabel}</span>
                  )}
                </button>
              </li>
            ))}

          {showCatalog && !loading && results.length === 0 && (
            <li className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">{t("review.noCatalogMatch")}</li>
          )}

          {!showCatalog &&
            browseEquipment.map((item) => {
              const label = item.sap_code || item.specifications;
              const sub = item.sap_code ? item.specifications : null;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className="w-full px-3 py-2.5 text-left hover:bg-brand-50 dark:hover:bg-brand-950/40 border-t border-slate-100 dark:border-slate-800"
                    onClick={() => pickValue(label, item)}
                  >
                    <span className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{label}</span>
                      <span className="text-[10px] uppercase tracking-wide text-slate-400 dark:text-slate-500">
                        {sourceLabel("equipment")}
                      </span>
                    </span>
                    {sub && <span className="block text-xs text-slate-500 dark:text-slate-400 truncate">{sub}</span>}
                    <span className="block text-xs text-slate-400 dark:text-slate-500">{item.weight_kg} kg</span>
                  </button>
                </li>
              );
            })}
        </ul>,
        document.body,
      )}
    </div>
  );
}
