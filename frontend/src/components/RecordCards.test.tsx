/**
 * One shape at every width: the card.
 *
 * What replaced the table has to keep the two things the table's mobile half
 * did well — a collapsed card shows only what you scan by, and everything else
 * is one tap away — plus the one thing the cards must not do: hide a question
 * the record is waiting for an answer to behind "show more".
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import RecordCards, { NoValue, QuantityWithUnit, RecordField } from "./RecordCards";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "nl" },
  }),
}));

interface Row {
  id: number;
  name: string;
  amount: number;
  note: string;
}

const rows: Row[] = [
  { id: 1, name: "steel plate", amount: 12, note: "on a pallet" },
  { id: 2, name: "petrol", amount: 20, note: "in drums" },
];

const fields: RecordField<Row>[] = [
  { key: "amount", label: "amount", primary: true, render: (row) => String(row.amount) },
  { key: "note", label: "note", render: (row) => row.note },
];

function renderCards(extra: Partial<React.ComponentProps<typeof RecordCards<Row>>> = {}) {
  render(
    <RecordCards
      rows={rows}
      fields={fields}
      rowKey={(row) => row.id}
      cardTitle={(row) => row.name}
      {...extra}
    />,
  );
}

describe("RecordCards", () => {
  it("shows a card per record with its title and primary field", () => {
    renderCards();
    expect(screen.getByText("steel plate")).toBeInTheDocument();
    expect(screen.getByText("petrol")).toBeInTheDocument();
    expect(screen.getAllByText("amount")).toHaveLength(2);
  });

  it("keeps the secondary fields behind show-more until asked", async () => {
    renderCards();
    expect(screen.queryByText("on a pallet")).not.toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: /records.viewMore/ })[0]);
    expect(screen.getByText("on a pallet")).toBeInTheDocument();
    // Only that card opened; the other one keeps its own state.
    expect(screen.queryByText("in drums")).not.toBeInTheDocument();
  });

  it("says with aria-expanded what the toggle does", async () => {
    renderCards();
    const toggle = screen.getAllByRole("button", { name: /records.viewMore/ })[0];
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(toggle);
    expect(screen.getAllByRole("button", { name: /records.viewLess/ })[0]).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("renders the actions per record", () => {
    renderCards({ actions: (row) => <button type="button">edit {row.id}</button> });
    expect(screen.getByRole("button", { name: "edit 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "edit 2" })).toBeInTheDocument();
  });

  it("without an explicit primary the first two fields are the ones shown", () => {
    render(
      <RecordCards
        rows={[rows[0]]}
        fields={[
          { key: "a", label: "a", render: () => "one" },
          { key: "b", label: "b", render: () => "two" },
          { key: "c", label: "c", render: () => "three" },
        ]}
        rowKey={(row) => row.id}
        cardTitle={(row) => row.name}
      />,
    );
    expect(screen.getByText("one")).toBeInTheDocument();
    expect(screen.getByText("two")).toBeInTheDocument();
    expect(screen.queryByText("three")).not.toBeInTheDocument();
  });

  it("shows the empty state instead of an empty list", () => {
    render(
      <RecordCards
        rows={[]}
        fields={fields}
        rowKey={(row: Row) => row.id}
        cardTitle={(row: Row) => row.name}
        empty={<span>nothing here</span>}
      />,
    );
    expect(screen.getByText("nothing here")).toBeInTheDocument();
  });

  it("has no toggle when there is nothing behind it", () => {
    render(
      <RecordCards
        rows={[rows[0]]}
        fields={[{ key: "amount", label: "amount", primary: true, render: () => "12" }]}
        rowKey={(row) => row.id}
        cardTitle={(row) => row.name}
      />,
    );
    expect(screen.queryByRole("button", { name: /records.view/ })).not.toBeInTheDocument();
  });

  it("puts the unit small behind the figure, and a dash where there is none", () => {
    render(
      <p>
        <QuantityWithUnit value={1200} unit="L" />
        <NoValue />
      </p>,
    );
    expect(screen.getByText("1200")).toBeInTheDocument();
    expect(screen.getByText("L")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
