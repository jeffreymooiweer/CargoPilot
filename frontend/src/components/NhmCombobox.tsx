/**
 * Box 24 of the CIM: the NHM code, picked from the nomenclature.
 *
 * The field stays what it is — six digits — and the value stays a string,
 * so a person who knows the code types it and moves on. What is new is
 * the list: typing digits lists the subheadings under that prefix, typing
 * a word searches the English and French labels, and picking one puts its
 * code in the box. The label of the code in the box is fetched and shown
 * under it, so a code typed by hand is read back in words.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { NhmEntry, api } from "../api/client";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm min-h-[40px]";

interface Props {
  value: string;
  onChange: (value: string) => void;
  /** So a label can point at the field and a caller can focus it. */
  id?: string;
}

export default function NhmCombobox({ value, onChange, id }: Props) {
  const { t } = useTranslation();
  const [query, setQuery] = useState(value);
  const [hits, setHits] = useState<NhmEntry[]>([]);
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState<NhmEntry | null>(null);

  // The value can change from outside (a kept shipment reopened, a template);
  // the box follows.
  useEffect(() => {
    setQuery(value);
  }, [value]);

  // The words behind a six-digit code, whether picked or typed.
  useEffect(() => {
    if (!/^\d{6}$/.test(value)) {
      setLabel(null);
      return;
    }
    let cancelled = false;
    api
      .nhmLookup(value)
      .then((entry) => {
        if (!cancelled) setLabel(entry);
      })
      .catch(() => {
        if (!cancelled) setLabel(null);
      });
    return () => {
      cancelled = true;
    };
  }, [value]);

  // The list, a moment after the last keystroke.
  useEffect(() => {
    const needle = query.trim();
    if (!open || needle.length < 2) {
      setHits([]);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      api
        .nhmSearch(needle)
        .then((result) => {
          if (!cancelled) setHits(result.results);
        })
        .catch(() => {
          if (!cancelled) setHits([]);
        });
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query, open]);

  return (
    <div className="space-y-1">
      <input
        id={id}
        className={inputClass}
        value={query}
        inputMode="text"
        placeholder={t("nhm.placeholder")}
        aria-label={t("nhm.placeholder")}
        onChange={(e) => {
          setQuery(e.target.value);
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
      />
      {open && hits.length > 0 && (
        <ul
          role="listbox"
          className="max-h-56 overflow-y-auto rounded-lg border border-slate-200 bg-white text-sm shadow-sm dark:border-slate-700 dark:bg-slate-900"
        >
          {hits.map((hit) => (
            <li key={hit.code}>
              <button
                type="button"
                role="option"
                aria-selected={hit.code === value}
                className="flex w-full items-baseline gap-2 px-3 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-800"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onChange(hit.code);
                  setQuery(hit.code);
                  setOpen(false);
                }}
              >
                <span className="font-mono font-medium text-slate-900 dark:text-slate-100">{hit.code}</span>
                <span className="text-slate-600 dark:text-slate-300">{hit.en}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {label && (
        <p className="text-xs text-slate-600 dark:text-slate-400" data-testid="nhm-label">
          {label.en}
          <span className="text-slate-400 dark:text-slate-500"> · {label.fr}</span>
        </p>
      )}
      <p className="text-[11px] text-slate-500 dark:text-slate-500">{t("nhm.source")}</p>
    </div>
  );
}
