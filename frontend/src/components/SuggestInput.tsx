import { ReactNode, useEffect, useRef, useState } from "react";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";

export interface SuggestItem<T> {
  key: string;
  data: T;
  render: ReactNode;
}

interface Props<T> {
  value: string;
  onChange: (value: string) => void;
  onPick: (item: T) => void;
  fetcher: (q: string) => Promise<SuggestItem<T>[]>;
  placeholder?: string;
  minLength?: number;
  onBlur?: () => void;
  className?: string;
}

/** Tekstinvoer met debounced suggestiedropdown; vrije tekst blijft altijd mogelijk. */
export default function SuggestInput<T>({
  value,
  onChange,
  onPick,
  fetcher,
  placeholder,
  minLength = 2,
  onBlur,
  className,
}: Props<T>) {
  const [items, setItems] = useState<SuggestItem<T>[]>([]);
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const latest = useRef(0);

  useEffect(() => {
    window.clearTimeout(timer.current);
    if (!open || picked || value.trim().length < minLength) {
      setItems([]);
      return;
    }
    const id = ++latest.current;
    timer.current = window.setTimeout(() => {
      fetcher(value)
        .then((results) => {
          if (latest.current === id) setItems(results);
        })
        .catch(() => {
          if (latest.current === id) setItems([]);
        });
    }, 250);
    return () => window.clearTimeout(timer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, open, picked]);

  return (
    <div className="relative">
      <input
        className={className ?? inputClass}
        value={value}
        placeholder={placeholder}
        onChange={(e) => {
          setPicked(false);
          onChange(e.target.value);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          setOpen(false);
          setItems([]);
          onBlur?.();
        }}
        autoComplete="off"
      />
      {open && !picked && items.length > 0 && (
        <ul className="absolute z-20 mt-1 max-h-72 w-full min-w-[280px] overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900">
          {items.map((item) => (
            <li key={item.key}>
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  setPicked(true);
                  setItems([]);
                  onPick(item.data);
                }}
                className="w-full px-3 py-2 text-left text-sm text-slate-800 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                {item.render}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
