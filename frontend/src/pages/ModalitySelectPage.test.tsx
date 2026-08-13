/**
 * Only road may be used to draw up documents, and the lock has three ways in.
 *
 * Rail, sea, inland waterway and air are built and reachable and *wrong* in
 * ways that do not announce themselves. Inland waterway answered its
 * separation question with the road table until v1.59.0 and still has no
 * table C, so a tank vessel consignment gets nothing at all. A half-right
 * document is worse than no document: it is signed and handed over, and the
 * consignor has no way to see which half was right.
 *
 * The reason this file exists rather than a line in the component is that the
 * tile is not the only way in. A bookmark reaches `/wizard/rail` without
 * touching a tile, and a `default_modality` set while a modality was open
 * navigates there on its own. Guarding the tiles alone guards the honest route
 * and leaves the other two open — which is the shape of lock that gets found
 * out in production rather than in review.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";

import ModalitySelectPage, {
  AVAILABLE_MODALITIES,
  MODALITIES,
  isModalityAvailable,
} from "./ModalitySelectPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }),
}));

const preferences = { default_modality: undefined as string | undefined };
vi.mock("../settings/preferences", () => ({
  usePreferences: () => ({ preferences, loaded: true }),
}));

function renderAt(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<ModalitySelectPage />} />
        <Route path="/wizard/:modality" element={<p>wizard</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("de modaliteitkeuze", () => {
  it("laat alleen wegvervoer toe", () => {
    expect([...AVAILABLE_MODALITIES]).toEqual(["road"]);
    expect(isModalityAvailable("road")).toBe(true);
    for (const key of MODALITIES.filter((m) => m !== "road")) {
      expect(isModalityAvailable(key)).toBe(false);
    }
  });

  it("zet de overige tegels op slot in plaats van ze te verbergen", () => {
    // Hiding them would raise the wrong question — "where did rail go?" — where
    // the true answer is "not yet, and here is why".
    preferences.default_modality = undefined;
    renderAt("/?choose=1");
    const tiles = screen.getAllByRole("button");
    const locked = tiles.filter((tile) => tile.hasAttribute("disabled"));
    expect(locked).toHaveLength(MODALITIES.length - 1);
    expect(screen.getAllByText("modality.locked").length).toBe(MODALITIES.length - 1);
  });

  it("doet niets als er op een vergrendelde tegel wordt geklikt", async () => {
    preferences.default_modality = undefined;
    renderAt("/?choose=1");
    const tiles = screen.getAllByRole("button");
    const locked = tiles.find((tile) => tile.hasAttribute("disabled"))!;
    await userEvent.click(locked);
    expect(screen.queryByText("wizard")).not.toBeInTheDocument();
  });

  it("opent wegvervoer gewoon", async () => {
    preferences.default_modality = undefined;
    renderAt("/?choose=1");
    const road = screen.getAllByRole("button").find((tile) => !tile.hasAttribute("disabled"))!;
    await userEvent.click(road);
    await waitFor(() => expect(screen.getByText("wizard")).toBeInTheDocument());
  });

  it("volgt een voorkeur voor een vergrendelde modaliteit niet meer", async () => {
    // The route that skips every tile: a preference set while inland waterway
    // was open would otherwise keep opening it after the lock went on.
    preferences.default_modality = "inland";
    renderAt("/");
    await waitFor(() => expect(screen.getAllByRole("button").length).toBeGreaterThan(0));
    expect(screen.queryByText("wizard")).not.toBeInTheDocument();
  });

  it("volgt een voorkeur voor wegvervoer wel", async () => {
    preferences.default_modality = "road";
    renderAt("/");
    await waitFor(() => expect(screen.getByText("wizard")).toBeInTheDocument());
  });
});
