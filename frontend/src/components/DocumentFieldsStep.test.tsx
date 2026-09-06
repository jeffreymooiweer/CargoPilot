/**
 * The shipment details step: telling before walking on, and being reachable
 * from somewhere else.
 *
 * Two things are pinned. **Next tells first.** A form with required fields
 * still empty says which, on the fields themselves and in a summary above
 * them — and then lets the user go on anyway, because CargoPilot does not
 * block a document it cannot finish; the export step keeps saying what is
 * missing and the server has the last word. Nothing is marked while somebody
 * is still typing: that is the difference between telling and nagging.
 *
 * **And a field can be arrived at.** The export step names a missing field by
 * its key; this step opens the form that field is on, puts the cursor in it,
 * and offers the way straight back to where the question was asked. Before
 * v1.196.0 the notice was text, and getting to the field meant pressing Back,
 * finding the form, finding the field, and walking forward again.
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import DocumentFieldsStep, { fieldId } from "./DocumentFieldsStep";
import { DocumentDefinition, DocumentRegistry } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options && "count" in options ? `${key}:${options.count}` : key,
    i18n: { language: "nl" },
  }),
}));

const text = (nl: string) => ({ nl, en: nl });

const REGISTRY: DocumentRegistry = {
  registry_version: "test",
  field_statuses: {} as DocumentRegistry["field_statuses"],
  modalities: [],
  shared_sections: [
    {
      key: "parties",
      label: text("Partijen"),
      fields: [
        { key: "consignor_name", label: text("Afzender"), status: "USER_REQUIRED", type: "text" },
        { key: "notify_party", label: text("Notify"), status: "USER_OPTIONAL", type: "text" },
      ],
    },
  ],
  documents: [],
};

const CMR: DocumentDefinition = {
  key: "cmr",
  label: text("CMR"),
  short_label: text("CMR"),
  category: "official",
  issue_status: text("Voorbereid"),
  exporter: "pdf_template",
  dg_profile: null,
  sections: [
    { ref: "parties" },
    {
      key: "cmr_own",
      label: text("CMR-velden"),
      fields: [
        { key: "place_of_issue", label: text("Plaats van opmaak"), status: "USER_REQUIRED", type: "text" },
      ],
    },
  ],
};

function Harness({ focusField, returnLabel, onReturn, onDone }: {
  focusField?: string | null;
  returnLabel?: string;
  onReturn?: () => void;
  onDone?: () => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  return (
    <DocumentFieldsStep
      registry={REGISTRY}
      documents={[CMR]}
      values={values}
      onChange={setValues}
      focusField={focusField}
      returnLabel={returnLabel}
      onReturn={onReturn}
      onDone={onDone}
    />
  );
}

describe("Next tells before it walks on", () => {
  it("names the empty required fields instead of moving to the next form", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "wizard.next" }));
    expect(screen.getByRole("alert")).toHaveTextContent("docfields.stillEmpty:1");
    // Still on the shared form: it did not walk on with the field empty.
    expect(screen.getByLabelText(/Afzender/)).toBeInTheDocument();
  });

  it("marks the field itself, and unmarks it the moment something is typed", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "wizard.next" }));
    expect(screen.getByText("docfields.fieldMissing")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/Afzender/), "Mooiweer BV");
    expect(screen.queryByText("docfields.fieldMissing")).toBeNull();
  });

  it("says nothing while somebody is only typing", async () => {
    render(<Harness />);
    await userEvent.type(screen.getByLabelText(/Afzender/), "Moo");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByText("docfields.fieldMissing")).toBeNull();
  });

  it("a second press goes on regardless: nothing here is blocked", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "wizard.next" }));
    await userEvent.click(screen.getByRole("button", { name: "docfields.continueAnyway" }));
    // On the CMR's own form now.
    expect(screen.getByLabelText(/Plaats van opmaak/)).toBeInTheDocument();
  });

  it("a summary entry takes the cursor to its field", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "wizard.next" }));
    await userEvent.click(within(screen.getByRole("alert")).getByRole("button", { name: "Afzender" }));
    expect(screen.getByLabelText(/Afzender/)).toHaveFocus();
  });
});

describe("arriving at one field from somewhere else", () => {
  it("opens the form the field is on and puts the cursor in it", async () => {
    render(<Harness focusField="place_of_issue" />);
    // The field lives on the CMR's own form, not the shared one.
    await waitFor(() => expect(screen.getByLabelText(/Plaats van opmaak/)).toHaveFocus());
    expect(document.getElementById(fieldId("place_of_issue"))).toBeTruthy();
  });

  it("offers the way straight back to where the question was asked", async () => {
    const onReturn = vi.fn();
    render(<Harness focusField="consignor_name" returnLabel="wizard.backToOverview" onReturn={onReturn} />);
    await userEvent.click(screen.getByRole("button", { name: "wizard.backToOverview" }));
    expect(onReturn).toHaveBeenCalled();
  });

  it("without a caller waiting there is no return action", () => {
    render(<Harness />);
    expect(screen.queryByRole("button", { name: "wizard.backToOverview" })).toBeNull();
  });
});
