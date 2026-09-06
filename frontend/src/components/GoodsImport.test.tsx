/**
 * Getting a list of goods in, from the goods step itself.
 *
 * Three things are pinned. The entrance: pasting and choosing a file are
 * actions with names on the step, not an icon inside a dialog somebody has to
 * open first. The question: a file whose heading row was recognised leaves
 * nothing to ask about and simply goes in, while a guessed one shows its column
 * mapping before anything is imported — asking every time is how a column
 * question becomes something people click past. And the choice: a shipment with
 * nothing in it is not asked whether to add or replace, because there is
 * nothing to replace.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";

import GoodsImport from "./GoodsImport";
import { ToastProvider } from "../toast/ToastProvider";
import { api, ImportAnalysis } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options && "count" in options ? `${key}:${options.count}` : key,
    i18n: { language: "nl" },
  }),
}));

const RECOGNISED: ImportAnalysis = {
  source: "header",
  has_header: true,
  mapping: { description: 0, quantity: 1, unit: 2 },
  columns: [
    { index: 0, header: "Omschrijving", samples: ["Stalen hoekprofiel"] },
    { index: 1, header: "Aantal", samples: ["8"] },
    { index: 2, header: "Eenheid", samples: ["stuks"] },
  ],
};

const GUESSED: ImportAnalysis = { ...RECOGNISED, source: "position", has_header: false };

const FILE = new File(["x"], "goods.xlsx", { type: "application/vnd.ms-excel" });

function renderImport(hasLines: boolean, onImport = vi.fn()) {
  render(
    <ToastProvider>
      <GoodsImport hasLines={hasLines} onImport={onImport} />
    </ToastProvider>,
  );
  return onImport;
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("the entrance on the goods step", () => {
  it("offers pasting and choosing a file by name, without opening anything", () => {
    renderImport(false);
    expect(screen.getByRole("button", { name: "review.importPaste" })).toBeInTheDocument();
    expect(screen.getByText("review.importFile")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("the paste area opens in place and takes the focus", async () => {
    renderImport(false);
    await userEvent.click(screen.getByRole("button", { name: "review.importPaste" }));
    const area = screen.getByLabelText("review.importPaste");
    expect(area).toBeInTheDocument();
    await waitFor(() => expect(area).toHaveFocus());
  });
});

describe("asking only where there is doubt", () => {
  it("a recognised file goes straight in when there is nothing to replace", async () => {
    vi.spyOn(api, "parseWizardImportFile").mockResolvedValue({
      text: "Stalen hoekprofiel | 8 | stuks", has_header: true, analysis: RECOGNISED,
      rows: [["Omschrijving", "Aantal", "Eenheid"], ["Stalen hoekprofiel", "8", "stuks"]],
    });
    const onImport = renderImport(false);
    await userEvent.upload(screen.getByLabelText("review.importFile", { selector: "input" }), FILE);
    await waitFor(() => expect(onImport).toHaveBeenCalledWith("Stalen hoekprofiel | 8 | stuks", "replace"));
    // Nothing was asked, so nothing is left standing.
    expect(screen.queryByLabelText("review.importPaste")).toBeNull();
  });

  it("a guessed file shows its columns before anything is imported", async () => {
    vi.spyOn(api, "parseWizardImportFile").mockResolvedValue({
      text: "Stalen hoekprofiel | 8 | stuks", has_header: false, analysis: GUESSED,
      rows: [["Stalen hoekprofiel", "8", "stuks"]],
    });
    const onImport = renderImport(false);
    await userEvent.upload(screen.getByLabelText("review.importFile", { selector: "input" }), FILE);
    expect(await screen.findByText("import.guessedColumns")).toBeInTheDocument();
    expect(onImport).not.toHaveBeenCalled();
  });

  it("says what it read and what it had to skip", async () => {
    vi.spyOn(api, "parseWizardImportFile").mockResolvedValue({
      text: "Stalen hoekprofiel | 8 | stuks", has_header: false, analysis: GUESSED,
      rows: [["Stalen hoekprofiel", "8", "stuks"], ["", "3", "stuks"], ["", "", ""]],
    });
    renderImport(false);
    await userEvent.upload(screen.getByLabelText("review.importFile", { selector: "input" }), FILE);
    expect(await screen.findByText(/review.importRead:1/)).toBeInTheDocument();
    expect(screen.getByText(/review.importSkipped:2/)).toBeInTheDocument();
  });
});

describe("adding or replacing", () => {
  it("an empty shipment is not asked which of the two it wants", async () => {
    const onImport = renderImport(false);
    await userEvent.click(screen.getByRole("button", { name: "review.importPaste" }));
    await userEvent.type(screen.getByLabelText("review.importPaste"), "Stalen plaat | 4 | stuks");
    expect(screen.queryByRole("button", { name: "review.importAppend" })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "review.importConfirm" }));
    expect(onImport).toHaveBeenCalledWith("Stalen plaat | 4 | stuks", "replace");
  });

  it("a shipment with lines is offered both, by name", async () => {
    const onImport = renderImport(true);
    await userEvent.click(screen.getByRole("button", { name: "review.importPaste" }));
    await userEvent.type(screen.getByLabelText("review.importPaste"), "Stalen plaat | 4 | stuks");
    expect(screen.getByRole("button", { name: "review.importReplace" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "review.importAppend" }));
    expect(onImport).toHaveBeenCalledWith("Stalen plaat | 4 | stuks", "append");
  });

  it("a recognised file with lines already there still asks which", async () => {
    vi.spyOn(api, "parseWizardImportFile").mockResolvedValue({
      text: "Stalen hoekprofiel | 8 | stuks", has_header: true, analysis: RECOGNISED,
      rows: [["Omschrijving", "Aantal", "Eenheid"], ["Stalen hoekprofiel", "8", "stuks"]],
    });
    const onImport = renderImport(true);
    await userEvent.upload(screen.getByLabelText("review.importFile", { selector: "input" }), FILE);
    expect(await screen.findByRole("button", { name: "review.importAppend" })).toBeInTheDocument();
    expect(onImport).not.toHaveBeenCalled();
  });

  it("nothing is imported from an empty paste", async () => {
    const onImport = renderImport(false);
    await userEvent.click(screen.getByRole("button", { name: "review.importPaste" }));
    expect(screen.getByRole("button", { name: "review.importConfirm" })).toBeDisabled();
    expect(onImport).not.toHaveBeenCalled();
  });
});
