/**
 * Grouping the questions by what they mean, instead of by which document asks.
 *
 * What is pinned here is the arithmetic of the merge: a key is asked once, a
 * key some document requires is required, and a document whose every question
 * was already asked adds nothing to the form — it is reported as covered
 * rather than shown as an empty heading.
 */
import { describe, expect, it } from "vitest";

import { groupFields } from "./documentGroups";
import { DocumentDefinition, DocumentRegistry } from "../api/client";

const text = (value: string) => ({ nl: value, en: value });

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
        { key: "carrier_name", label: text("Vervoerder"), status: "USER_OPTIONAL", type: "text" },
      ],
    },
    {
      key: "locations",
      label: text("Route"),
      fields: [{ key: "loading_point", label: text("Laadplaats"), status: "USER_REQUIRED", type: "text" }],
    },
    {
      key: "references",
      label: text("Referenties"),
      fields: [{ key: "booking_number", label: text("Boekingsnummer"), status: "USER_OPTIONAL", type: "text" }],
    },
  ],
  documents: [],
};

function doc(key: string, refs: string[], fields: DocumentDefinition["sections"][number]["fields"]): DocumentDefinition {
  return {
    key,
    label: text(key.toUpperCase()),
    short_label: text(key.toUpperCase()),
    category: "official",
    issue_status: text("Voorbereid"),
    exporter: "generic",
    dg_profile: null,
    sections: [
      ...refs.map((ref) => ({ ref })),
      ...(fields?.length ? [{ key: `${key}_details`, label: text(`${key} details`), fields }] : []),
    ],
  };
}

const CMR = doc("cmr", ["parties", "locations", "references"], [
  { key: "container_number", label: text("Containernummer (vak 15)"), status: "OPERATIONAL", type: "text" },
  { key: "established_place", label: text("Opgemaakt te (vak 21)"), status: "USER_REQUIRED", type: "text" },
]);

const IMO = doc("imo_dgd", ["parties", "locations"], [
  { key: "container_number", label: text("Containernummer"), status: "USER_REQUIRED", type: "text" },
  { key: "vessel_flight", label: text("Schip"), status: "USER_OPTIONAL", type: "text" },
]);

const PLACARDS = doc("placarding_sheet", ["parties"], []);

describe("grouping the questions", () => {
  it("puts the parties, the route and the additions in three groups", () => {
    const { groups } = groupFields(REGISTRY, [CMR]);
    expect(groups.map((g) => g.key)).toEqual(["parties", "route", "additions"]);
    expect(groups[0].sections[0].fields.map((f) => f.key)).toEqual(["consignor_name", "carrier_name"]);
    expect(groups[1].sections[0].fields.map((f) => f.key)).toEqual(["loading_point"]);
    // The references and what the CMR needs beyond them, in that order.
    expect(groups[2].sections.map((s) => s.key)).toEqual(["references", "doc:cmr"]);
  });

  it("asks a key once, however many documents want it", () => {
    const { groups } = groupFields(REGISTRY, [CMR, IMO]);
    const keys = groups.flatMap((g) => g.sections.flatMap((s) => s.fields.map((f) => f.key)));
    expect(keys.filter((key) => key === "container_number")).toHaveLength(1);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("says who else is asking, and what they call it", () => {
    const { groups } = groupFields(REGISTRY, [CMR, IMO]);
    const container = groups
      .flatMap((g) => g.sections.flatMap((s) => s.fields))
      .find((f) => f.key === "container_number");
    expect(container?.alsoAsked.map((one) => one.label.nl)).toEqual(["Containernummer"]);
    expect(container?.alsoAsked[0].document.nl).toBe("IMO_DGD");
  });

  it("a field one document requires is required, whatever the first one called it", () => {
    const { groups } = groupFields(REGISTRY, [CMR, IMO]);
    const container = groups
      .flatMap((g) => g.sections.flatMap((s) => s.fields))
      .find((f) => f.key === "container_number");
    // The CMR has it as operational; the IMO form requires it.
    expect(container?.status).toBe("USER_REQUIRED");
    expect(container?.label.nl).toBe("Containernummer (vak 15)");
  });

  it("a document with no questions of its own adds no heading", () => {
    const { groups, covered } = groupFields(REGISTRY, [CMR, PLACARDS]);
    expect(groups[2].sections.map((s) => s.key)).toEqual(["references", "doc:cmr"]);
    expect(covered.map((d) => d.key)).toEqual(["placarding_sheet"]);
  });

  it("a document whose every question was already asked is covered too", () => {
    const twice = doc("second_cmr", ["parties"], [
      { key: "established_place", label: text("Opgemaakt te"), status: "USER_REQUIRED", type: "text" },
    ]);
    const { groups, covered } = groupFields(REGISTRY, [CMR, twice]);
    expect(groups[2].sections.map((s) => s.key)).toEqual(["references", "doc:cmr"]);
    expect(covered.map((d) => d.key)).toEqual(["second_cmr"]);
  });

  it("leaves out a shared section no selected document refers to", () => {
    const { groups } = groupFields(REGISTRY, [IMO]);
    // The IMO form does not use the references section.
    expect(groups.flatMap((g) => g.sections.map((s) => s.key))).not.toContain("references");
  });
});
