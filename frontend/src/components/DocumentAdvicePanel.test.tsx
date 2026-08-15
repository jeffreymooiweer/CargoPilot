/**
 * The document advice: three honest groups.
 *
 * "Required" is reserved for what a read provision carries — with dangerous
 * goods, 5.4.1 requires a transport document with the prescribed particulars,
 * and the registry names which document that is per modality. Everything else
 * is recommended (DG support papers, the customary transport document) or
 * possible. Without dangerous goods nothing is called required at all: a
 * commercial document is the consignor's choice.
 */
import { describe, expect, it } from "vitest";

import { buildAdvice } from "./DocumentAdvicePanel";
import { DocumentRegistry } from "../api/client";

const registry = {
  modalities: [
    { key: "road", documents: ["cmr", "avc_waybill", "placarding_sheet", "packing_list"] },
    { key: "inland", documents: ["adn_transport_doc", "stowage_plan", "packing_list"] },
    { key: "sea", documents: ["bl_si", "imo_dgd", "packing_list"] },
  ],
  documents: [
    { key: "cmr", sections: [] },
    { key: "avc_waybill", sections: [] },
    { key: "placarding_sheet", dg_only: true, sections: [] },
    { key: "packing_list", sections: [] },
    { key: "adn_transport_doc", dg_only: true, sections: [] },
    { key: "stowage_plan", dg_only: true, sections: [] },
    { key: "bl_si", sections: [] },
    { key: "imo_dgd", dg_only: true, sections: [] },
  ],
  shared_sections: [],
  modality_defaults: { road: "cmr", inland: "packing_list", sea: "bl_si" },
  dg_transport_documents: { road: "cmr", inland: "adn_transport_doc", sea: "imo_dgd" },
} as unknown as DocumentRegistry;

describe("buildAdvice", () => {
  it("without dangerous goods nothing is required and the customary document is recommended", () => {
    const advice = buildAdvice(registry, "road", false);
    expect(advice.required).toEqual([]);
    expect(advice.recommended).toEqual(["cmr"]);
    expect(advice.preselected).toEqual(["cmr"]);
    expect(advice.possible).toContain("placarding_sheet");
  });

  it("with dangerous goods the 5.4.1 document is required and the DG papers recommended", () => {
    const advice = buildAdvice(registry, "road", true);
    expect(advice.required).toEqual(["cmr"]);
    expect(advice.recommended).toContain("placarding_sheet");
    // The AVC waybill is an alternative transport document, not a DG paper.
    expect(advice.possible).toContain("avc_waybill");
    expect(advice.preselected).toContain("cmr");
  });

  it("each modality names its own 5.4.1 document", () => {
    expect(buildAdvice(registry, "inland", true).required).toEqual(["adn_transport_doc"]);
    expect(buildAdvice(registry, "sea", true).required).toEqual(["imo_dgd"]);
  });

  it("at sea the shipping instructions stay recommended next to the required declaration", () => {
    const advice = buildAdvice(registry, "sea", true);
    expect(advice.recommended).toContain("bl_si");
  });

  it("every offered document lands in exactly one group", () => {
    for (const needsDg of [false, true]) {
      const advice = buildAdvice(registry, "road", needsDg);
      const all = [...advice.required, ...advice.recommended, ...advice.possible].sort();
      expect(all).toEqual(["avc_waybill", "cmr", "packing_list", "placarding_sheet"]);
    }
  });
});
