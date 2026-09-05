/**
 * The wizard's state as one document, so a kept shipment can be reopened.
 *
 * The server stores this without reading it — it is the interface's own
 * shape, versioned by the interface. What goes in is the *source* state:
 * the lines as typed, the calculated result, the declared dangerous goods,
 * the document fields, the selection and the signature. Everything the
 * wizard derives from those (the advice, the profiles, the warnings) is
 * recomputed on open, so a snapshot never carries a stale judgement.
 *
 * Reading is defensive on purpose. A snapshot written by a later version
 * with a shape this one does not know, or a row somebody edited by hand,
 * must open as far as it can rather than crash the wizard: every field has
 * a fallback and the version is checked for a major break only.
 */
import type { CalcResult, DgEntry } from "../api/client";
import type { DraftLine } from "../components/ReviewLinesPanel";

export const SNAPSHOT_VERSION = 1;

export interface WizardSnapshot {
  version: number;
  modality: string;
  stepKey: "lines" | "dg" | "details" | "export";
  /** The language the documents are drawn up in; null means the screen's. */
  docLang: string | null;
  /** null means "the advice decides". */
  selectedDocs: string[] | null;
  docValues: Record<string, string>;
  skippedQuestions: string[];
  draftLines: DraftLine[];
  nextId: number;
  result: CalcResult | null;
  dgEntries: DgEntry[];
  signature: string | null;
}

const STEPS = new Set(["lines", "dg", "details", "export"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
}

/** A snapshot from whatever was stored, or null when it is not one at all. */
export function readSnapshot(raw: unknown): WizardSnapshot | null {
  if (!isRecord(raw)) return null;
  const version = typeof raw.version === "number" ? raw.version : 0;
  if (version < 1 || version > SNAPSHOT_VERSION) return null;

  const draftLines = Array.isArray(raw.draftLines)
    ? (raw.draftLines.filter(isRecord) as unknown as DraftLine[])
    : [];
  const values: Record<string, string> = {};
  if (isRecord(raw.docValues)) {
    for (const [key, value] of Object.entries(raw.docValues)) {
      if (typeof value === "string") values[key] = value;
    }
  }
  const stepKey = typeof raw.stepKey === "string" && STEPS.has(raw.stepKey)
    ? (raw.stepKey as WizardSnapshot["stepKey"])
    : "lines";
  const lines: DraftLine[] = draftLines.length > 0
    ? draftLines
    : [{ id: 1, description: "", quantity: 1, unit: "pcs" }];
  // The next id must clear every line there is, including the blank one a
  // missing list falls back to — a duplicate id is two rows editing as one.
  const nextId = typeof raw.nextId === "number" && raw.nextId > 0
    ? raw.nextId
    : Math.max(0, ...lines.map((line) => Number(line.id) || 0)) + 1;

  return {
    version,
    modality: typeof raw.modality === "string" ? raw.modality : "",
    stepKey,
    docLang: typeof raw.docLang === "string" ? raw.docLang : null,
    selectedDocs: Array.isArray(raw.selectedDocs) ? strings(raw.selectedDocs) : null,
    docValues: values,
    skippedQuestions: strings(raw.skippedQuestions),
    draftLines: lines,
    nextId,
    result: isRecord(raw.result) && Array.isArray(raw.result.lines) ? (raw.result as unknown as CalcResult) : null,
    dgEntries: Array.isArray(raw.dgEntries) ? (raw.dgEntries.filter(isRecord) as unknown as DgEntry[]) : [],
    signature: typeof raw.signature === "string" && raw.signature ? raw.signature : null,
  };
}
