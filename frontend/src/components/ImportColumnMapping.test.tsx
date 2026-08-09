/**
 * The column mapping of an imported file.
 *
 * The import guesses when it does not recognise the heading row, and it has to —
 * otherwise every import becomes handwork. What is recorded here is that the
 * user sees *that* it guessed, and gets to see enough to correct the guess. A
 * dropdown saying "column 1, column 2, column 3" does not do that; what is in
 * the column does.
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
  // The user has to be able to tell from the content which column is the description.
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

  // Description from column 1 (the references) to column 2 (the names).
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
  // Without a recognised heading row, row 1 reads along as a goods line; that is
  // often exactly what goes wrong.
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
