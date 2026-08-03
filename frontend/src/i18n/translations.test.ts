/**
 * Een taal die half af is, is erger dan geen taal.
 *
 * i18next valt bij een ontbrekende sleutel stil terug op het Engels. Dat is
 * precies wat een halve vertaling onzichtbaar maakt: het scherm blijft werken,
 * maar de gebruiker krijgt Duits met Engelse gaten en merkt niet dat er iets
 * mist. Deze test dwingt af dat de drie bestanden dezelfde sleutels dragen —
 * en dat een nieuwe sleutel dus in alle drie tegelijk landt.
 */
import { describe, expect, it } from "vitest";

import settingsSource from "../pages/SettingsPage.tsx?raw";
import i18nSetup from "./index.ts?raw";
import de from "./de.json";
import en from "./en.json";
import nl from "./nl.json";
import { DEFAULT_LANGUAGE, documentLanguage, SUPPORTED_LANGUAGES } from "./language";

type Json = Record<string, unknown>;

/** Alle sleutelpaden, met arrays uitgeschreven, zodat ook een sectie die in één
 *  taal een alinea mist bovenkomt. */
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

const BUNDLES: Record<string, Json> = { nl, en, de };

describe("de vertaalbestanden", () => {
  it("dekken elke taal die de app aanbiedt", () => {
    expect(Object.keys(BUNDLES).sort()).toEqual([...SUPPORTED_LANGUAGES].sort());
  });

  for (const language of ["en", "de"]) {
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
    // {{count}} dat in de vertaling {{aantal}} heet, komt als letterlijke
    // accolades op het scherm.
    const dutch = flatten(nl);
    for (const language of ["en", "de"]) {
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
  it("staan alle drie in de keuzelijst van de instellingen", () => {
    // Een taalbestand toevoegen zonder de keuzelijst bij te werken levert een
    // taal op die niemand kan kiezen.
    for (const language of SUPPORTED_LANGUAGES) {
      expect(settingsSource, language).toContain(`<option value="${language}">`);
    }
  });

  it("zijn alle drie bij i18next geregistreerd", () => {
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
    // i18next levert "de-AT" wanneer de browser dat zegt; Oostenrijk krijgt
    // gewoon Duits en niet stilzwijgend Nederlands.
    expect(documentLanguage("de-AT")).toBe("de");
    expect(documentLanguage("en_GB")).toBe("en");
  });

  it("valt bij een onbekende taal terug op het Nederlands", () => {
    // Nederlands is de taal waarin de gegevens het volledigst zijn.
    expect(documentLanguage("fr")).toBe(DEFAULT_LANGUAGE);
    expect(documentLanguage(undefined)).toBe(DEFAULT_LANGUAGE);
    expect(documentLanguage("")).toBe(DEFAULT_LANGUAGE);
  });
});
