/**
 * The name suggestion on the lines step.
 *
 * Typing "benzine" used to produce nothing: the DG tick stayed off and the UN
 * number had to be typed again on the DG step, while the backend's name index
 * had known the substance all along. Now the backend sends candidates and this
 * panel proposes them. The rules under test are the ones that keep a
 * suggestion a suggestion: confirming sets the tick *and* the UN number,
 * rejecting puts it away for good, and nothing happens without a click.
 */
import { render, screen } from "@testing-library/react";
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
