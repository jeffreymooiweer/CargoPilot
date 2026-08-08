/**
 * Dezelfde gegevens, twee vormen — en op mobiel niet minder gegevens.
 *
 * De verleiding bij een kaartweergave is om velden te laten vallen die niet op
 * het scherm passen. Het artikel waar dit onderdeel op is gebaseerd zegt juist
 * het omgekeerde: toon er eerst een paar en zet de rest achter "toon meer", zodat
 * alles bereikbaar blijft. Deze tests leggen dat vast, want een veld dat op
 * mobiel stilletjes verdwijnt is erger dan een lange kaart.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResponsiveRecords, { QuantityWithUnit, RecordColumn } from "./ResponsiveRecords";

interface Row {
  id: number;
  name: string;
  quantity: string;
  weight: string;
  volume: string;
}

const rows: Row[] = [
  { id: 1, name: "Diesel", quantity: "1 200 L", weight: "1 002 kg", volume: "1,2 m³" },
  { id: 2, name: "Grind", quantity: "20 t", weight: "20 000 kg", volume: "12,5 m³" },
];

const columns: RecordColumn<Row>[] = [
  { key: "name", header: "Omschrijving", render: (r) => r.name },
  { key: "quantity", header: "Aantal", primary: true, render: (r) => r.quantity },
  { key: "weight", header: "Gewicht", render: (r) => r.weight },
  { key: "volume", header: "Volume", render: (r) => r.volume },
];

function setup() {
  return render(
    <ResponsiveRecords
      rows={rows}
      columns={columns}
      rowKey={(r) => r.id}
      cardTitle={(r) => r.name}
      actions={(r) => <button type="button">verwijder {r.id}</button>}
    />,
  );
}

describe("ResponsiveRecords", () => {
  it("renders a real table for desktop", () => {
    setup();
    // Een tabel laat rijen met elkaar vergelijken; dat kan een kaart niet.
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Omschrijving",
      "Aantal",
      "Gewicht",
      "Volume",
      // i18n draait in deze tests zonder geladen vertalingen, dus de sleutel
      // zelf komt eruit. Dat is genoeg: de kolom bestaat en is vertaalbaar.
      "records.actions",
    ]);
    expect(screen.getAllByRole("row")).toHaveLength(rows.length + 1);
  });

  it("renders one card per row alongside it", () => {
    setup();
    // De kaartkop draagt het veld waaraan je de regel herkent.
    const cards = document.querySelectorAll("article");
    expect(cards).toHaveLength(2);
    expect(cards[0].textContent).toContain("Diesel");
  });

  it("shows only the primary field on a collapsed card", () => {
    setup();
    const card = document.querySelectorAll("article")[0];
    expect(card.textContent).toContain("1 200 L");
    // Gewicht en volume zitten achter "toon meer" — maar staan wel in de tabel.
    expect(card.textContent).not.toContain("1 002 kg");
    expect(screen.getByRole("table").textContent).toContain("1 002 kg");
  });

  it("reveals the remaining fields on demand, and hides them again", () => {
    setup();
    const card = document.querySelectorAll("article")[0];
    const toggle = card.querySelector("button[aria-expanded]") as HTMLButtonElement;
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(card.textContent).toContain("1 002 kg");
    expect(card.textContent).toContain("1,2 m³");

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(card.textContent).not.toContain("1 002 kg");
  });

  it("expands each card on its own", () => {
    setup();
    const cards = document.querySelectorAll("article");
    fireEvent.click(cards[0].querySelector("button[aria-expanded]") as HTMLButtonElement);
    expect(cards[0].textContent).toContain("1 002 kg");
    expect(cards[1].textContent).not.toContain("20 000 kg");
  });

  it("puts the actions in the card header as well as the table", () => {
    setup();
    // Twee kaarten en twee tabelrijen, dus elke actie bestaat twee keer.
    expect(screen.getAllByRole("button", { name: /verwijder 1/ })).toHaveLength(2);
  });

  it("offers no toggle when every field already fits", () => {
    render(
      <ResponsiveRecords
        rows={rows}
        columns={[{ key: "name", header: "Omschrijving", primary: true, render: (r) => r.name }]}
        rowKey={(r) => r.id}
        cardTitle={(r) => r.name}
      />,
    );
    expect(document.querySelector("button[aria-expanded]")).toBeNull();
  });

  it("shows the empty state instead of an empty table", () => {
    render(
      <ResponsiveRecords
        rows={[]}
        columns={columns}
        rowKey={(r) => r.id}
        cardTitle={(r) => r.name}
        empty="Nog geen regels"
      />,
    );
    expect(screen.getByText("Nog geen regels")).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
  });
});

describe("QuantityWithUnit", () => {
  it("puts the unit behind the value instead of in its own column", () => {
    // Zoals het artikel het doet: "150 (sqm)", niet een kolom "eenheid".
    render(<QuantityWithUnit value="1 200" unit="L" />);
    expect(screen.getByText("1 200").parentElement?.textContent).toBe("1 200L");
  });

  it("leaves the value alone when there is no unit", () => {
    render(<QuantityWithUnit value="12" />);
    expect(screen.getByText("12").textContent).toBe("12");
  });
});
