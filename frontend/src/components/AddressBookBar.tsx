/**
 * The address book on the details step: one picker per party that fills the
 * party's name, address and contact fields, and one save button per party
 * that puts what is in those fields into the book under the party's name.
 *
 * Only drawn where the installation keeps its shipments — the book lives
 * beside the history and its routes do not exist otherwise. The carrier is
 * one "name and address" field, so a pick joins the two with a line break
 * and a save splits them at the first one.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Address, api } from "../api/client";
import { useToast } from "../toast/ToastProvider";

const selectClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm min-h-[40px]";
const saveClass =
  "shrink-0 rounded-lg border border-slate-200 dark:border-slate-700 px-3 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 min-h-[40px]";

/** The three parties the details step names, and the fields each one has. */
export const PARTIES = [
  { key: "consignor", fields: { name: "consignor_name", address: "consignor_address", contact: "consignor_contact" } },
  { key: "consignee", fields: { name: "consignee_name", address: "consignee_address", contact: "consignee_contact" } },
  { key: "carrier", fields: { name: "carrier_name" } },
] as const;

type Party = (typeof PARTIES)[number];

/** What one party's fields hold, read as one address-book entry. */
export function entryFrom(party: Party, values: Record<string, string>): { name: string; address: string; contact: string } {
  const name = (values[party.fields.name] ?? "").trim();
  if ("address" in party.fields) {
    return {
      name,
      address: (values[party.fields.address] ?? "").trim(),
      contact: (values[party.fields.contact] ?? "").trim(),
    };
  }
  const [first, ...rest] = name.split("\n");
  return { name: (first ?? "").trim(), address: rest.join("\n").trim(), contact: "" };
}

/** The values with one party's fields filled from an entry. */
export function fillFrom(party: Party, entry: Address, values: Record<string, string>): Record<string, string> {
  if ("address" in party.fields) {
    return {
      ...values,
      [party.fields.name]: entry.name,
      [party.fields.address]: entry.address,
      [party.fields.contact]: entry.contact,
    };
  }
  return { ...values, [party.fields.name]: [entry.name, entry.address].filter(Boolean).join("\n") };
}

interface Props {
  values: Record<string, string>;
  onChange: (values: Record<string, string>) => void;
  /** The party's label as the form shows it, by party key. */
  labels: Record<string, string>;
}

export default function AddressBookBar({ values, onChange, labels }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const [entries, setEntries] = useState<Address[]>([]);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .addresses()
      .then((list) => {
        if (!cancelled) setEntries(list);
      })
      .catch(() => {
        /* An empty book reads the same as one that could not be fetched. */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const pick = (party: Party, id: string) => {
    const entry = entries.find((e) => String(e.id) === id);
    if (entry) onChange(fillFrom(party, entry, values));
  };

  const save = async (party: Party) => {
    const entry = entryFrom(party, values);
    if (!entry.name) return;
    setSaving(party.key);
    try {
      const saved = await api.saveAddress(entry);
      setEntries((list) => {
        const without = list.filter((e) => e.id !== saved.id);
        return [...without, saved].sort((a, b) => a.name.localeCompare(b.name));
      });
      toast.success(t("addressBook.saved", { name: saved.name }));
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSaving(null);
    }
  };

  return (
    <div
      className="mt-3 rounded-xl border border-dashed border-slate-200 bg-slate-50/60 p-3 dark:border-slate-700 dark:bg-slate-800/40"
      data-testid="address-book"
    >
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("addressBook.title")}</span>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          {entries.length === 0 ? t("addressBook.empty") : t("addressBook.hint")}
        </span>
      </div>
      <div className="mt-2 grid gap-2 md:grid-cols-3">
        {PARTIES.map((party) => {
          const label = labels[party.key] ?? party.key;
          const canSave = !!entryFrom(party, values).name;
          return (
            <div key={party.key} className="flex gap-1.5">
              <select
                className={selectClass}
                value=""
                aria-label={t("addressBook.pick", { party: label })}
                onChange={(e) => pick(party, e.target.value)}
                disabled={entries.length === 0}
              >
                <option value="">{t("addressBook.pick", { party: label })}</option>
                {entries.map((entry) => (
                  <option key={entry.id} value={entry.id}>
                    {entry.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className={saveClass}
                disabled={!canSave || saving === party.key}
                onClick={() => void save(party)}
                title={t("addressBook.saveTitle", { party: label })}
                aria-label={t("addressBook.saveTitle", { party: label })}
              >
                {t("addressBook.save")}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
