/**
 * A language that is half finished is worse than no language.
 *
 * On a missing key i18next falls back quietly to English. That is precisely what
 * makes a half translation invisible: the screen keeps working, but the user
 * gets French with English gaps and does not notice anything is missing. This
 * test enforces that all the language files carry the same keys — and therefore
 * that a new key lands in every language at once.
 */
import { describe, expect, it } from "vitest";

import settingsSource from "../pages/SettingsPage.tsx?raw";
import i18nSetup from "./index.ts?raw";
import de from "./de.json";
import fr from "./fr.json";
import en from "./en.json";
import nl from "./nl.json";
import {
  DEFAULT_LANGUAGE,
  documentLanguage,
  LANGUAGE_NAMES,
  SUPPORTED_LANGUAGES,
} from "./language";

type Json = Record<string, unknown>;

/** Every key path, with arrays written out, so that a section missing a
 *  paragraph in one language surfaces too. */
function paths(value: unknown, prefix = ""): string[] {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => paths(item, `${prefix}[${index}]`));
  }
  if (value && typeof value === "object") {
    return Object.entries(value as Json).flatMap(([key, item]) =>
      paths(item, prefix ? `${prefix}.${key}` : key),
    );
  }
  return [prefix];
}

const BUNDLES: Record<string, Json> = { nl, en, de, fr };

/** Every language except Dutch, because that is what is compared against.
 *
 * This first said `["en", "de"]`. French arrived in v1.44.0 and thereby fell
 * outside the comparison: the language with the most room for gaps was the only
 * one not being checked. Hence derived rather than enumerated. */
const COMPARED = SUPPORTED_LANGUAGES.filter((language) => language !== "nl");

describe("de vertaalbestanden", () => {
  it("dekken elke taal die de app aanbiedt", () => {
    expect(Object.keys(BUNDLES).sort()).toEqual([...SUPPORTED_LANGUAGES].sort());
  });

  for (const language of COMPARED) {
    it(`${language} draagt dezelfde sleutels als het Nederlands`, () => {
      const dutch = paths(nl);
      const other = paths(BUNDLES[language]);
      expect(other.filter((key) => !dutch.includes(key))).toEqual([]);
      expect(dutch.filter((key) => !other.includes(key))).toEqual([]);
    });

    it(`${language} laat geen enkele waarde leeg`, () => {
      const empty = Object.entries(flatten(BUNDLES[language]))
        .filter(([, value]) => String(value).trim() === "")
        .map(([key]) => key);
      expect(empty).toEqual([]);
    });
  }

  it("houdt de interpolatievariabelen gelijk, anders valt er een gat in de zin", () => {
    // {{count}} that is called {{aantal}} in the translation ends up on the
    // screen as literal braces.
    const dutch = flatten(nl);
    for (const language of COMPARED) {
      const other = flatten(BUNDLES[language]);
      for (const [key, value] of Object.entries(dutch)) {
        expect(variables(String(other[key])), `${language} · ${key}`).toEqual(
          variables(String(value)),
        );
      }
    }
  });
});

function flatten(value: unknown, prefix = ""): Record<string, unknown> {
  if (Array.isArray(value) || (value && typeof value === "object")) {
    const entries = Array.isArray(value)
      ? value.map((item, index) => [`${prefix}[${index}]`, item] as const)
      : Object.entries(value as Json).map(
          ([key, item]) => [prefix ? `${prefix}.${key}` : key, item] as const,
        );
    return Object.assign({}, ...entries.map(([key, item]) => flatten(item, key)));
  }
  return { [prefix]: value };
}

function variables(text: string): string[] {
  return [...text.matchAll(/\{\{(\w+)\}\}/g)].map((match) => match[1]).sort();
}

describe("de talen die de app aanbiedt", () => {
  it("staan allemaal in de keuzelijst van de instellingen", () => {
    // Adding a language file without updating the dropdown produced a language
    // nobody could choose. The dropdown is now built from SUPPORTED_LANGUAGES,
    // so that can no longer happen — what *can* happen is a language without a
    // name, which then appears as an empty line in the list.
    expect(settingsSource).toContain("SUPPORTED_LANGUAGES.map");
    for (const language of SUPPORTED_LANGUAGES) {
      expect(LANGUAGE_NAMES[language]?.trim(), language).toBeTruthy();
    }
  });

  it("zijn allemaal bij i18next geregistreerd", () => {
    for (const language of SUPPORTED_LANGUAGES) {
      expect(i18nSetup, language).toMatch(new RegExp(`\\b${language}: \\{ translation:`));
    }
  });
});

describe("documentLanguage", () => {
  it("geeft de backend dezelfde taal als het scherm", () => {
    expect(documentLanguage("de")).toBe("de");
  });

  it("telt een landvariant mee voor haar basistaal", () => {
    // i18next produces "de-AT" when the browser says so; Austria simply gets
    // German and not Dutch by stealth.
    expect(documentLanguage("de-AT")).toBe("de");
    expect(documentLanguage("en_GB")).toBe("en");
  });

  it("valt bij een onbekende taal terug op het Nederlands", () => {
    // Dutch is the language in which the data is most complete.
    // "fr" has belonged to the supported languages since v1.44.0; "it" takes
    // over the role of unknown language here.
    expect(documentLanguage("it")).toBe(DEFAULT_LANGUAGE);
    expect(documentLanguage(undefined)).toBe(DEFAULT_LANGUAGE);
    expect(documentLanguage("")).toBe(DEFAULT_LANGUAGE);
  });
});
