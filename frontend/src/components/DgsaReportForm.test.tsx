/**
 * The adviser's form: drawn from the server's definition, proposals taken
 * over on request and never by themselves, answers saved in the form's shape.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DgsaFormResponse, DgsaReport } from "../api/client";
import DgsaReportForm from "./DgsaReportForm";
import { ToastProvider } from "../toast/ToastProvider";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options?.value !== undefined ? `${key}:${options.value}` : key,
    i18n: { language: "nl" },
  }),
}));

const api = vi.hoisted(() => ({ saveDgsaAnswers: vi.fn() }));
vi.mock("../api/client", () => ({ api }));

const report = {
  year: 2026, language: "nl", by_class: [{ class: "3", shipments: 2, products: 3, quantity_kg: 1600, quantity_l: 100, quantity_unknown: 0 }],
} as unknown as DgsaReport;

const form: DgsaFormResponse = {
  report,
  scope: "",
  definition: {
    source: "DVSA",
    answer_labels: { yes: "Ja", no: "Nee", na: "N.v.t.", details: "Toelichting" },
    sections: [
      { key: "company", title: "Bedrijfsgegevens" },
      { key: "hcdg", title: "Hoog risico" },
      { key: "transportation", title: "Vervoer" },
      { key: "class7", title: "Alleen klasse 7", only_with_class: "7" },
    ],
    questions: [
      { key: "company_name", section: "company", kind: "text", text: "Bedrijfsnaam", prefill: "brand_name" },
      { key: "hcdg_carried", section: "hcdg", kind: "yesnona", text: "HCDG vervoerd?", checklist: "DGSA17", prefill: "hcdg" },
      { key: "transport_table", section: "transportation", kind: "transport_table", text: "Tabel", prefill: "transport_table",
        operations: ["consigning", "carriage"], operation_labels: { consigning: "Verzenden", carriage: "Vervoeren" },
        bands: ["<5", "5-50"], classes: ["3", "9"], band_note: "ton per jaar" },
      { key: "c7_emergency", section: "class7", kind: "yesno", text: "Klasse 7 vraag" },
    ],
    checklist: { title: "Checklist", columns: {}, additional_heading: "", items: [] },
  },
  prefill: {
    company_name: "Mooiweer Logistics",
    hcdg_carried: { answer: "no", details: "" },
    transport_table: { "3": { operations: ["consigning"], band: "", quantity_kg: 1600, quantity_l: 100, shipments: 2 } },
  },
  answers: {},
  saved_at: null,
  has_signature: false,
};

beforeEach(() => {
  vi.clearAllMocks();
  api.saveDgsaAnswers.mockImplementation(async (_y: number, _d: string, answers: unknown) => ({
    ok: true, saved_at: "2026-09-05T10:00:00Z", answers,
  }));
});

function renderForm() {
  const onSaved = vi.fn();
  render(
    <ToastProvider>
      <DgsaReportForm year={2026} department="" language="nl" form={form} onSaved={onSaved} />
    </ToastProvider>,
  );
  return onSaved;
}

describe("het DVSA-formulier", () => {
  it("tekent de secties uit de definitie en verbergt het klasse 7-blok zonder klasse 7", () => {
    renderForm();
    expect(screen.getByText("Bedrijfsgegevens")).toBeInTheDocument();
    expect(screen.getByText("Vervoer")).toBeInTheDocument();
    expect(screen.queryByText("Alleen klasse 7")).toBeNull();
    // The counted figures are shown beside the class, not written into it.
    expect(screen.getByText(/1.600 kg · 100 L · 2×|1,600 kg · 100 L · 2×/)).toBeInTheDocument();
    expect(screen.getByLabelText("3 Verzenden")).not.toBeChecked();
  });

  it("neemt een voorstel alleen over op verzoek en bewaart in de vorm van het formulier", async () => {
    const onSaved = renderForm();
    expect(screen.getByRole("button", { name: "dgsa.save" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "dgsa.takeOverValue:Mooiweer Logistics" }));
    expect(screen.getByDisplayValue("Mooiweer Logistics")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "dgsa.takeOverTable" }));
    expect(screen.getByLabelText("3 Verzenden")).toBeChecked();
    await userEvent.click(screen.getByLabelText("3 Vervoeren"));
    await userEvent.selectOptions(screen.getByLabelText("3 dgsa.band"), "5-50");
    await userEvent.click(screen.getByLabelText("Ja"));
    await userEvent.type(screen.getByLabelText("HCDG vervoerd? — Toelichting"), "UN 1017");

    await userEvent.click(screen.getByRole("button", { name: "dgsa.save" }));
    await waitFor(() => expect(api.saveDgsaAnswers).toHaveBeenCalledTimes(1));
    const [year, department, answers] = api.saveDgsaAnswers.mock.calls[0];
    expect(year).toBe(2026);
    expect(department).toBe("");
    expect(answers).toEqual({
      company_name: "Mooiweer Logistics",
      transport_table: { "3": { operations: ["consigning", "carriage"], band: "5-50" } },
      hcdg_carried: { answer: "yes", details: "UN 1017" },
    });
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith("2026-09-05T10:00:00Z"));
    expect(screen.getByRole("button", { name: "dgsa.save" })).toBeDisabled();
  });
});
