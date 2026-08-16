/**
 * The assistant panel: a chat that can only say what the backend produced.
 *
 * The panel verbalises structured events — a parsed line, a recognition to
 * confirm, an open question with its options — and writes every reply back
 * into the same wizard state. These tests pin the contract: the request
 * carries the wizard state and the pending question, the returned state is
 * applied, and option chips send the stored value while showing the label.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import AssistantPanel from "./AssistantPanel";
import { api } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `${key} ${JSON.stringify(vars)}` : key,
    i18n: { language: "nl" },
  }),
}));

vi.mock("../api/client", () => ({
  api: { assistantStep: vi.fn() },
}));

const stepMock = api.assistantStep as ReturnType<typeof vi.fn>;

function renderPanel(onApplyState = vi.fn()) {
  render(
    <AssistantPanel
      buildState={() => ({ modality: "road", draft_lines: [] })}
      onApplyState={onApplyState}
    />,
  );
  return onApplyState;
}

describe("AssistantPanel", () => {
  it("sends the message with the wizard state and applies what comes back", async () => {
    const returned = { modality: "road", draft_lines: [{ id: 1 }] };
    stepMock.mockResolvedValueOnce({
      state: returned,
      events: [{ kind: "lines_added", count: 1 }],
      pending: null,
    });
    const onApplyState = renderPanel();
    await userEvent.type(screen.getByPlaceholderText("assistant.placeholder"), "1000 jerrycans diesel");
    await userEvent.click(screen.getByRole("button", { name: "assistant.send" }));
    expect(stepMock).toHaveBeenCalledWith(
      expect.objectContaining({ message: "1000 jerrycans diesel", language: "nl" }),
    );
    expect(onApplyState).toHaveBeenCalledWith(returned);
    expect(await screen.findByText(/assistant\.linesAdded/)).toBeTruthy();
  });

  it("renders a question's options as chips that send the stored value", async () => {
    stepMock.mockResolvedValueOnce({
      state: {},
      events: [
        {
          kind: "dg_question",
          field: "carriage_mode",
          label: { nl: "Vervoerswijze" },
          reason: "carriage_mode_decides",
          options: ["packages", "tank"],
        },
      ],
      pending: {
        scope: "dg_question",
        field: "carriage_mode",
        required: true,
        options: ["packages", "tank"],
        option_labels: { packages: { nl: "Colli" }, tank: { nl: "Tank" } },
      },
    });
    renderPanel();
    await userEvent.type(screen.getByPlaceholderText("assistant.placeholder"), "diesel");
    await userEvent.click(screen.getByRole("button", { name: "assistant.send" }));
    // The chip shows the label…
    const chip = await screen.findByRole("button", { name: "Colli" });
    stepMock.mockResolvedValueOnce({ state: {}, events: [], pending: null });
    await userEvent.click(chip);
    // …and sends the stored value.
    expect(stepMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ message: "packages" }),
    );
  });

  it("a required question offers no skip chip", async () => {
    stepMock.mockResolvedValueOnce({
      state: {},
      events: [],
      pending: {
        scope: "dg_question", field: "carriage_mode",
        required: true, options: ["packages"], option_labels: {},
      },
    });
    renderPanel();
    await userEvent.type(screen.getByPlaceholderText("assistant.placeholder"), "x");
    await userEvent.click(screen.getByRole("button", { name: "assistant.send" }));
    await screen.findByRole("button", { name: "packages" });
    expect(screen.queryByRole("button", { name: "assistant.skip" })).toBeNull();
  });
});
