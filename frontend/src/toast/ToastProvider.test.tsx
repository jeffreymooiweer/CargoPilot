/**
 * The toast lifetimes are the contract, so the tests pin them: a success
 * leaves on its own, an error never does, and an undoable delete really is
 * deferred — the API call fires when the window closes and never fires when
 * the undo is taken. Those last two are the difference between "undo" as a
 * UI flourish and undo as a promise.
 */
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider, useToast, type ToastApi } from "./ToastProvider";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "nl" },
  }),
}));

/** Hands the api out of the tree so a test can drive it directly. */
function Grab({ onApi }: { onApi: (api: ToastApi) => void }) {
  onApi(useToast());
  return null;
}

function setup() {
  let api: ToastApi | null = null;
  render(
    <ToastProvider>
      <Grab onApi={(a) => (api = a)} />
    </ToastProvider>,
  );
  return () => {
    if (!api) throw new Error("ToastApi not captured");
    return api;
  };
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ToastProvider", () => {
  it("a success dismisses itself after four seconds", async () => {
    const api = setup();
    act(() => void api().success("saved"));
    expect(screen.getByText("saved")).toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(4100));
    await waitFor(() => expect(screen.queryByText("saved")).not.toBeInTheDocument());
  });

  it("an error stays until it is closed by hand", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const api = setup();
    act(() => void api().error("boom"));
    act(() => void vi.advanceTimersByTime(60000));
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    await user.click(screen.getByRole("button", { name: "toast.dismiss" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("a loading toast follows its action: progress, then the outcome", async () => {
    const api = setup();
    let handle!: ReturnType<ToastApi["loading"]>;
    act(() => {
      handle = api().loading("working");
    });
    // No timer closes it.
    act(() => void vi.advanceTimersByTime(60000));
    expect(screen.getByText("working")).toBeInTheDocument();
    // And it carries no dismiss button: only its outcome may close it.
    expect(screen.queryByRole("button", { name: "toast.dismiss" })).not.toBeInTheDocument();
    act(() => handle.progress("still working"));
    expect(screen.getByText("still working")).toBeInTheDocument();
    act(() => handle.success("done"));
    expect(screen.getByText("done")).toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(4100));
    await waitFor(() => expect(screen.queryByText("done")).not.toBeInTheDocument());
  });

  it("an undoable delete fires the deferred call when the window closes", async () => {
    const api = setup();
    const execute = vi.fn();
    const restore = vi.fn();
    act(() => void api().undoable("deleted", { execute, restore }));
    expect(execute).not.toHaveBeenCalled();
    act(() => void vi.advanceTimersByTime(6100));
    expect(execute).toHaveBeenCalledTimes(1);
    expect(restore).not.toHaveBeenCalled();
  });

  it("undo means the deferred call never happens", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const api = setup();
    const execute = vi.fn();
    const restore = vi.fn();
    act(() => void api().undoable("deleted", { execute, restore }));
    await user.click(screen.getByRole("button", { name: "toast.undo" }));
    expect(restore).toHaveBeenCalledTimes(1);
    // Even after the window would have closed: nothing fires.
    act(() => void vi.advanceTimersByTime(10000));
    expect(execute).not.toHaveBeenCalled();
  });

  it("dismissing an undoable toast is 'I don't need the undo': it fires now", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const api = setup();
    const execute = vi.fn();
    act(() => void api().undoable("deleted", { execute, restore: vi.fn() }));
    await user.click(screen.getByRole("button", { name: "toast.dismiss" }));
    expect(execute).toHaveBeenCalledTimes(1);
    // And only once, even when its timer would fire later.
    act(() => void vi.advanceTimersByTime(10000));
    expect(execute).toHaveBeenCalledTimes(1);
  });

  it("being pushed out by a full stack still fires the deferred call", () => {
    const api = setup();
    const execute = vi.fn();
    act(() => void api().undoable("deleted", { execute, restore: vi.fn() }));
    // Five more toasts arrive; the stack holds five, so the oldest is evicted.
    act(() => {
      for (let i = 0; i < 5; i += 1) api().info(`note ${i}`);
    });
    expect(screen.queryByText("deleted")).not.toBeInTheDocument();
    expect(execute).toHaveBeenCalledTimes(1);
  });

  it("a sticky info toast never times out, and only the × counts as dismissed", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const api = setup();
    const onDismiss = vi.fn();
    act(() => void api().info("update available", { sticky: true, onDismiss }));
    act(() => void vi.advanceTimersByTime(60000));
    expect(screen.getByText("update available")).toBeInTheDocument();
    expect(onDismiss).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "toast.dismiss" }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("eviction does not count as the user dismissing a sticky notice", () => {
    const api = setup();
    const onDismiss = vi.fn();
    act(() => void api().info("update available", { sticky: true, onDismiss }));
    act(() => {
      for (let i = 0; i < 5; i += 1) api().info(`note ${i}`);
    });
    expect(screen.queryByText("update available")).not.toBeInTheDocument();
    expect(onDismiss).not.toHaveBeenCalled();
  });

  it("errors announce assertively, the rest politely", () => {
    const api = setup();
    act(() => {
      api().error("bad");
      api().success("good");
    });
    expect(screen.getByRole("alert")).toHaveAttribute("aria-live", "assertive");
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });
});
