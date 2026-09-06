/**
 * What the wizard says about the entry it is holding.
 *
 * The honesty is the whole test. A save that failed must say so — the one
 * thing a draft may never keep to itself — and an installation that stores
 * nothing must say that too, with the file as the way out, rather than
 * quietly losing somebody's work on the next reload.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import DraftBar from "./DraftBar";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options && "time" in options ? `${key}:${options.time}` : key,
    i18n: { language: "nl" },
  }),
}));

describe("what happens to the entry while it is being made", () => {
  it("says nothing at all before anything is entered", () => {
    const { container } = render(<DraftBar mode="kept" status="idle" active={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("says when it was saved", () => {
    render(<DraftBar mode="kept" status="saved" savedAt={new Date()} active onDiscard={vi.fn()} />);
    expect(screen.getByText(/draft.savedAt/)).toBeInTheDocument();
  });

  it("says a failed save out loud", () => {
    render(<DraftBar mode="kept" status="failed" active />);
    expect(screen.getByText("draft.failed")).toBeInTheDocument();
    expect(screen.queryByText(/draft.saved/)).toBeNull();
  });

  it("offers to throw the draft away", async () => {
    const onDiscard = vi.fn();
    render(<DraftBar mode="kept" status="saved" active onDiscard={onDiscard} />);
    await userEvent.click(screen.getByRole("button", { name: "draft.discard" }));
    expect(onDiscard).toHaveBeenCalled();
  });

  it("where nothing is stored it says so, and hands over the file instead", async () => {
    const onDownload = vi.fn();
    render(<DraftBar mode="file" status="idle" active onDownload={onDownload} onOpenFile={vi.fn()} />);
    expect(screen.getByText("draft.notKeptHere")).toBeInTheDocument();
    // And no claim that anything was saved.
    expect(screen.queryByText("draft.saved")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "draft.download" }));
    expect(onDownload).toHaveBeenCalled();
  });

  it("reads a draft file back", async () => {
    const onOpenFile = vi.fn();
    render(<DraftBar mode="file" status="idle" active onOpenFile={onOpenFile} />);
    const file = new File(["{}"], "concept.json", { type: "application/json" });
    await userEvent.upload(screen.getByLabelText("draft.open"), file);
    expect(onOpenFile).toHaveBeenCalledWith(file);
  });
});
