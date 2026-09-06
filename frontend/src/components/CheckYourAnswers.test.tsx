/**
 * The last look before the documents are made.
 *
 * Two things are pinned: an answer nobody gave says so rather than showing an
 * empty space, and every row that *is* something to change carries the way to
 * change it. A summary you cannot act on is a decoration.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import CheckYourAnswers from "./CheckYourAnswers";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }),
}));

describe("check your answers", () => {
  it("shows the answers as they stand", () => {
    render(
      <CheckYourAnswers
        title="Controleer uw antwoorden"
        rows={[
          { key: "consignor", label: "Afzender", value: "Mooiweer BV" },
          { key: "route", label: "Route", value: "Rotterdam → Antwerpen" },
        ]}
      />,
    );
    expect(screen.getByText("Mooiweer BV")).toBeInTheDocument();
    expect(screen.getByText("Rotterdam → Antwerpen")).toBeInTheDocument();
  });

  it("says when nothing was given instead of showing a gap", () => {
    render(
      <CheckYourAnswers title="x" rows={[{ key: "consignee", label: "Geadresseerde", value: "", wanted: true }]} />,
    );
    expect(screen.getByText("check.nothingGiven")).toBeInTheDocument();
  });

  it("every row that can be changed says so, by name", async () => {
    const onChange = vi.fn();
    render(
      <CheckYourAnswers
        title="x"
        rows={[
          { key: "consignor", label: "Afzender", value: "Mooiweer BV", onChange },
          { key: "assessment", label: "Beoordeling", value: "Geen gevaarlijke stoffen" },
        ]}
      />,
    );
    // The assessment is derived, so it is not something to change here.
    expect(screen.getAllByRole("button")).toHaveLength(1);
    await userEvent.click(screen.getByRole("button", { name: /Afzender/ }));
    expect(onChange).toHaveBeenCalled();
  });

  it("the row's label names what the change button changes", () => {
    render(
      <CheckYourAnswers
        title="x"
        rows={[{ key: "route", label: "Route", value: "Rotterdam", onChange: vi.fn() }]}
      />,
    );
    const button = screen.getByRole("button");
    expect(within(button).getByText(/Route/)).toBeInTheDocument();
  });
});
