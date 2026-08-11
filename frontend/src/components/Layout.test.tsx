/**
 * The side menu gets out of the way of the wizard, and comes back on request.
 *
 * The lines step is a table you *type* in — description, quantity, unit, cargo
 * form and two masses are all input fields — and on a laptop the fixed 200px
 * rail took enough width off it that the fields were too narrow to enter
 * anything in. So the rail folds away when the wizard opens.
 *
 * Two things about that are easy to get wrong and both are worse than the
 * original problem:
 *
 * - **It must fold back.** A menu that disappears the moment you pick a
 *   modality and cannot be recovered has trapped the user in the wizard.
 * - **It must not fold itself back shut.** Deriving the state from the route on
 *   every render looks equivalent and is not: the user opens the rail to reach
 *   the settings link, the next render puts it away again, and the menu appears
 *   broken. The route decides once, on the way in and on the way out; after that
 *   the user decides.
 *
 * And a collapsed menu is still in the DOM. Links that can be tabbed into but
 * not seen are worse than a menu that is simply gone, so they leave the tab
 * order with it.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Layout from "./Layout";
import { api, User } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "nl" },
  }),
}));

const user: User = { id: 1, username: "jeffrey", role: "user", active: true } as User;

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<Layout user={user} onLogout={() => {}} />}>
          <Route path="/" element={<p>home</p>} />
          <Route path="/wizard/:modality" element={<p>wizard</p>} />
          <Route path="/settings" element={<p>settings</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

/** The grid that carries the rail; its columns are what actually animates. */
function grid(): HTMLElement {
  const nav = document.getElementById("main-nav");
  expect(nav).not.toBeNull();
  return nav!.parentElement as HTMLElement;
}

const isOpen = () => grid().className.includes("md:grid-cols-[200px_1fr]");

beforeEach(() => {
  vi.spyOn(api, "health").mockResolvedValue({ status: "ok", app: "CargoPilot", version: "1.53.0" });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("de zijbalk", () => {
  it("staat open op een gewone pagina", async () => {
    renderAt("/");
    await waitFor(() => expect(isOpen()).toBe(true));
    expect(document.getElementById("main-nav")).toHaveAttribute("aria-hidden", "false");
  });

  it("klapt weg zodra de wizard opent", async () => {
    renderAt("/wizard/road");
    await waitFor(() => expect(isOpen()).toBe(false));
    expect(grid().className).toContain("md:grid-cols-[0px_1fr]");
  });

  it("neemt de gap mee, zodat er geen strook overblijft", async () => {
    renderAt("/wizard/road");
    await waitFor(() => expect(grid().className).toContain("md:gap-x-0"));
  });

  it("kan tijdens de wizard weer terug", async () => {
    renderAt("/wizard/road");
    await waitFor(() => expect(isOpen()).toBe(false));

    await userEvent.click(screen.getByRole("button", { name: "nav.expandMenu" }));
    expect(isOpen()).toBe(true);
    // And shut again, from the same button.
    await userEvent.click(screen.getByRole("button", { name: "nav.collapseMenu" }));
    expect(isOpen()).toBe(false);
  });

  it("blijft open als de gebruiker hem tijdens de wizard opent", async () => {
    // The regression this file exists for: deriving the state from the route on
    // every render puts the rail away again on the next keystroke.
    renderAt("/wizard/road");
    await waitFor(() => expect(isOpen()).toBe(false));

    await userEvent.click(screen.getByRole("button", { name: "nav.expandMenu" }));
    expect(isOpen()).toBe(true);

    await userEvent.click(screen.getByText("nav.settings"));
    await waitFor(() => expect(screen.getByText("settings")).toBeInTheDocument());
    expect(isOpen()).toBe(true);
  });

  it("haalt de links uit de tabvolgorde zolang hij dicht is", async () => {
    renderAt("/wizard/road");
    await waitFor(() => expect(isOpen()).toBe(false));

    const nav = document.getElementById("main-nav")!;
    expect(nav).toHaveAttribute("aria-hidden", "true");
    for (const link of nav.querySelectorAll("a")) {
      expect(link).toHaveAttribute("tabindex", "-1");
    }

    await userEvent.click(screen.getByRole("button", { name: "nav.expandMenu" }));
    for (const link of nav.querySelectorAll("a")) {
      expect(link).not.toHaveAttribute("tabindex");
    }
  });

  it("laat de schil het scherm gebruiken zodra de balk weg is", async () => {
    // Folding the rail away is only half of it: the shell is capped at 80rem,
    // so on a wide monitor the 200px freed up went into the margin and the
    // table — which wants 1,620px — was no better off.
    renderAt("/wizard/road");
    await waitFor(() => expect(grid().className).toContain("max-w-[1800px]"));

    await userEvent.click(screen.getByRole("button", { name: "nav.expandMenu" }));
    expect(grid().className).toContain("max-w-7xl");
  });

  it("houdt de kop even breed als de inhoud, anders staan ze niet op één lijn", async () => {
    renderAt("/wizard/road");
    await waitFor(() => expect(grid().className).toContain("max-w-[1800px]"));
    const headerRow = screen.getByRole("banner").firstElementChild as HTMLElement;
    expect(headerRow.className).toContain("max-w-[1800px]");
  });

  it("zegt met aria-expanded wat de knop doet", async () => {
    renderAt("/");
    const toggle = await screen.findByRole("button", { name: "nav.collapseMenu" });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(toggle).toHaveAttribute("aria-controls", "main-nav");

    await userEvent.click(toggle);
    expect(screen.getByRole("button", { name: "nav.expandMenu" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });
});
