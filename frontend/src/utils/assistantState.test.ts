/**
 * The state round trip between the wizard and the assistant.
 *
 * The server is stateless: every turn the modal rebuilds the state from the
 * wizard, and everything the backend wrote must land back in the wizard.
 * Whatever this round trip does not carry is silently forgotten between
 * turns. The owner found the first casualty: a skipped question was not
 * carried, so "skip" was forgotten the moment the next answer was sent, and
 * the same optional question came back after every turn — swallowing the
 * answers meant for other questions.
 */
import { describe, expect, it } from "vitest";

import { AssistantState } from "../api/client";
import { DraftLine } from "../components/ReviewLinesPanel";
import { buildAssistantState, draftLinesFromAssistant } from "./assistantState";

const args = (draftLines: DraftLine[], skipped: string[] = []) => ({
  modality: "road",
  draftLines,
  resultLines: undefined,
  dgEntries: [],
  docValues: {},
  selectedDocs: null,
  skippedQuestions: skipped,
});

function roundTrip(backendState: AssistantState, current: DraftLine[]) {
  const lines = draftLinesFromAssistant(backendState, current) ?? current;
  const skipped = (backendState.skipped_questions ?? []).map(String);
  return buildAssistantState(args(lines, skipped));
}

describe("the wizard/assistant state round trip", () => {
  it("carries a skipped question through to the next turn", () => {
    const backendState: AssistantState = {
      modality: "road",
      draft_lines: [{ id: 1, description: "stalen plaat", quantity: 1, unit: "pcs" }],
      skipped_questions: ["goods:1:goods_dimensions"],
    };
    const rebuilt = roundTrip(backendState, []);
    expect(rebuilt.skipped_questions).toEqual(["goods:1:goods_dimensions"]);
  });

  it("carries an answered measurement through to the next turn", () => {
    const backendState: AssistantState = {
      modality: "road",
      draft_lines: [{
        id: 1, description: "stalen plaat", quantity: 1, unit: "pcs",
        length_cm: 200, width_cm: 100, height_cm: 2,
      }],
    };
    const rebuilt = roundTrip(backendState, []);
    const line = rebuilt.draft_lines?.[0] as Record<string, unknown>;
    expect([line.length_cm, line.width_cm, line.height_cm]).toEqual([200, 100, 2]);
  });

  it("keeps what the wizard holds beyond the exchanged fields", () => {
    const current: DraftLine[] = [{
      id: 1, description: "stalen plaat", quantity: 1, unit: "pcs",
      wall_thickness_mm: 8,
    }];
    const lines = draftLinesFromAssistant(
      { draft_lines: [{ id: 1, description: "stalen plaat", quantity: 1, unit: "pcs" }] },
      current,
    );
    expect(lines?.[0].wall_thickness_mm).toBe(8);
  });

  it("a stated weight travels as the answer, a computed one never does", () => {
    const stated = buildAssistantState(args([{
      id: 1, description: "machineonderdeel", quantity: 4, unit: "pallet",
      weight_each_kg: 900,
    }]));
    expect((stated.draft_lines?.[0] as Record<string, unknown>).weight_each_kg).toBe(900);

    const computed = buildAssistantState({
      ...args([{ id: 1, description: "stalen plaat", quantity: 1, unit: "pcs" }]),
      resultLines: [{ line_id: 1, weight_each_kg: 314 } as never],
    });
    const line = computed.draft_lines?.[0] as Record<string, unknown>;
    expect(line.weight_each_kg).toBeUndefined();
    expect(line.computed_weight_each_kg).toBe(314);
  });
});
