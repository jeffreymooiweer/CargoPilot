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
 * Since v1.202.0 folding it no longer empties it. The rail keeps its icons at
 * 56px instead of going to nothing, so the destinations stay one press away
 * while the wizard still gets the width the lines table was measured to need.
 * Each icon carries its label as its accessible name, because an icon without
 * one is a guess — and there is only ever one rail in the document, so nothing
 * is on the screen twice for the tab key to find.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Layout from "./Layout";
import { ToastProvider } from "../toast/ToastProvider";
import { PreferencesProvider } from "../settings/preferences";
import { BrandingContext } from "../branding";
import { api, User, VISITOR } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "nl" },
  }),
}));

const user: User = { id: 1, username: "jeffrey", role: "user", active: true } as User;

function renderAt(path: string) {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<Layout user={user} onLogout={() => {}} />}>
            <Route path="/" element={<p>home</p>} />
            <Route path="/wizard/:modality" element={<p>wizard</p>} />
            <Route path="/settings" element={<p>settings</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ToastProvider>,
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
    // Open means the words are there, not only the glyphs.
    expect(screen.getByText("nav.settings")).toBeInTheDocument();
  });

  it("klapt weg zodra de wizard opent", async () => {
    renderAt("/wizard/road");
    await waitFor(() => expect(isOpen()).toBe(false));
    expect(grid().className).toContain("md:grid-cols-[56px_1fr]");
  });

  it("houdt de bestemmingen bereikbaar zodra hij smal is", async () => {
    // The whole point of 56px instead of 0: the menu is narrower, not gone.
    renderAt("/wizard/road");
    await waitFor(() => expect(isOpen()).toBe(false));

    const nav = document.getElementById("main-nav")!;
    const settings = screen.getByRole("link", { name: "nav.settings" });
    expect(nav.contains(settings)).toBe(true);
    // The label is the accessible name; the words themselves are away.
    expect(settings.textContent).toBe("");
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

  it("zet elke bestemming maar één keer in het document", async () => {
    // The folded rail and the open one are the same links drawn twice. Keeping
    // both mounted would put every destination on the screen twice — once for
    // the eye and once more for a screen reader and the tab key.
    renderAt("/wizard/road");
    await waitFor(() => expect(isOpen()).toBe(false));
    expect(screen.getAllByRole("link", { name: "nav.settings" })).toHaveLength(1);

    await userEvent.click(screen.getByRole("button", { name: "nav.expandMenu" }));
    expect(screen.getAllByRole("link", { name: "nav.settings" })).toHaveLength(1);
  });

  it("laat de schil het scherm gebruiken zodra de balk smal is", async () => {
    // Folding the rail away is only half of it: the shell is capped at 80rem,
    // so on a wide monitor the width freed up went into the margin and the
    // table — which wants 1,620px — was no better off. The cap is the folded
    // rail's 56px wider than the 1,800px the table was measured against.
    renderAt("/wizard/road");
    await waitFor(() => expect(grid().className).toContain("max-w-[1856px]"));

    await userEvent.click(screen.getByRole("button", { name: "nav.expandMenu" }));
    expect(grid().className).toContain("max-w-7xl");
  });

  it("houdt de kop even breed als de inhoud, anders staan ze niet op één lijn", async () => {
    renderAt("/wizard/road");
    await waitFor(() => expect(grid().className).toContain("max-w-[1856px]"));
    const headerRow = screen.getByRole("banner").firstElementChild as HTMLElement;
    expect(headerRow.className).toContain("max-w-[1856px]");
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

describe("de open installatie", () => {
  // Nobody is signed in, so there is nobody to sign out — and where the
  // account name would stand, the chrome says which application this is,
  // so a visitor can see it without asking the server.
  function renderOpen() {
    vi.spyOn(api, "publicSettings").mockRejectedValue(new Error("offline"));
    // The provider applies the browser's theme on load, and jsdom has no
    // matchMedia; the preferences tests stub it the same way.
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (query: string) => ({
        matches: false,
        media: query,
        addEventListener: () => {},
        removeEventListener: () => {},
      }),
    });
    return render(
      <PreferencesProvider mode="open">
        <ToastProvider>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route element={<Layout user={VISITOR} onLogout={() => {}} />}>
                <Route path="/" element={<p>home</p>} />
              </Route>
            </Routes>
          </MemoryRouter>
        </ToastProvider>
      </PreferencesProvider>,
    );
  }

  it("heeft geen uitlogknop en zegt in plaats van een naam wat het is", async () => {
    renderOpen();
    expect(await screen.findByText("nav.openMode")).toBeInTheDocument();
    expect(screen.queryByText("nav.logout")).toBeNull();
  });

  it("zet de installatie ook bij het versienummer", async () => {
    renderOpen();
    await waitFor(() =>
      expect(screen.getByLabelText("settings.version v1.53.0")).toHaveTextContent("nav.openMode · v1.53.0"),
    );
  });
});

describe("de huisstijl", () => {
  it("zet de eigen naam en het eigen logo in de kop, zonder het logo om te keren", async () => {
    render(
      <BrandingContext.Provider
        value={{
          branding: { name: "Mooiweer Logistiek", logo: "/api/branding/logo?v=7", modalities: {} },
          refresh: async () => {},
        }}
      >
        <ToastProvider>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route element={<Layout user={user} onLogout={() => {}} />}>
                <Route path="/" element={<p>home</p>} />
              </Route>
            </Routes>
          </MemoryRouter>
        </ToastProvider>
      </BrandingContext.Provider>,
    );
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Mooiweer Logistiek");
    const logo = screen.getByRole("banner").querySelector("img") as HTMLImageElement;
    expect(logo.getAttribute("src")).toBe("/api/branding/logo?v=7");
    // The default glyph is inverted for the dark theme; a company's logo is
    // shown in its own colours, or it is not the company's logo.
    expect(logo.className).not.toContain("invert");
  });

  it("valt terug op de productnaam en het eigen glyph", async () => {
    renderAt("/");
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("app.name");
    const logo = screen.getByRole("banner").querySelector("img") as HTMLImageElement;
    expect(logo.getAttribute("src")).toBe("/shipping.png");
    expect(logo.className).toContain("dark:invert");
  });
});
