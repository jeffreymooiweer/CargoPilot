/**
 * Groupage from the history: the kept shipments the viewer may see become
 * consignments on the vehicle with one click, through the same export the
 * file route reads.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GroupagePage from "./GroupagePage";
import { ToastProvider } from "../toast/ToastProvider";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options && "count" in options ? `${key}:${options.count}` : key,
    i18n: { language: "nl" },
  }),
}));

const settings = { history_enabled: true };
vi.mock("../settings/preferences", () => ({
  usePreferences: () => ({ publicSettings: settings, preferences: {}, loaded: true, mode: "organisation" }),
}));

const api = vi.hoisted(() => ({
  shipments: vi.fn(),
  shipment: vi.fn(),
  dgTrip: vi.fn(),
}));
vi.mock("../api/client", () => ({ api }));

const kept = [
  {
    id: 7, reference: "CP-2026-100", modality: "road", language: "nl", regulations: ["ADR"],
    consignor_name: "Afzender BV", consignee_name: "Ontvanger GmbH", goods_count: 3,
    has_dangerous_goods: true, has_documents: true, created_by: "ada",
    created_at: "2026-09-05T08:00:00Z", updated_at: "2026-09-05T08:00:00Z",
  },
  {
    id: 8, reference: "CP-2026-101", modality: "road", language: "nl", regulations: [],
    consignor_name: "Afzender BV", consignee_name: "", goods_count: 1,
    has_dangerous_goods: false, has_documents: false, created_by: "",
    created_at: "2026-09-04T08:00:00Z", updated_at: "2026-09-04T08:00:00Z",
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  settings.history_enabled = true;
  api.shipments.mockResolvedValue({ items: kept, total: 2, page: 1, per_page: 50 });
  api.shipment.mockResolvedValue({
    ...kept[0],
    snapshot: {},
    export: {
      format: "cargopilot.shipment",
      regulations: ["ADR"],
      // The wizard's own field name; a consignment is named by its reference,
      // not by its consignor, or three from one shipper look alike.
      consignment: { reference: "CP-2026-100", consignor_name: "Afzender BV" },
      dangerous_goods: [{ line_id: "1", products: [{ un_number: "1203" }, { un_number: "1263" }] }],
    },
  });
});

function renderPage() {
  return render(
    <ToastProvider>
      <GroupagePage />
    </ToastProvider>,
  );
}

describe("groepage uit de historie", () => {
  it("toont het kiesvak alleen waar de historie aanstaat", () => {
    settings.history_enabled = false;
    renderPage();
    expect(screen.queryByText("groupage.fromHistory")).toBeNull();
    expect(api.shipments).not.toHaveBeenCalled();
  });

  it("zet een bewaarde zending met één klik op het voertuig, en niet twee keer", async () => {
    renderPage();
    const list = await screen.findByTestId("groupage-history");
    expect(list).toHaveTextContent("CP-2026-100");
    // The one without dangerous goods has nothing to add.
    expect(screen.getByText("groupage.noDgShort")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "groupage.addFromHistory" }));
    await waitFor(() => expect(api.shipment).toHaveBeenCalledWith(7));
    expect(await screen.findByText("groupage.onTheVehicle:1")).toBeInTheDocument();
    expect(screen.getByLabelText("groupage.consignmentName")).toHaveValue("CP-2026-100");
    expect(screen.getByText("groupage.positions:2")).toBeInTheDocument();
    // Added once: the button now says so and is disabled.
    expect(screen.getByRole("button", { name: "groupage.alreadyAdded" })).toBeDisabled();
  });

  it("stuurt de zoekopdracht mee", async () => {
    renderPage();
    await screen.findByTestId("groupage-history");
    await userEvent.type(screen.getByPlaceholderText("groupage.searchHistory"), "101");
    await waitFor(() =>
      expect(api.shipments).toHaveBeenLastCalledWith(expect.objectContaining({ q: "101" })),
    );
  });
});
