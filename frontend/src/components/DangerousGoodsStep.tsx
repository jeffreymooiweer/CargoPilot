import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, DgEntry, DgInstructions, DgPackaging, DgProduct, DgUnEntry, LineItem } from "../api/client";
import InfoTooltip from "./InfoTooltip";
import SuggestInput, { SuggestItem } from "./SuggestInput";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

interface Props {
  lines: LineItem[];
  entries: DgEntry[];
  onChange: (entries: DgEntry[]) => void;
  /** Toon één positie per scherm met navigatie */
  perPosition?: boolean;
  /** Extra DG-velden voor geselecteerde documenten (bijv. IATA/IMO) */
  extraFields?: string[];
}

const CORE_FIELDS = [
  "un_number",
  "proper_shipping_name",
  "class",
  "subsidiary_risks",
  "packing_group",
  "type_of_package",
  "quantity_packages",
  "quantity_items_per_package",
  "net_mass_liters_per_package",
  "gross_mass_per_package",
  "eq_lq_points",
  "dimensions",
  "additional_information",
] as const;

function emptyProduct(): DgProduct {
  return {
    un_number: "",
    proper_shipping_name: "",
    class: "",
    subsidiary_risks: "",
    packing_group: "",
    packing_instruction: "",
    type_of_package: "",
    quantity_packages: "",
    quantity_items_per_package: "",
    net_mass_liters_per_package: "",
    gross_mass_per_package: "",
    eq_lq_points: "",
    dimensions: "",
    additional_information: "",
    caliber: "",
  };
}

export function buildDgEntries(lines: LineItem[]): DgEntry[] {
  return lines
    .filter((line) => line.include && line.dangerous_goods)
    .map((line) => ({
      line_id: line.line_id,
      vehicle: line.output_description || line.description,
      registration: "",
      products: [
        {
          ...emptyProduct(),
          un_number: line.detected_un_numbers?.[0] || "",
        },
      ],
    }));
}

