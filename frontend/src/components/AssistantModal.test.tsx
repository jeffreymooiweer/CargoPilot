/**
 * The assistant as a survey in a modal.
 *
 * One question per screen, options as selectable answers, and a previous
 * button that really goes back: the server is stateless, so history is a
 * client-side stack of snapshots, and going back restores the wizard state
 * taken before that answer was applied. These tests pin that mechanism, the
 * value/label split of the answers, and that a misunderstood answer neither
 * advances the survey nor grows the history.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AssistantModal from "./AssistantModal";
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

const QUESTION = {
  state: { modality: "road", draft_lines: [{ id: 1 }] },
  events: [{ kind: "lines_added", count: 1 }],
  pending: {
    scope: "dg_question",
    field: "carriage_mode",
    required: true,
    label: { nl: "Vervoerswijze" },
    reason: "carriage_mode_decides",
    options: ["packages", "tank"],
    option_labels: { packages: { nl: "Colli" }, tank: { nl: "Tank" } },
  },
};

function renderModal(onApplyState = vi.fn(), onClose = vi.fn()) {
  render(
    <AssistantModal
      open
      onClose={onClose}
      buildState={() => ({ modality: "road", draft_lines: [] })}
      onApplyState={onApplyState}
    />,
  );
  return { onApplyState, onClose };
}

async function reachQuestion(onApplyState = vi.fn()) {
  stepMock.mockResolvedValueOnce(QUESTION);
  renderModal(onApplyState);
  await userEvent.type(
    screen.getByLabelText("assistant.describeLabel"),
    "1000 jerrycans diesel",
  );
  await userEvent.click(screen.getByRole("button", { name: "assistant.start" }));
  await screen.findByText(/Vervoerswijze/);
  return onApplyState;
}

beforeEach(() => stepMock.mockReset());

describe("AssistantModal", () => {
  it("starts as a describe screen and turns the reply into a survey question", async () => {
    const onApplyState = await reachQuestion();
    expect(onApplyState).toHaveBeenCalledWith(QUESTION.state);
    // Options are radios showing the localized label.
    expect(screen.getByRole("radio", { name: "Colli" })).toBeTruthy();
    expect(screen.getByRole("radio", { name: "Tank" })).toBeTruthy();
  });

  it("an answer needs a selection, and the selection sends the stored value", async () => {
    await reachQuestion();
    const next = screen.getByRole("button", { name: "assistant.next" });
    expect((next as HTMLButtonElement).disabled).toBe(true);
    await userEvent.click(screen.getByRole("radio", { name: "Colli" }));
    stepMock.mockResolvedValueOnce({ state: {}, events: [], pending: null });
    await userEvent.click(next);
    expect(stepMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ message: "packages" }),
    );
  });

  it("previous restores the snapshot taken before the answer", async () => {
    const onApplyState = await reachQuestion();
    await userEvent.click(screen.getByRole("button", { name: "assistant.previous" }));
    // Back to the describe screen, with the pre-answer state re-applied.
    expect(screen.getByLabelText("assistant.describeLabel")).toBeTruthy();
    expect(onApplyState).toHaveBeenLastCalledWith({ modality: "road", draft_lines: [] });
  });

  it("a misunderstood answer keeps the question and grows no history", async () => {
    await reachQuestion();
    await userEvent.click(screen.getByRole("radio", { name: "Tank" }));
    stepMock.mockResolvedValueOnce({
      state: {},
      events: [{ kind: "not_understood" }],
      pending: QUESTION.pending,
    });
    await userEvent.click(screen.getByRole("button", { name: "assistant.next" }));
    expect(await screen.findByText("assistant.notUnderstood")).toBeTruthy();
    expect(screen.getByText(/Vervoerswijze/)).toBeTruthy();
  });

  it("shows the lay phrasing and keeps label and help behind the info mark", async () => {
    stepMock.mockResolvedValueOnce({
      ...QUESTION,
      pending: {
        ...QUESTION.pending,
        simple: { nl: "Hoe gaat dit vervoerd worden?" },
        help: { nl: "De regels verschillen per vervoerswijze." },
      },
    });
    renderModal();
    await userEvent.type(screen.getByLabelText("assistant.describeLabel"), "diesel");
    await userEvent.click(screen.getByRole("button", { name: "assistant.start" }));
    expect(await screen.findByText("Hoe gaat dit vervoerd worden?")).toBeTruthy();
    // The formal wording only appears after opening the info mark.
    expect(screen.queryByText(/De regels verschillen/)).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "assistant.info" }));
    expect(screen.getByText(/Vervoerswijze — De regels verschillen/)).toBeTruthy();
  });

  it("a follow-up question shows the example and grows no history", async () => {
    await reachQuestion();
    await userEvent.click(screen.getByRole("radio", { name: "Tank" }));
    stepMock.mockResolvedValueOnce({
      state: {},
      events: [{ kind: "clarify", field: "carriage_mode", example: "25 L" }],
      pending: QUESTION.pending,
    });
    await userEvent.click(screen.getByRole("button", { name: "assistant.next" }));
    expect(await screen.findByText(/assistant.clarify.*25 L/)).toBeTruthy();
    expect(screen.getByText(/Vervoerswijze/)).toBeTruthy();
  });

  it("a corrected answer names what was tried", async () => {
    await reachQuestion();
    await userEvent.click(screen.getByRole("radio", { name: "Tank" }));
    stepMock.mockResolvedValueOnce({
      state: {},
      events: [{ kind: "clarify", field: "carriage_mode", attempt: "per onderzeeboot" }],
      pending: QUESTION.pending,
    });
    await userEvent.click(screen.getByRole("button", { name: "assistant.next" }));
    expect(await screen.findByText(/assistant.corrected.*per onderzeeboot/)).toBeTruthy();
  });

  it("no pending question means the survey is done", async () => {
    stepMock.mockResolvedValueOnce({ state: {}, events: [{ kind: "ready", documents: [] }], pending: null });
    const { onClose } = renderModal();
    await userEvent.type(screen.getByLabelText("assistant.describeLabel"), "staal");
    await userEvent.click(screen.getByRole("button", { name: "assistant.start" }));
    expect(await screen.findByText("assistant.ready")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "assistant.done" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("clicking the backdrop closes; clicking the dialog does not", async () => {
    const { onClose } = renderModal();
    await userEvent.click(screen.getByRole("dialog"));
    expect(onClose).not.toHaveBeenCalled();
    await userEvent.click(screen.getByTestId("assistant-backdrop"));
    expect(onClose).toHaveBeenCalled();
  });
});
