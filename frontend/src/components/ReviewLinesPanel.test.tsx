/**
 * The goods step: a line you edit where it stands, a dialog for the rest, and
 * a snackbar that asks.
 *
 * What is pinned here is the trade this step makes. The four things a
 * consignment is made of — description, quantity, unit, and the outcome — are
 * on the line, and changing a quantity is one keystroke rather than open, type,
 * close. Everything else, the thirteen fields the old table died of, stays in
 * the detail dialog and is not creeping back onto the row.
 *
 * Then the two rules that keep the numbers honest: a figure is never shown for
 * input it was not computed from, and a line whose own text has not moved keeps
 * its figures, marked as not yet rechecked, rather than blinking away on every
 * keystroke.
 *
 * And the name recognition, which is the one thing on a line that asks the user
 * a *question*, and therefore asks it where the application asks things: a
 * snackbar that stays until answered. Accepting sets the tick *and* the UN
 * number, closing it is a final no, and nothing happens without a click.
 */
import { render, screen, within } from "@testing-library/react";
import { useState } from "react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ReviewLinesPanel, { DraftLine } from "./ReviewLinesPanel";
import { ToastProvider } from "../toast/ToastProvider";
import { LineItem } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options && "number" in options ? `${key}:${options.number}` : key,
    i18n: { language: "nl" },
  }),
}));

const draft: DraftLine = { id: 1, description: "20 vaten benzine", quantity: 20, unit: "vaten" };

function resultLine(candidates: LineItem["dg_name_candidates"], over: Partial<LineItem> = {}): LineItem {
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
    ...over,
  } as unknown as LineItem;
}

function renderPanel(lines: DraftLine[], result?: LineItem[], extra: Record<string, unknown> = {}) {
  const onDraftChange = (extra.onDraftChange as ReturnType<typeof vi.fn>) ?? vi.fn();
  render(
    <ToastProvider>
      <ReviewLinesPanel
        draftLines={lines}
        resultLines={result}
        onDraftChange={onDraftChange}
        onRemoveLine={vi.fn()}
        onDuplicateLine={vi.fn()}
        onAddLine={vi.fn()}
        translateMessage={(m) => m}
        {...extra}
      />
    </ToastProvider>,
  );
  return onDraftChange;
}

/** The panel is controlled, so typing only behaves like typing when something
 *  actually holds the lines. The wizard does; a bare spy does not, and the
 *  field would keep re-rendering its old value under the keystrokes. */
function StatefulPanel({ lines, result, onChange, replaceWith, onAddLine, clearResultOnEdit }: {
  lines: DraftLine[];
  result?: LineItem[];
  onChange: (lines: DraftLine[]) => void;
  /** Swapped in without remounting, the way an import replaces the lines. */
  replaceWith?: DraftLine[];
  onAddLine?: () => void;
  /** What the wizard does: a changed line clears the calculated result. */
  clearResultOnEdit?: boolean;
}) {
  const [current, setCurrent] = useState(lines);
  const [computed, setComputed] = useState(result);
  return (
    <ToastProvider>
      {replaceWith && (
        <button type="button" onClick={() => setCurrent(replaceWith)}>
          simulate import
        </button>
      )}
      <ReviewLinesPanel
        draftLines={current}
        resultLines={computed}
        onDraftChange={(next) => {
          setCurrent(next);
          if (clearResultOnEdit) setComputed(undefined);
          onChange(next);
        }}
        onRemoveLine={vi.fn()}
        onDuplicateLine={vi.fn()}
        onAddLine={onAddLine ?? (() => {
          setCurrent((lines_) => [...lines_, {
            id: Math.max(...lines_.map((l) => l.id)) + 1, description: "", quantity: 1, unit: "stuks",
          }]);
        })}
        translateMessage={(m) => m}
      />
    </ToastProvider>
  );
}

const petrol = [{ un: "1203", name: "BENZINE (MOTOR SPIRIT)", class: "3" }];

