/**
 * Which language the backend is given.
 *
 * The interface and the documents speak the same language, but that was worked
 * out separately in six places with `startsWith("en") ? "en" : "nl"`. While
 * there were two languages that went unnoticed; with a third it meant the
 * screens went German and the warnings, field names and exports stayed Dutch.
 * One place, so one more language is one line.
 */

export const SUPPORTED_LANGUAGES = ["nl", "en", "de", "fr"] as const;

export type Language = (typeof SUPPORTED_LANGUAGES)[number];

export const DEFAULT_LANGUAGE: Language = "nl";

/** What each language is called in the dropdown — in that language itself.
 *
 * "Deutsch" and not "German": whoever wants to set the interface to German is
 * still reading Dutch at that moment and looks for the word they know. The list
 * is built from SUPPORTED_LANGUAGES, so adding a language file without updating
 * the dropdown is no longer possible. */
export const LANGUAGE_NAMES: Record<Language, string> = {
  nl: "Nederlands",
  en: "English",
  de: "Deutsch",
  fr: "Français",
};

/** The language code the backend expects, derived from i18next.
 *
 * i18next also produces variants like "de-AT" or "en-GB"; those count towards
 * their base language. What we do not know falls back to Dutch — the language in
 * which the data is most complete. */
export function documentLanguage(language: string | undefined): Language {
  const base = String(language || "").toLowerCase().split(/[-_]/)[0];
  return (SUPPORTED_LANGUAGES as readonly string[]).includes(base)
    ? (base as Language)
    : DEFAULT_LANGUAGE;
}

/** Text from a {nl, en, de, fr} block from the backend.
 *
 * The document registry comes from the server and can come from an older or a
 * custom edition in which a language is missing. An empty label is then worse
 * than a label in another language: the user sees a field without a name. Hence
 * the order requested → Dutch → English. */
export function localised(
  text: Partial<Record<Language, string>> | undefined | null,
  language: Language,
): string {
  if (!text) return "";
  return text[language] || text.nl || text.en || "";
}
