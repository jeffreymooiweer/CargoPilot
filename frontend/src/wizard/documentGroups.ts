/**
 * The questions of the shipment-details step, grouped by what they mean.
 *
 * The step used to be built per document: one form with the shared sections,
 * then one form for every selected document that has fields of its own. Because
 * the answers are one flat map keyed by field key, a document asking for
 * `container_number` was asking the same question the previous form had already
 * asked — the same value, under another box number, on another form. With four
 * documents selected that is four forms and a handful of questions asked twice.
 *
 * Here the same registry is read into three groups: the parties, the route, and
 * the additions — the references plus whatever each document needs beyond them.
 * A key appears once. Where several documents ask for it, the first definition
 * is the one shown and the others are recorded on it, so the form can say who
 * else is asking and under what name.
 */
import { DocumentDefinition, DocumentField, DocumentRegistry, DocumentSection, LocalizedText } from "../api/client";

export type GroupKey = "parties" | "route" | "additions";

/** Which group a shared section belongs to. A section this does not name — one
 *  added to the registry later — lands with the additions rather than
 *  disappearing from the form. */
const SHARED_GROUPS: Record<string, GroupKey> = {
  parties: "parties",
  locations: "route",
  references: "additions",
};

export const GROUP_ORDER: GroupKey[] = ["parties", "route", "additions"];

export interface GroupedField extends DocumentField {
  /** The other documents asking for this same key, and what each calls it.
   *  Empty when only one document asks. */
  alsoAsked: { document: LocalizedText; label: LocalizedText }[];
}

export interface GroupedSection {
  key: string;
  /** The heading above these fields: a shared section's own label, or the
   *  document's label for the fields it needs beyond the shared ones. */
  label?: LocalizedText;
  fields: GroupedField[];
}

export interface FieldGroup {
  key: GroupKey;
  sections: GroupedSection[];
}

export interface GroupedQuestions {
  groups: FieldGroup[];
  /** The documents that ask nothing beyond what the groups already ask —
   *  named on the form, so a document that produced no question of its own is
   *  not read as forgotten. */
  covered: DocumentDefinition[];
}

/** Every question a document set asks, in the order the form asks them. */
export function questions(registry: DocumentRegistry, documents: DocumentDefinition[]): GroupedField[] {
  return groupFields(registry, documents).groups.flatMap((group) =>
    group.sections.flatMap((section) => section.fields),
  );
}

/**
 * What choosing a document adds to the form: the questions it brings that
 * nothing already selected was asking.
 *
 * An extra document usually adds nothing at all — its questions were asked by
 * the ones already chosen — and saying so is worth as much as naming the one
 * question it does add.
 */
export function addedQuestions(
  registry: DocumentRegistry,
  before: DocumentDefinition[],
  after: DocumentDefinition[],
): GroupedField[] {
  const had = new Set(questions(registry, before).map((field) => field.key));
  return questions(registry, after).filter((field) => !had.has(field.key));
}

/** A field that some selected document requires is required, whatever the
 *  document that happened to define it first calls it. A required definition
 *  also drops the condition of a conditional one: the document needing it does
 *  not need it conditionally. */
function merge(kept: GroupedField, next: DocumentField): void {
  if (next.status === "USER_REQUIRED" && kept.status !== "USER_REQUIRED") {
    kept.status = "USER_REQUIRED";
    delete kept.condition;
  }
  if (!kept.help && next.help) kept.help = next.help;
}

/**
 * Read the selected documents into the three groups.
 *
 * Shared sections come first and in registry order, so their generic labels are
 * the ones a merged field keeps; a document's own sections follow in the order
 * the documents were selected.
 */
export function groupFields(registry: DocumentRegistry, documents: DocumentDefinition[]): GroupedQuestions {
  const groups = new Map<GroupKey, GroupedSection[]>(GROUP_ORDER.map((key) => [key, []]));
  const seen = new Map<string, GroupedField>();

  const add = (group: GroupKey, section: GroupedSection): void => {
    if (section.fields.length > 0) groups.get(group)?.push(section);
  };

  const take = (fields: DocumentField[] | undefined, document?: LocalizedText): GroupedField[] => {
    const taken: GroupedField[] = [];
    for (const field of fields ?? []) {
      const already = seen.get(field.key);
      if (already) {
        merge(already, field);
        if (document) already.alsoAsked.push({ document, label: field.label });
        continue;
      }
      const copy: GroupedField = { ...field, alsoAsked: [] };
      seen.set(field.key, copy);
      taken.push(copy);
    }
    return taken;
  };

  const referenced: string[] = [];
  for (const doc of documents) {
    for (const section of doc.sections) {
      if (section.ref && !referenced.includes(section.ref)) referenced.push(section.ref);
    }
  }
  for (const section of registry.shared_sections) {
    if (!section.key || !referenced.includes(section.key)) continue;
    add(SHARED_GROUPS[section.key] ?? "additions", {
      key: section.key,
      label: section.label,
      fields: take(section.fields),
    });
  }

  const covered: DocumentDefinition[] = [];
  for (const doc of documents) {
    const own = doc.sections.filter((s): s is DocumentSection => !s.ref && !!s.fields?.length);
    const fields = own.flatMap((section) => take(section.fields, doc.short_label ?? doc.label));
    if (fields.length === 0) covered.push(doc);
    add("additions", { key: `doc:${doc.key}`, label: doc.label, fields });
  }

  return {
    groups: GROUP_ORDER.map((key) => ({ key, sections: groups.get(key) ?? [] })).filter(
      (group) => group.sections.length > 0,
    ),
    covered,
  };
}
