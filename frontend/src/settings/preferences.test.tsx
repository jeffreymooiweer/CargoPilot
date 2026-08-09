/**
 * Instellingen die van de server komen, in een app die al geverfd is.
 *
 * Twee dingen kunnen hier stukgaan, en geen van beide valt op zonder test.
 *
 * Het eerste is de volgorde. De voorkeuren komen over het netwerk, maar er moet
 * al iets op het scherm staan voordat het antwoord binnen is. Daarom houdt de
 * app een kopie in `localStorage` en past die meteen toe; het antwoord van de
 * server wint daarna. Wie die kopie tot waarheid promoveert, krijgt precies het
 * gedrag terug dat we kwijt wilden: een gebruiker die op een tweede apparaat
 * inlogt en de app in het Nederlands en in het licht terugvindt.
 *
 * Het tweede is de terugval. Een mislukt verzoek om instellingen mag de wizard
 * niet blokkeren — iemand die geen voorkeuren kan ophalen moet nog steeds een
 * vrachtbrief kunnen maken.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "i18next";

import { api, UserPreferences } from "../api/client";
import {
  EMPTY_PREFERENCES,
  LANGUAGE_STORAGE_KEY,
  PreferencesProvider,
  applyPreferences,
  usePreferences,
} from "./preferences";

function preferences(overrides: Partial<UserPreferences> = {}): UserPreferences {
  return { ...EMPTY_PREFERENCES, ...overrides };
}

function Probe() {
  const { preferences: current, loaded } = usePreferences();
  return (
    <div>
      <span data-testid="loaded">{String(loaded)}</span>
      <span data-testid="consignor">{current.consignor_name}</span>
      <span data-testid="unit">{current.default_unit}</span>
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove("dark");
  vi.spyOn(i18n, "changeLanguage").mockResolvedValue(((key: string) => key) as never);
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    }),
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("applyPreferences", () => {
  it("zet het donkere thema aan", () => {
    applyPreferences(preferences({ theme: "dark" }));

    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("laat 'system' het systeem volgen in plaats van een keuze te bewaren", () => {
    // Een opgeslagen "light" zou het systeem blijven overstemmen; daarom wist
    // applySystemTheme de sleutel in plaats van er een waarde in te zetten.
    applyPreferences(preferences({ theme: "dark" }));
    applyPreferences(preferences({ theme: "system" }));

    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(localStorage.getItem("cargopilot-theme")).toBeNull();
  });

  it("bewaart de taal als kopie, zodat de volgende start niet flikkert", () => {
    applyPreferences(preferences({ language: "fr" }));

    expect(i18n.changeLanguage).toHaveBeenCalledWith("fr");
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("fr");
  });

  it("laat een taal die we niet kennen niet door naar i18next", () => {
    // documentLanguage vangt het af: een onbekende code zou anders een leeg
    // scherm opleveren, want er is geen vertaalbestand voor.
    applyPreferences(preferences({ language: "it" }));

    expect(i18n.changeLanguage).toHaveBeenCalledWith("nl");
  });
});

describe("de voorkeurenprovider", () => {
  it("haalt de voorkeuren op en deelt ze met de rest van de app", async () => {
    vi.spyOn(api, "mySettings").mockResolvedValue(
      preferences({ consignor_name: "Mooiweer BV", default_unit: "pallet", theme: "dark" }),
    );
    vi.spyOn(api, "publicSettings").mockResolvedValue({
      default_language: "nl",
      default_theme: "system",
      address_lookup_enabled: true,
      un_cards_enabled: true,
      organisation_name: "",
      organisation_address: "",
    });

    render(
      <PreferencesProvider>
        <Probe />
      </PreferencesProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("loaded")).toHaveTextContent("true"));
    expect(screen.getByTestId("consignor")).toHaveTextContent("Mooiweer BV");
    expect(screen.getByTestId("unit")).toHaveTextContent("pallet");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("blijft bruikbaar wanneer de instellingen niet op te halen zijn", async () => {
    // Geen voorkeuren is geen reden om geen vrachtbrief te kunnen maken.
    vi.spyOn(api, "mySettings").mockRejectedValue(new Error("offline"));
    vi.spyOn(api, "publicSettings").mockRejectedValue(new Error("offline"));

    render(
      <PreferencesProvider>
        <Probe />
      </PreferencesProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("loaded")).toHaveTextContent("true"));
    expect(screen.getByTestId("unit")).toHaveTextContent(EMPTY_PREFERENCES.default_unit);
  });
});
