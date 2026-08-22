/**
 * The lines step: cards that show, a dialog that edits.
 *
 * Two things are pinned here. The first is the shape: the card carries no
 * input fields at all — that is what lets one layout work on a phone and on a
 * monitor — and everything changeable lives behind the edit icon. The second
 * is the name suggestion, which is the exception that proves it: typing
 * "benzine" used to produce nothing, and now the backend's candidates are
 * offered on the card itself, because a substance recognised but never
 * confirmed is what this step exists to catch. Confirming sets the tick *and*
 * the UN number, rejecting puts it away for good, and nothing happens without
 * a click.
 */
import { render, screen } from "@testing-library/react";
import { useState } from "react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ReviewLinesPanel, { DraftLine } from "./ReviewLinesPanel";
import { LineItem } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "nl" },
  }),
}));

const draft: DraftLine = { id: 1, description: "20 vaten benzine", quantity: 20, unit: "vaten" };

function resultLine(candidates: LineItem["dg_name_candidates"]): LineItem {
  return {
    line_id: 1,
    raw: "20 vaten benzine",
    description: "20 vaten benzine",
    output_description: "20 vaten benzine",
    quantity: 20,
    unit: "vaten",
    material: null,
    product_type: null,
    weight_each_kg: null,
    weight_total_kg: null,
    material_volume_m3: null,
    transport_volume_m3: null,
    length_cm: null,
    width_cm: null,
    height_cm: null,
    status: "ok",
    messages: [],
    include: true,
    dangerous_goods: false,
    dg_name_candidates: candidates,
  } as unknown as LineItem;
}

function renderPanel(lines: DraftLine[], result: LineItem[], onDraftChange = vi.fn()) {
  render(
    <ReviewLinesPanel
      draftLines={lines}
      resultLines={result}
      onDraftChange={onDraftChange}
      onRemoveLine={vi.fn()}
      onDuplicateLine={vi.fn()}
      onAddLine={vi.fn()}
      translateMessage={(m) => m}
    />,
  );
  return onDraftChange;
}

/** The panel is controlled, so typing only behaves like typing when something
 *  actually holds the lines. The wizard does; a bare spy does not, and the
 *  field would keep re-rendering its old value under the keystrokes. */
function StatefulPanel({ lines, result, onChange }: {
  lines: DraftLine[];
  result: LineItem[];
  onChange: (lines: DraftLine[]) => void;
}) {
  const [current, setCurrent] = useState(lines);
  return (
    <ReviewLinesPanel
      draftLines={current}
      resultLines={result}
      onDraftChange={(next) => {
        setCurrent(next);
        onChange(next);
      }}
      onRemoveLine={vi.fn()}
      onDuplicateLine={vi.fn()}
      onAddLine={vi.fn()}
      translateMessage={(m) => m}
    />
  );
}

const petrol = [{ un: "1203", name: "BENZINE (MOTOR SPIRIT)", class: "3" }];

describe("DG name suggestion", () => {
  it("confirming sets the tick and carries the UN number", async () => {
    const onDraftChange = renderPanel([draft], [resultLine(petrol)]);
    await userEvent.click(screen.getAllByRole("button", { name: "review.dgApply" })[0]);
    const updated = onDraftChange.mock.calls[onDraftChange.mock.calls.length - 1][0] as DraftLine[];
    expect(updated[0].dangerous_goods).toBe(true);
    expect(updated[0].confirmed_un).toBe("1203");
  });

  it("rejecting puts the suggestion away for this line", async () => {
    const onDraftChange = renderPanel([draft], [resultLine(petrol)]);
    await userEvent.click(screen.getAllByRole("button", { name: "review.dgDismiss" })[0]);
    const updated = onDraftChange.mock.calls[onDraftChange.mock.calls.length - 1][0] as DraftLine[];
    expect(updated[0].dg_dismissed).toBe(true);
  });

  it("a dismissed suggestion does not come back", () => {
    renderPanel([{ ...draft, dg_dismissed: true }], [resultLine(petrol)]);
    expect(screen.queryByText("review.dgSuggestedOne")).toBeNull();
  });

  it("several candidates become a button per UN number, none pre-chosen", async () => {
    const acids = [
      { un: "1830", name: "ZWAVELZUUR met meer dan 51% zuur", class: "8" },
      { un: "2796", name: "ZWAVELZUUR met ten hoogste 51% zuur", class: "8" },
    ];
    const onDraftChange = renderPanel([draft], [resultLine(acids)]);
    expect(screen.getAllByText("review.dgSuggestedMany").length).toBeGreaterThan(0);
    await userEvent.click(screen.getAllByRole("button", { name: "UN 2796" })[0]);
    const updated = onDraftChange.mock.calls[onDraftChange.mock.calls.length - 1][0] as DraftLine[];
    expect(updated[0].confirmed_un).toBe("2796");
    expect(updated[0].dangerous_goods).toBe(true);
  });

  it("without candidates there is no chip", () => {
    renderPanel([draft], [resultLine([])]);
    expect(screen.queryByText("review.dgSuggestedOne")).toBeNull();
    expect(screen.queryByText("review.dgSuggestedMany")).toBeNull();
  });
});

describe("the card and its edit dialog", () => {
  it("the card itself holds nothing you can type in", () => {
    renderPanel([draft], [resultLine([])]);
    // The whole reason one layout now works at every width: text reflows where
    // a row of input fields cannot. The only control on a card is a button.
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("spinbutton")).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("shows what the line says, read-only", () => {
    renderPanel([{ ...draft, quantity: 20, unit: "vaten" }], [resultLine([])]);
    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.getByText("vaten")).toBeInTheDocument();
    expect(screen.getByText("20 vaten benzine")).toBeInTheDocument();
  });

  it("the edit icon opens a dialog with the fields in it", async () => {
    renderPanel([draft], [resultLine([])]);
    expect(screen.queryByRole("dialog")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "review.editLine" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(screen.getByLabelText("review.quantity")).toBeInTheDocument();
  });

  it("changing a value in the dialog changes the line", async () => {
    const onChange = vi.fn();
    render(<StatefulPanel lines={[draft]} result={[resultLine([])]} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "review.editLine" }));
    const quantity = screen.getByLabelText("review.quantity");
    await userEvent.clear(quantity);
    await userEvent.type(quantity, "35");
    const updated = onChange.mock.calls[onChange.mock.calls.length - 1][0] as DraftLine[];
    expect(updated[0].quantity).toBe(35);
  });

  it("closes on Escape and on the done button", async () => {
    renderPanel([draft], [resultLine([])]);
    await userEvent.click(screen.getByRole("button", { name: "review.editLine" }));
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "review.editLine" }));
    await userEvent.click(screen.getByRole("button", { name: "review.doneEditing" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("the dimensions read as one measurement rather than three cells", async () => {
    renderPanel([{ ...draft, length_cm: 200, width_cm: 80, height_cm: 40 }], [resultLine([])]);
    // A secondary field: what you scan by stays on the collapsed card, the
    // rest is one tap away.
    await userEvent.click(screen.getByRole("button", { name: /records.viewMore/ }));
    expect(screen.getByText("200 × 80 × 40")).toBeInTheDocument();
  });
});
