/**
 * The settings, grouped into tabs.
 *
 * One long scroll put the personal fields and the instance-wide ones in a
 * single list, which they are emphatically not: a theme sits beside a switch
 * that decides whether this installation talks to the internet at all. The
 * tabs separate them, the dropdown does the same on a phone where a tab row
 * would wrap or scroll out of sight, and the administrator's groups exist
 * only for an administrator.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SettingsPage from "./SettingsPage";
import { User } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, vars?: Record<string, unknown>) =>
      vars && typeof vars.defaultValue === "string" ? String(vars.defaultValue) : key,
    i18n: { language: "nl" },
  }),
}));

vi.mock("../api/client", () => ({
  api: {
    health: vi.fn().mockResolvedValue({ version: "1.115.0" }),
    settingsOptions: vi.fn().mockResolvedValue({ modalities: ["road"], units: [] }),
    instanceSettings: vi.fn().mockResolvedValue({}),
    assistantStatus: vi.fn().mockResolvedValue({
      mode: "deterministic", installed: false, available: true, installable: true,
      download: { state: "idle" },
    }),
    // The maintenance tab's panels ask for their state on mount.
    updateCapability: vi.fn().mockResolvedValue({ available: false }),
    updateState: vi.fn().mockResolvedValue({ current: "1.115.0", state: null }),
    unCardStoreStatus: vi.fn().mockResolvedValue({
      local: { installed: false }, remote: null,
    }),
    // My details carries the second factor, which asks for its own state.
    twoFactorStatus: vi.fn().mockResolvedValue({
      active: false, method: "", required: false, recovery_codes_left: 0,
    }),
  },
}));

const preferences = {
  theme: "system", language: "nl", default_modality: "", default_unit: "pcs",
  prefill_documents: true, consignor_name: "", consignor_address: "",
  consignor_contact: "", carrier_name: "", loading_point: "",
  emergency_contact: "", signature_image: "",
};

vi.mock("../settings/preferences", () => ({
  usePreferences: () => ({ preferences, save: vi.fn(), loaded: true }),
}));

const userOf = (role: string) => ({ id: 1, username: "u", role, active: true }) as unknown as User;

beforeEach(() => vi.clearAllMocks());

describe("SettingsPage tabs", () => {
  it("opens on appearance and shows only that group", async () => {
    render(<SettingsPage user={userOf("user")} />);
    expect(await screen.findByText("settings.appearance")).toBeTruthy();
    expect(screen.queryByText("settings.myDetails")).toBeNull();
    expect(screen.queryByText("settings.shipmentDefaults")).toBeNull();
  });

  it("switching tabs shows the other group", async () => {
    render(<SettingsPage user={userOf("user")} />);
    await userEvent.click(await screen.findByRole("tab", { name: "settings.tabDetails" }));
    expect(screen.getByText("settings.myDetails")).toBeTruthy();
    expect(screen.queryByText("settings.appearance")).toBeNull();
    // The save button travels with the personal tabs; one draft, one button.
    expect(screen.getByRole("button", { name: "settings.save" })).toBeTruthy();
  });

  it("the phone dropdown selects the same groups", async () => {
    render(<SettingsPage user={userOf("user")} />);
    const picker = await screen.findByLabelText("settings.tabPick");
    await userEvent.selectOptions(picker, "shipment");
    expect(screen.getByText("settings.shipmentDefaults")).toBeTruthy();
  });

  it("the administrator groups exist only for an administrator", async () => {
    const { unmount } = render(<SettingsPage user={userOf("user")} />);
    await screen.findByText("settings.appearance");
    expect(screen.queryByRole("tab", { name: "settings.tabAdmin" })).toBeNull();
    expect(screen.queryByRole("tab", { name: "settings.tabMaintenance" })).toBeNull();
    unmount();

    render(<SettingsPage user={userOf("admin")} />);
    expect(await screen.findByRole("tab", { name: "settings.tabAdmin" })).toBeTruthy();
    // Maintenance holds the action panels: updating, the UN card set and
    // the assistant's model live here, away from the saved settings.
    await userEvent.click(screen.getByRole("tab", { name: "settings.tabMaintenance" }));
    await waitFor(() => expect(screen.getByText("settings.adminUpdates")).toBeTruthy());
    expect(screen.getByText("settings.unCardsStoreTitle")).toBeTruthy();
    await waitFor(() => expect(screen.getByText("settings.assistantTitle")).toBeTruthy());
    expect(screen.queryByRole("button", { name: "settings.saveAdmin" })).toBeNull();
  });
});