describe("editing a line where it stands", () => {
  it("the description, the quantity and the unit are on the row itself", () => {
    renderPanel([draft], [resultLine([])]);
    expect(screen.getByLabelText("review.descriptionOfLine:1")).toHaveValue("20 vaten benzine");
    expect(screen.getByLabelText("review.quantityOfLine:1")).toHaveValue(20);
    expect(screen.getByLabelText("review.unitOfLine:1")).toBeInTheDocument();
  });

  it("changing a quantity costs the keystroke and nothing else", async () => {
    const onChange = vi.fn();
    render(<StatefulPanel lines={[draft]} result={[resultLine([])]} onChange={onChange} />);
    const quantity = screen.getByLabelText("review.quantityOfLine:1");
    await userEvent.clear(quantity);
    await userEvent.type(quantity, "35");
    const updated = onChange.mock.calls[onChange.mock.calls.length - 1][0] as DraftLine[];
    expect(updated[0].quantity).toBe(35);
    // No window opened for it: that is the whole point of the row.
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("the row carries the four fields and not the thirteen", () => {
    renderPanel([{ ...draft, length_cm: 200, width_cm: 80, height_cm: 40 }], [resultLine([])]);
    // Dimensions are shown as text under the row, not as fields on it.
    expect(screen.getByText(/200 × 80 × 40 cm/)).toBeInTheDocument();
    expect(screen.queryByLabelText("review.length_cm")).toBeNull();
    expect(screen.queryByLabelText("review.wallThickness")).toBeNull();
  });

  it("the details icon opens the dialog with the rest of the fields", async () => {
    renderPanel([draft], [resultLine([])]);
    expect(screen.queryByRole("dialog")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "review.lineDetails" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText("review.quantity")).toBeInTheDocument();
  });

  it("a new line gets the cursor in its description", async () => {
    render(<StatefulPanel lines={[draft]} onChange={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "review.addLine" }));
    expect(screen.getByLabelText("review.descriptionOfLine:2")).toHaveFocus();
  });

  it("Enter on the last line makes the next one", async () => {
    const onAddLine = vi.fn();
    render(<StatefulPanel lines={[draft]} onChange={vi.fn()} onAddLine={onAddLine} />);
    await userEvent.click(screen.getByLabelText("review.quantityOfLine:1"));
    await userEvent.keyboard("{Enter}");
    expect(onAddLine).toHaveBeenCalled();
  });

  it("Enter on an earlier line moves to the next one instead of adding", async () => {
    const onAddLine = vi.fn();
    const second: DraftLine = { id: 2, description: "10 pallets", quantity: 10, unit: "pallets" };
    render(<StatefulPanel lines={[draft, second]} onChange={vi.fn()} onAddLine={onAddLine} />);
    await userEvent.click(screen.getByLabelText("review.quantityOfLine:1"));
    await userEvent.keyboard("{Enter}");
    expect(onAddLine).not.toHaveBeenCalled();
    expect(screen.getByLabelText("review.descriptionOfLine:2")).toHaveFocus();
  });
});

describe("figures while the calculation runs", () => {
  it("a line that did not change keeps its figures, marked as not yet rechecked", async () => {
    const first = { ...draft, id: 1 };
    const second: DraftLine = { id: 2, description: "10 pallets", quantity: 10, unit: "pallets" };
    render(
      <StatefulPanel
        lines={[first, second]}
        result={[resultLine([], { weight_total_kg: 880 }), resultLine([], { line_id: 2, weight_total_kg: 120 })]}
        onChange={vi.fn()}
        clearResultOnEdit
      />,
    );
    expect(screen.getByText("880")).toBeInTheDocument();

    // Typing in line 2 clears the whole result, as the wizard does.
    await userEvent.type(screen.getByLabelText("review.descriptionOfLine:2"), "x");

    // Line 1 keeps its weight and says it is waiting to be rechecked.
    expect(screen.getByText("880")).toBeInTheDocument();
    expect(screen.getAllByText("review.toBeRechecked").length).toBe(2);
    // Line 2's weight is gone: it belonged to the previous description.
    expect(screen.queryByText("120")).toBeNull();
  });

  it("without a result there are no figures at all", () => {
    renderPanel([draft]);
    expect(screen.getByText("review.toBeRechecked")).toBeInTheDocument();
    expect(screen.queryByText("status.ok")).toBeNull();
  });
});

describe("what the import left behind", () => {
  const settled = (id: number, description: string) =>
    ({ id, description, quantity: 1, unit: "stuks" }) as DraftLine;

  it("says how many lines want attention, and narrows to them", async () => {
    const lines = [settled(1, "Stalen plaat"), settled(2, "Diverse onderdelen"), settled(3, "Stalen buis")];
    const results = [
      resultLine([], { line_id: 1, weight_total_kg: 100 }),
      resultLine([], { line_id: 2, status: "needs_review", messages: ["no_dimensions"] }),
      resultLine([], { line_id: 3, weight_total_kg: 50 }),
    ];
    renderPanel(lines, results);
    expect(screen.getByText("review.attentionSummary")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "review.onlyAttention" }));
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByLabelText("review.descriptionOfLine:2")).toHaveValue("Diverse onderdelen");

    await userEvent.click(screen.getByRole("button", { name: "review.showAllLines" }));
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });

  it("says nothing when every line came out settled", () => {
    renderPanel([draft], [resultLine([], { weight_total_kg: 100 })]);
    expect(screen.queryByText("review.attentionSummary")).toBeNull();
    expect(screen.queryByRole("button", { name: "review.onlyAttention" })).toBeNull();
  });
});

