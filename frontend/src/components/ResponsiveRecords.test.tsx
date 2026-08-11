/**
 * The same data, two shapes — and on mobile not less data.
 *
 * The temptation with a card view is to drop fields that do not fit on the
 * screen. The article this component is based on says the opposite: show a few
 * of them and put the rest behind "show more", so everything stays reachable.
 * These tests record that, because a field that quietly disappears on mobile is
 * worse than a long card.
 */
import {
  render,
  screen,
  fireEvent,
  waitForElementToBeRemoved,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    // A table lets rows be compared with each other; a card cannot.
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Omschrijving",
      "Aantal",
      "Gewicht",
      "Volume",
      // i18n runs in these tests without loaded translations, so the key itself
      // comes out. That is enough: the column exists and is translatable.
      "records.actions",
    ]);
    expect(screen.getAllByRole("row")).toHaveLength(rows.length + 1);
  });

  it("renders one card per row alongside it", () => {
    setup();
    // The card heading carries the field you recognise the line by.
    const cards = document.querySelectorAll("article");
    expect(cards).toHaveLength(2);
    expect(cards[0].textContent).toContain("Diesel");
  });

  it("shows only the primary field on a collapsed card", () => {
    setup();
    const card = document.querySelectorAll("article")[0];
    expect(card.textContent).toContain("1 200 L");
    // Weight and volume sit behind "show more" — but are in the table.
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
    // Two cards and two table rows, so every action exists twice.
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

describe("de vloer onder de desktoptabel", () => {
  // A `w-full` table can never be wider than its container, so the
  // `overflow-x-auto` around it never engages and the browser takes the missing
  // width out of the cells instead. On a table you read that is fine — the text
  // wraps. On a table you *type* in it is not: the lines step gave its number
  // field 30px and its unit select 28px.
  it("laat de tabel breder worden dan zijn container", () => {
    render(
      <ResponsiveRecords
        rows={rows}
        columns={columns}
        rowKey={(r) => r.id}
        cardTitle={(r) => r.name}
        minWidth="min-w-[1620px]"
      />,
    );
    expect(screen.getByRole("table").className).toContain("min-w-[1620px]");
    expect(screen.getByRole("table").parentElement?.className).toContain("overflow-x-auto");
  });

  it("laat een tabel zonder vloer met rust", () => {
    render(
      <ResponsiveRecords
        rows={rows}
        columns={columns}
        rowKey={(r) => r.id}
        cardTitle={(r) => r.name}
      />,
    );
    expect(screen.getByRole("table").className).not.toContain("min-w-");
  });
});

describe("het detailpaneel", () => {
  /**
   * The third way out of a table that is too wide.
   *
   * The lines table has thirteen columns of input fields and wants 1,620px, so
   * on anything narrower something has to give: the table scrolls sideways or
   * the fields get squeezed. The panel is the alternative — one line, every
   * column under each other, at full width — and it is the *same* shape as the
   * mobile card, which is why it belongs to this component.
   *
   * What makes it worth testing is that it holds the same controls as the row
   * behind it. A panel you can only read would send you back to the cramped
   * table to change anything.
   */
  function open() {
    render(
      <ResponsiveRecords
        rows={rows}
        columns={columns}
        rowKey={(r) => r.id}
        cardTitle={(r) => r.name}
        detail
        actions={(r) => <button type="button">Verwijder {r.name}</button>}
      />,
    );
    return screen.getAllByRole("button", { name: "records.showDetail" });
  }

  it("geeft elke rij een detailknop", () => {
    expect(open()).toHaveLength(rows.length);
  });

  it("blijft weg als er niet om gevraagd is", () => {
    render(
      <ResponsiveRecords
        rows={rows}
        columns={columns}
        rowKey={(r) => r.id}
        cardTitle={(r) => r.name}
      />,
    );
    expect(screen.queryByRole("button", { name: "records.showDetail" })).toBeNull();
  });

  it("toont alle kolommen van die ene regel onder elkaar", async () => {
    const [, second] = open();
    await userEvent.click(second);

    const panel = screen.getByRole("dialog");
    // Every column, including the ones the mobile card hides behind "show more".
    for (const column of columns) {
      expect(within(panel).getByText(column.header)).toBeInTheDocument();
    }
    // And it is the *clicked* row, not the first one.
    expect(within(panel).getByText("20 t")).toBeInTheDocument();
  });

  it("neemt de acties van de regel mee", async () => {
    await userEvent.click(open()[0]);
    expect(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Verwijder Diesel" }),
    ).toBeInTheDocument();
  });

  it("sluit met Escape en geeft de focus terug aan de knop", async () => {
    const [first] = open();
    await userEvent.click(first);
    expect(screen.getByRole("dialog")).toHaveFocus();

    await userEvent.keyboard("{Escape}");
    await waitForElementToBeRemoved(() => screen.queryByRole("dialog"));
    expect(first).toHaveFocus();
  });

  it("sluit met het kruisje", async () => {
    await userEvent.click(open()[0]);
    await userEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "records.closeDetail" }),
    );
    await waitForElementToBeRemoved(() => screen.queryByRole("dialog"));
  });

  it("zet de pagina achter het paneel vast en laat hem daarna weer los", async () => {
    await userEvent.click(open()[0]);
    expect(document.body.style.overflow).toBe("hidden");
    await userEvent.keyboard("{Escape}");
    await waitForElementToBeRemoved(() => screen.queryByRole("dialog"));
    expect(document.body.style.overflow).not.toBe("hidden");
  });

  it("verdwijnt als de regel eronder verdwijnt", async () => {
    // The row is held by its key and not by its index, so a line deleted from
    // the table behind the panel takes the panel with it instead of leaving one
    // that describes a different line.
    const { rerender } = render(
      <ResponsiveRecords
        rows={rows}
        columns={columns}
        rowKey={(r) => r.id}
        cardTitle={(r) => r.name}
        detail
      />,
    );
    await userEvent.click(screen.getAllByRole("button", { name: "records.showDetail" })[1]);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    rerender(
      <ResponsiveRecords
        rows={[rows[0]]}
        columns={columns}
        rowKey={(r) => r.id}
        cardTitle={(r) => r.name}
        detail
      />,
    );
    // Straight away, without the slide-out: what it described is gone, so
    // watching it leave would be watching a panel about nothing.
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("QuantityWithUnit", () => {
  it("puts the unit behind the value instead of in its own column", () => {
    // As the article does it: "150 (sqm)", not a column "unit".
    render(<QuantityWithUnit value="1 200" unit="L" />);
    expect(screen.getByText("1 200").parentElement?.textContent).toBe("1 200L");
  });

  it("leaves the value alone when there is no unit", () => {
    render(<QuantityWithUnit value="12" />);
    expect(screen.getByText("12").textContent).toBe("12");
  });
});
