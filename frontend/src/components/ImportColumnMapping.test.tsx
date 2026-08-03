/**
 * De kolomindeling van een geïmporteerd bestand.
 *
 * De import raadt wanneer hij de koptekst niet herkent, en dat moet ook —
 * anders wordt elke import handwerk. Wat hier wordt vastgelegd is dat de
 * gebruiker ziet dát er geraden is, en genoeg te zien krijgt om de gok te
 * kunnen corrigeren. Een keuzelijst met "kolom 1, kolom 2, kolom 3" doet dat
 * niet; wat er in de kolom staat wel.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ImportColumnMapping from "./ImportColumnMapping";
import { ImportAnalysis } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }),
}));

const GUESSED: ImportAnalysis = {
  source: "position",
  has_header: false,
  mapping: { description: 0, quantity: 1, unit: 2 },
  columns: [
    { index: 0, header: "", samples: ["Ref", "A-1", "A-2"] },
    { index: 1, header: "", samples: ["Benaming", "Stalen hoekprofiel 80x80x8x6000"] },
    { index: 2, header: "", samples: ["Aant.", "8", "4"] },
    { index: 3, header: "", samples: ["Eenh.", "stuks", "stuks"] },
  ],
};

const RECOGNISED: ImportAnalysis = {
  source: "header",
  has_header: true,
  mapping: { description: 0, quantity: 1, unit: 2 },
  columns: [
    { index: 0, header: "Omschrijving", samples: ["Stalen hoekprofiel 80x80x8x6000"] },
    { index: 1, header: "Aantal", samples: ["8"] },
    { index: 2, header: "Eenheid", samples: ["stuks"] },
  ],
};

it("zegt het wanneer de kolommen zijn geraden", () => {
  render(<ImportColumnMapping analysis={GUESSED} onChange={vi.fn()} />);
  expect(screen.getByText("import.guessedColumns")).toBeInTheDocument();
});

it("zegt het ook wanneer de koptekst wel is herkend", () => {
  render(<ImportColumnMapping analysis={RECOGNISED} onChange={vi.fn()} />);
  expect(screen.getByText("import.recognisedColumns")).toBeInTheDocument();
});

it("toont per kolom wat erin staat, niet alleen een nummer", () => {
  render(<ImportColumnMapping analysis={GUESSED} onChange={vi.fn()} />);
  // De gebruiker moet aan de inhoud kunnen zien welke kolom de omschrijving is.
  expect(
    screen.getAllByRole("option", { name: /Stalen hoekprofiel 80x80x8x6000/ }).length,
  ).toBeGreaterThan(0);
});

it("laat een lange kolominhoud niet de keuzelijst opblazen", () => {
  const long = { ...GUESSED, columns: [{ index: 0, header: "", samples: ["x".repeat(200)] }] };
  render(<ImportColumnMapping analysis={long} onChange={vi.fn()} />);
  const option = screen.getAllByRole("option")[1];
  expect(option.textContent!.length).toBeLessThan(70);
});

it("geeft een gewijzigde kolomkeuze door", () => {
  const onChange = vi.fn();
  render(<ImportColumnMapping analysis={GUESSED} onChange={onChange} />);

  // Omschrijving van kolom 1 (de referenties) naar kolom 2 (de benamingen).
  fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: "1" } });
  expect(onChange).toHaveBeenCalledWith(
    { description: 1, quantity: 1, unit: 2 },
    false,
  );
});

it("laat een kolom bewust leeg laten", () => {
  const onChange = vi.fn();
  render(<ImportColumnMapping analysis={GUESSED} onChange={onChange} />);
  fireEvent.change(screen.getAllByRole("combobox")[2], { target: { value: "" } });
  expect(onChange).toHaveBeenCalledWith(
    { description: 0, quantity: 1, unit: null },
    false,
  );
});

it("laat de eerste regel als koptekst aanmerken", () => {
  // Zonder herkende koptekst leest regel 1 mee als goederenregel; dat is vaak
  // precies wat er misgaat.
  const onChange = vi.fn();
  render(<ImportColumnMapping analysis={GUESSED} onChange={onChange} />);
  fireEvent.click(screen.getByRole("checkbox"));
  expect(onChange).toHaveBeenCalledWith(GUESSED.mapping, true);
});

it("toont niets voor een bestand zonder kolommen", () => {
  const empty: ImportAnalysis = {
    source: "none",
    has_header: false,
    mapping: { description: null, quantity: null, unit: null },
    columns: [],
  };
  const { container } = render(<ImportColumnMapping analysis={empty} onChange={vi.fn()} />);
  expect(container).toBeEmptyDOMElement();
});

describe("terwijl er een nieuwe indeling wordt opgehaald", () => {
  it("staan de keuzes op slot", () => {
    render(<ImportColumnMapping analysis={GUESSED} onChange={vi.fn()} busy />);
    for (const box of screen.getAllByRole("combobox")) {
      expect(box).toBeDisabled();
    }
    expect(screen.getByRole("checkbox")).toBeDisabled();
  });
});