export default function DangerousGoodsStep({ lines, entries, onChange, perPosition = false, extraFields = [] }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language.startsWith("en") ? "en" : "nl";
  const [instructions, setInstructions] = useState<DgInstructions | null>(null);
  const [lookupError, setLookupError] = useState("");
  const [positionIndex, setPositionIndex] = useState(0);

  useEffect(() => {
    api.dgInstructions().then(setInstructions).catch(() => setInstructions(null));
  }, []);

  const helpFor = (field: string) => {
    const item = instructions?.dg_fields?.[field];
    return item?.help?.[lang] || "";
  };

  const labelFor = (field: string) => {
    const item = instructions?.dg_fields?.[field];
    return item?.label?.[lang] || field;
  };

  const updateEntry = (index: number, patch: Partial<DgEntry>) => {
    onChange(entries.map((entry, i) => (i === index ? { ...entry, ...patch } : entry)));
  };

  const updateProduct = (entryIndex: number, productIndex: number, patch: Partial<DgProduct>) => {
    const entry = entries[entryIndex];
    const products = entry.products.map((product, i) => (i === productIndex ? { ...product, ...patch } : product));
    updateEntry(entryIndex, { products });
  };

  const classBadge = (cls: string, pg?: string) => (
    <span className="ml-auto flex shrink-0 items-center gap-1">
      {cls && (
        <span className="rounded bg-orange-100 px-1.5 py-0.5 text-[11px] font-semibold text-orange-800 dark:bg-orange-900/50 dark:text-orange-200">
          {t("dgsearch.classShort")} {cls}
        </span>
      )}
      {pg && (
        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          PG {pg}
        </span>
      )}
    </span>
  );

  const unFetcher = async (q: string): Promise<SuggestItem<DgUnEntry>[]> => {
    const { results } = await api.dgSearch(q);
    return results.map((entry, i) => ({
      key: `${entry.un}-${i}`,
      data: entry,
      render: (
        <span className="flex items-center gap-2">
          <span className="shrink-0 font-mono font-semibold">UN {entry.un}</span>
          <span className="min-w-0 truncate">{entry.name_en || entry.name_de}</span>
          {classBadge(entry.class, entry.packing_group)}
        </span>
      ),
    }));
  };

  const applyUnEntry = (entryIndex: number, productIndex: number, un: DgUnEntry) => {
    const patch: Partial<DgProduct> = {
      un_number: un.un,
      proper_shipping_name: (un.name_en || un.name_de).toUpperCase(),
      class: un.class,
      subsidiary_risks: un.classification_code,
      packing_group: un.packing_group,
      packing_instruction: un.packing_instructions.split(" ")[0] || "",
    };
    if (un.transport_category) {
      (patch as Record<string, string>).transport_category = un.transport_category;
    }
    if (un.tunnel_code) {
      patch.additional_information = `Tunnel: (${un.tunnel_code})`;
    }
    updateProduct(entryIndex, productIndex, patch);
    // Live ADR 2025-verrijking (exacte PSN e.d.) wanneer de externe bron bereikbaar is.
    void lookupUn(entryIndex, productIndex, un.un, true);
  };

  const packagingFetcher = async (q: string): Promise<SuggestItem<DgPackaging>[]> => {
    const { results } = await api.dgPackagings(q, 40);
    return results.map((p) => ({
      key: p.code,
      data: p,
      render: (
        <span className="flex items-center gap-2">
          <span className="w-14 shrink-0 font-mono font-semibold">{p.code}</span>
          <span className="min-w-0 truncate">{p.label[lang as "nl" | "en"]}</span>
          {p.contents !== "beide" && (
            <span className="ml-auto shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {p.contents === "vloeistof" ? t("dgsearch.liquid") : t("dgsearch.solid")}
            </span>
          )}
        </span>
      ),
    }));
  };

  const lookupUn = async (entryIndex: number, productIndex: number, un: string, silent = false) => {
    setLookupError("");
    if (!un || un.replace(/\D/g, "").length < 4) return;
    try {
      const data = await api.dgLookup(un);
      // Alleen overschrijven met velden die de bron daadwerkelijk levert.
      const patch: Partial<DgProduct> = { un_number: data.un_number || un };
      if (data.proper_shipping_name) patch.proper_shipping_name = data.proper_shipping_name;
      if (data.class) patch.class = data.class;
      if (data.subsidiary_risks) patch.subsidiary_risks = data.subsidiary_risks;
      if (data.packing_group) patch.packing_group = data.packing_group;
      if (data.packing_instruction) patch.packing_instruction = data.packing_instruction;
      if (data.transport_category != null && data.transport_category !== "") {
        (patch as Record<string, string>).transport_category = String(data.transport_category);
      }
      updateProduct(entryIndex, productIndex, patch);
    } catch (e) {
      if (!silent) setLookupError(String(e));
    }
  };

  const visibleEntries = perPosition && entries.length > 0 ? [entries[positionIndex]] : entries;
  const visibleEntryOffset = perPosition ? positionIndex : 0;

  return (
    <div className="space-y-4">
      <div className={`${panelClass} p-4 text-sm text-slate-600 dark:text-slate-300`}>
        <p>{instructions?.dg_intro?.[lang] || t("wizard.dgIntro")}</p>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{t("wizard.dgSource")}</p>
      </div>

      {perPosition && entries.length > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-600 dark:text-slate-400">
            {t("wizard.dgPositionOf", { current: positionIndex + 1, total: entries.length })}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={positionIndex === 0}
              onClick={() => setPositionIndex((i) => i - 1)}
              className={buttonSecondary}
            >
              {t("wizard.back")}
            </button>
            <button
              type="button"
              disabled={positionIndex >= entries.length - 1}
              onClick={() => setPositionIndex((i) => i + 1)}
              className={buttonSecondary}
            >
              {t("wizard.next")}
            </button>
          </div>
        </div>
      )}

      {visibleEntries.map((entry, localIndex) => {
        const entryIndex = visibleEntryOffset + localIndex;
        return (
        <div key={entry.line_id} className={`${panelClass} p-5 space-y-4`}>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100">
              {t("wizard.dgLine")} {entry.line_id}
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">{entry.vehicle}</p>
          </div>
          <Field
            label={t("wizard.dgVehicle")}
            help={t("wizard.dgVehicleHelp")}
            value={entry.vehicle}
            onChange={(v) => updateEntry(entryIndex, { vehicle: v })}
          />
          {entry.products.map((product, productIndex) => (
            <div key={productIndex} className="grid md:grid-cols-2 gap-3 border-t border-slate-100 dark:border-slate-800 pt-4">
              <div>
                <div className="flex items-center gap-1.5">
                  <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
                    {labelFor("un_number")}
                  </label>
                  {helpFor("un_number") && <InfoTooltip text={helpFor("un_number")} />}
                </div>
                <div className="mt-1">
                  <SuggestInput<DgUnEntry>
                    value={product.un_number ?? ""}
                    onChange={(v) => updateProduct(entryIndex, productIndex, { un_number: v })}
                    onPick={(un) => applyUnEntry(entryIndex, productIndex, un)}
                    fetcher={unFetcher}
                    placeholder={t("dgsearch.unPlaceholder")}
                    minLength={2}
                    onBlur={() => lookupUn(entryIndex, productIndex, product.un_number ?? "")}
                  />
                </div>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t("dgsearch.unHint")}</p>
              </div>
              {[...CORE_FIELDS.filter((f) => f !== "un_number"), ...extraFields.filter((f) => !(CORE_FIELDS as readonly string[]).includes(f))].map((field) =>
                field === "type_of_package" ? (
                  <div key={field}>
                    <div className="flex items-center gap-1.5">
                      <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{labelFor(field)}</label>
                      {helpFor(field) && <InfoTooltip text={helpFor(field)} />}
                    </div>
                    <div className="mt-1">
                      <SuggestInput<DgPackaging>
                        value={String(product.type_of_package ?? "")}
                        onChange={(v) => updateProduct(entryIndex, productIndex, { type_of_package: v })}
                        onPick={(p) =>
                          updateProduct(entryIndex, productIndex, {
                            type_of_package: `${p.code} ${p.label[lang as "nl" | "en"]}`,
                          })
                        }
                        fetcher={packagingFetcher}
                        placeholder={t("dgsearch.packagingPlaceholder")}
                        minLength={1}
                      />
                    </div>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t("dgsearch.packagingHint")}</p>
                  </div>
                ) : (
                  <Field
                    key={field}
                    label={labelFor(field)}
                    help={helpFor(field)}
                    value={String(product[field as keyof DgProduct] ?? "")}
                    onChange={(v) => updateProduct(entryIndex, productIndex, { [field]: v })}
                  />
                ),
              )}
            </div>
          ))}
        </div>
        );
      })}

      {lookupError && <p className="text-amber-600 dark:text-amber-300 text-sm">{lookupError}</p>}
    </div>
  );
}

const buttonSecondary = "px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50";

function Field({
  label,
  help,
  value,
  onChange,
  onBlur,
}: {
  label: string;
  help?: string;
  value: string;
  onChange: (v: string) => void;
  onBlur?: () => void;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5">
        <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{label}</label>
        {help && <InfoTooltip text={help} />}
      </div>
      <input className={`${inputClass} mt-1`} value={value} onChange={(e) => onChange(e.target.value)} onBlur={onBlur} />
    </div>
  );
}
