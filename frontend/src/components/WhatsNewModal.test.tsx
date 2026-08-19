/**
 * The what's-new card shows an update once, and only to someone who has an
 * update to see.
 *
 * The three quiet paths matter as much as the loud one. A user whose marker
 * equals the running version gets nothing — not even a save. A user without a
 * marker (fresh account, or from before the card existed) gets nothing shown
 * but the marker written, because their first login is not an update and a
 * wall of history teaches people to dismiss unread. And dismissing is what
 * writes the marker, so an unread card comes back next login instead of being
 * lost.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import WhatsNewModal, { parseBlocks, renderInline } from "./WhatsNewModal";
import { api, UserPreferences } from "../api/client";
import { EMPTY_PREFERENCES } from "../settings/preferences";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options?.version ? `${key} ${options.version}` : key,
    i18n: { language: "nl" },
  }),
}));

const saveMock = vi.fn(async (values: UserPreferences) => values);
let mockedPreferences: UserPreferences = EMPTY_PREFERENCES;
let mockedLoaded = true;

vi.mock("../settings/preferences", async (importOriginal) => {
  const original = await importOriginal<typeof import("../settings/preferences")>();
  return {
    ...original,
    usePreferences: () => ({
      preferences: mockedPreferences,
      publicSettings: null,
      loaded: mockedLoaded,
      save: saveMock,
      reload: async () => {},
    }),
  };
});

const NOTES = {
  version: "1.125.0",
  entries: [
    {
      version: "1.125.0",
      date: "2026-08-19",
      body: "### Added\n\n- **The card itself.** Shown once\n  after an update.",
    },
  ],
  truncated: false,
};

function withPreferences(overrides: Partial<UserPreferences>, loaded = true) {
  mockedPreferences = { ...EMPTY_PREFERENCES, ...overrides };
  mockedLoaded = loaded;
}

afterEach(() => {
  vi.restoreAllMocks();
  saveMock.mockClear();
});

describe("WhatsNewModal", () => {
  it("shows the entries to a user whose marker is behind", async () => {
    withPreferences({ last_seen_version: "1.124.0" });
    const changelog = vi.spyOn(api, "changelog").mockResolvedValue(NOTES);
    render(<WhatsNewModal />);
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(changelog).toHaveBeenCalledWith("1.124.0");
    // The wrapped list item is one sentence again, bold rendered as such.
    expect(screen.getByText("The card itself.").tagName).toBe("STRONG");
    expect(screen.getByText(/Shown once after an update/)).toBeInTheDocument();
    // Showing is not acknowledging: nothing saved until dismissed.
    expect(saveMock).not.toHaveBeenCalled();
  });

  it("dismissing writes the running version as seen", async () => {
    withPreferences({ last_seen_version: "1.124.0" });
    vi.spyOn(api, "changelog").mockResolvedValue(NOTES);
    render(<WhatsNewModal />);
    await screen.findByRole("dialog");
    // Both the × and the footer button carry the close name; either dismisses.
    await userEvent.click(screen.getAllByRole("button", { name: "whatsNew.close" })[0]);
    await waitFor(() =>
      expect(saveMock).toHaveBeenCalledWith(
        expect.objectContaining({ last_seen_version: "1.125.0" }),
      ),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("stays quiet for a marker that matches the running version", async () => {
    withPreferences({ last_seen_version: "1.125.0" });
    vi.spyOn(api, "changelog").mockResolvedValue({ ...NOTES, entries: [] });
    render(<WhatsNewModal />);
    await waitFor(() => expect(api.changelog).toHaveBeenCalled());
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(saveMock).not.toHaveBeenCalled();
  });

  it("marks a user without a marker silently instead of showing history", async () => {
    withPreferences({ last_seen_version: "" });
    vi.spyOn(api, "changelog").mockResolvedValue({ ...NOTES, truncated: true });
    render(<WhatsNewModal />);
    await waitFor(() =>
      expect(saveMock).toHaveBeenCalledWith(
        expect.objectContaining({ last_seen_version: "1.125.0" }),
      ),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("does nothing before the account's preferences have answered", async () => {
    // The cached EMPTY_PREFERENCES would read as "no marker" and swallow the
    // notes by writing the marker for a user who has simply not loaded yet.
    withPreferences({ last_seen_version: "1.124.0" }, false);
    const changelog = vi.spyOn(api, "changelog").mockResolvedValue(NOTES);
    render(<WhatsNewModal />);
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(changelog).not.toHaveBeenCalled();
    expect(saveMock).not.toHaveBeenCalled();
  });

  it("survives a failing endpoint without a card or a save", async () => {
    withPreferences({ last_seen_version: "1.124.0" });
    vi.spyOn(api, "changelog").mockRejectedValue(new Error("offline"));
    render(<WhatsNewModal />);
    await waitFor(() => expect(api.changelog).toHaveBeenCalled());
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(saveMock).not.toHaveBeenCalled();
  });
});

describe("the changelog's own markdown, minimally", () => {
  it("splits headings, items and wrapped continuations", () => {
    const blocks = parseBlocks(
      "### Added\n\n- **First.** A line\n  that wraps.\n- Second.\n\nA closing paragraph.",
    );
    expect(blocks).toEqual([
      { kind: "heading", text: "Added" },
      { kind: "item", text: "**First.** A line that wraps." },
      { kind: "item", text: "Second." },
      { kind: "paragraph", text: "A closing paragraph." },
    ]);
  });

  it("renders bold, italics and code inline", () => {
    const { container } = render(<p>{renderInline("a **b** *c* `d`")}</p>);
    expect(container.querySelector("strong")?.textContent).toBe("b");
    expect(container.querySelector("em")?.textContent).toBe("c");
    expect(container.querySelector("code")?.textContent).toBe("d");
  });
});
