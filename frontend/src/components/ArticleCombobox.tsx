/** Pick an article of the organisation's own library onto a goods line.
 *
 *  The library is small — codes the office types every day — so it is
 *  fetched once and searched in the browser by code, name or UN number.
 *  Choosing one hands the whole article back; the line dialog decides what
 *  to do with it. Only drawn where the installation keeps a library.
 */
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { Article, api } from "../api/client";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";

interface Props {
  /** The code on the line, if one was picked. */
  value?: string;
  onPick: (article: Article) => void;
  onClear: () => void;
}

export default function ArticleCombobox({ value, onPick, onClear }: Props) {
  const { t } = useTranslation();
  const [articles, setArticles] = useState<Article[]>([]);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api
      .articles()
      .then((list) => setArticles(list.filter((a) => a.active)))
      .catch(() => setArticles([]));
  }, []);

  const hits = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const pool = needle
      ? articles.filter((a) =>
          [a.code, a.name, a.un_number, a.proper_shipping_name].some((f) => f.toLowerCase().includes(needle)),
        )
      : articles;
    return pool.slice(0, 12);
  }, [articles, query]);

  if (articles.length === 0 && !value) return null;

  return (
    <div className="space-y-1">
      {value ? (
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-800 dark:bg-sky-900/40 dark:text-sky-300">
            {value}
          </span>
          <button
            type="button"
            className="text-xs text-slate-600 underline dark:text-slate-300"
            onClick={() => {
              onClear();
              setQuery("");
            }}
          >
            {t("articles.clearFromLine")}
          </button>
        </div>
      ) : (
        <>
          <input
            className={inputClass}
            value={query}
            placeholder={t("articles.pick")}
            aria-label={t("articles.pick")}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
          />
          {open && hits.length > 0 && (
            <ul
              role="listbox"
              className="max-h-48 overflow-y-auto rounded-lg border border-slate-200 bg-white text-sm shadow-sm dark:border-slate-700 dark:bg-slate-900"
            >
              {hits.map((article) => (
                <li key={article.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={false}
                    className="flex w-full items-baseline gap-2 px-3 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-800"
                    onClick={() => {
                      onPick(article);
                      setOpen(false);
                      setQuery("");
                    }}
                  >
                    <span className="font-medium text-slate-900 dark:text-slate-100">{article.code}</span>
                    <span className="text-slate-600 dark:text-slate-300">{article.name}</span>
                    {article.un_number && <span className="ml-auto text-xs text-slate-500">UN {article.un_number}</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
