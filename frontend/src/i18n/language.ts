/**
 * Welke taal de backend meekrijgt.
 *
 * De interface en de documenten spreken dezelfde taal, maar dat werd op zes
 * plaatsen apart uitgerekend met `startsWith("en") ? "en" : "nl"`. Zolang er
 * twee talen waren viel dat niet op; bij een derde taal betekende het dat de
 * schermen Duits werden en de waarschuwingen, veldnamen en exports Nederlands
 * bleven. Eén plek, dus een taal erbij is één regel.
 */

export const SUPPORTED_LANGUAGES = ["nl", "en", "de", "fr"] as const;

export type Language = (typeof SUPPORTED_LANGUAGES)[number];

export const DEFAULT_LANGUAGE: Language = "nl";

/** De taalcode die de backend verwacht, afgeleid uit i18next.
 *
 * i18next levert ook varianten als "de-AT" of "en-GB"; die tellen mee voor hun
 * basistaal. Wat we niet kennen valt terug op Nederlands — dat is de taal
 * waarin de gegevens het volledigst zijn. */
export function documentLanguage(language: string | undefined): Language {
  const base = String(language || "").toLowerCase().split(/[-_]/)[0];
  return (SUPPORTED_LANGUAGES as readonly string[]).includes(base)
    ? (base as Language)
    : DEFAULT_LANGUAGE;
}

/** Tekst uit een {nl, en, de, fr}-blokje van de backend.
 *
 * Het documentregister komt van de server en kan uit een oudere of eigen
 * uitgave komen waarin een taal ontbreekt. Een leeg label is dan erger dan een
 * label in een andere taal: de gebruiker ziet een veld zonder naam. Vandaar de
 * volgorde gevraagd → Nederlands → Engels. */
export function localised(
  text: Partial<Record<Language, string>> | undefined | null,
  language: Language,
): string {
  if (!text) return "";
  return text[language] || text.nl || text.en || "";
}