describe("the DG name recognition, asked in a snackbar", () => {
  it("accepting sets the tick and carries the UN number", async () => {
    const onDraftChange = renderPanel([draft], [resultLine(petrol)]);
    await userEvent.click(await screen.findByRole("button", { name: "review.dgApply" }));
    const updated = onDraftChange.mock.calls[onDraftChange.mock.calls.length - 1][0] as DraftLine[];
    expect(updated[0].dangerous_goods).toBe(true);
    expect(updated[0].confirmed_un).toBe("1203");
  });

  it("accepting closes the snackbar", async () => {
    render(<StatefulPanel lines={[draft]} result={[resultLine(petrol)]} onChange={vi.fn()} />);
    await userEvent.click(await screen.findByRole("button", { name: "review.dgApply" }));
    expect(screen.queryByText("review.dgToastOne")).toBeNull();
  });

  it("closing the snackbar is a no, and a final one", async () => {
    const onDraftChange = renderPanel([draft], [resultLine(petrol)]);
    await screen.findByText("review.dgToastOne:1");
    await userEvent.click(screen.getByRole("button", { name: "toast.dismiss" }));
    const updated = onDraftChange.mock.calls[onDraftChange.mock.calls.length - 1][0] as DraftLine[];
    expect(updated[0].dg_dismissed).toBe(true);
  });

  it("a rejected recognition is not asked again", () => {
    renderPanel([{ ...draft, dg_dismissed: true }], [resultLine(petrol)]);
    expect(screen.queryByText("review.dgToastOne:1")).toBeNull();
  });

  it("an already confirmed line is not asked again either", () => {
    renderPanel([{ ...draft, confirmed_un: "1203" }], [resultLine(petrol)]);
    expect(screen.queryByText("review.dgToastOne:1")).toBeNull();
  });

  it("several candidates become a button per UN number, none pre-chosen", async () => {
    const acids = [
      { un: "1830", name: "ZWAVELZUUR met meer dan 51% zuur", class: "8" },
      { un: "2796", name: "ZWAVELZUUR met ten hoogste 51% zuur", class: "8" },
    ];
    const onDraftChange = renderPanel([draft], [resultLine(acids)]);
    expect(await screen.findByText("review.dgToastMany:1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "UN 1830" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "UN 2796" }));
    const updated = onDraftChange.mock.calls[onDraftChange.mock.calls.length - 1][0] as DraftLine[];
    expect(updated[0].confirmed_un).toBe("2796");
    expect(updated[0].dangerous_goods).toBe(true);
  });

  it("without candidates nothing is asked", () => {
    renderPanel([draft], [resultLine([])]);
    expect(screen.queryByText("review.dgToastOne:1")).toBeNull();
    expect(screen.queryByText("review.dgToastMany:1")).toBeNull();
  });

  it("asks again about a line number that a replacing import reused", async () => {
    // An import with "replace" numbers from 1 again. The guard against a
    // second toast used to remember the line-and-substance key forever, so a
    // new consignment whose first line held the same substance as the one
    // already answered was never asked about at all.
    render(
      <StatefulPanel
        lines={[draft]}
        result={[resultLine(petrol)]}
        onChange={vi.fn()}
        replaceWith={[{ id: 1, description: "10 vaten benzine", quantity: 10, unit: "vaten" }]}
      />,
    );
    await screen.findByText("review.dgToastOne:1");
    await userEvent.click(screen.getByRole("button", { name: "review.dgApply" }));
    expect(screen.queryByText("review.dgToastOne:1")).toBeNull();

    // The panel stays mounted, as it does in the wizard: the same line number
    // and the same substance, but a fresh line nobody has answered for.
    await userEvent.click(screen.getByRole("button", { name: "simulate import" }));
    expect(await screen.findByText("review.dgToastOne:1")).toBeInTheDocument();
  });

  it("the recognition is off the row entirely", async () => {
    renderPanel([draft], [resultLine(petrol)]);
    await screen.findByText("review.dgToastOne:1");
    // One place asks it, and it is not the row: the row stays what is carried.
    expect(screen.getAllByText("review.dgToastOne:1")).toHaveLength(1);
  });

  it("an answered line shows its UN number on the row", () => {
    renderPanel([{ ...draft, confirmed_un: "1203", dangerous_goods: true }], [resultLine([])]);
    const rows = screen.getAllByRole("listitem");
    expect(within(rows[0]).getByText("UN 1203")).toBeInTheDocument();
  });
});
