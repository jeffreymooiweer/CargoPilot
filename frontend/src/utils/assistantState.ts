import { AssistantState, DgEntry, LineItem } from "../api/client";
import { DraftLine } from "../components/ReviewLinesPanel";

/**
 * The wizard state as the assistant exchanges it — and back.
 *
 * The server is stateless: every turn the modal rebuilds the state from the
 * wizard, and everything the assistant wrote must land back in the wizard.
 * Whatever these two functions do not carry is silently forgotten between
 * turns. That is not theoretical: the skipped questions were not carried,
 * so every "skip" was forgotten the moment the next answer was sent — and
 * the same optional question came back after every turn, swallowing whatever
 * was typed as an answer to it.
 */
export function buildAssistantState(args: {
  modality: string;
  draftLines: DraftLine[];
  resultLines?: LineItem[];
  dgEntries: DgEntry[];
  docValues: Record<string, string>;
  selectedDocs: string[] | null;
  skippedQuestions: string[];
}): AssistantState {
  return {
    modality: args.modality,
    draft_lines: args.draftLines
      .filter((line) => line.description.trim())
      .map((line) => {
        const resultLine = args.resultLines?.find((r) => r.line_id === line.id);
        return {
          id: line.id,
          description: line.description,
          quantity: line.quantity || 1,
          unit: line.unit,
          dangerous_goods: Boolean(line.dangerous_goods),
          confirmed_un: line.confirmed_un,
          dg_dismissed: line.dg_dismissed,
          detected_un_numbers: resultLine?.detected_un_numbers ?? [],
          dg_name_candidates: resultLine?.dg_name_candidates ?? [],
          // What the consignor stated themselves travels as their answer; the
          // computed weight travels beside it, never as an override.
          weight_each_kg: line.weight_each_kg === "" ? undefined : line.weight_each_kg,
          computed_weight_each_kg: resultLine?.weight_each_kg ?? undefined,
          length_cm: line.length_cm === "" ? undefined : line.length_cm,
          width_cm: line.width_cm === "" ? undefined : line.width_cm,
          height_cm: line.height_cm === "" ? undefined : line.height_cm,
          package_content: line.package_content ?? resultLine?.package_content ?? undefined,
        };
      }),
    dg_entries: args.dgEntries,
    doc_values: args.docValues,
    selected_docs: args.selectedDocs,
    skipped_questions: args.skippedQuestions,
  };
}

/** The assistant's draft lines mapped onto the wizard's own, merged by id so
 *  nothing the wizard holds beyond these fields is lost. */
export function draftLinesFromAssistant(
  state: AssistantState,
  current: DraftLine[],
): DraftLine[] | null {
  if (!Array.isArray(state.draft_lines) || state.draft_lines.length === 0) return null;
  const byId = new Map(current.map((line) => [line.id, line]));
  return state.draft_lines.map((line) => ({
    ...(byId.get(Number(line.id)) ?? {}),
    id: Number(line.id),
    description: String(line.description ?? ""),
    quantity: (line.quantity as number) ?? 1,
    unit: String(line.unit ?? "pcs"),
    dangerous_goods: Boolean(line.dangerous_goods),
    confirmed_un: (line.confirmed_un as string) || undefined,
    dg_dismissed: Boolean(line.dg_dismissed) || undefined,
    // The assistant speaks the old flag only; what the screen holds is the
    // fuller answer, so a rejection it sends is read back as one.
    dg_decision: byId.get(Number(line.id))?.dg_decision
      ?? (line.confirmed_un ? "confirmed" : line.dg_dismissed ? "rejected" : undefined),
    package_content: (line.package_content as string) || undefined,
    // Measurements the assistant asked for land in the same columns the
    // lines table writes, so the classic wizard computes with them too.
    length_cm: (line.length_cm as number) ?? undefined,
    width_cm: (line.width_cm as number) ?? undefined,
    height_cm: (line.height_cm as number) ?? undefined,
    weight_each_kg: (line.weight_each_kg as number) ?? undefined,
  }));
}
