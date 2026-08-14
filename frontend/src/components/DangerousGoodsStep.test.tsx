/** What the derivation is allowed to overwrite, and what it is not.
 *
 * `dg/prepare` fills in what follows from the UN number: the class, the proper
 * shipping name, the labels, the derived totals. It is debounced by 250 ms and
 * then takes a round trip, and it only runs again when the UN number, the counts
 * or the packaging change.
 *
 * That leaves a window. Everything else on the form — a total typed by hand, a
 * technical name — can be typed while a request is out, into a form the reply
 * knows nothing about. Taking the reply as the new truth put the old value back:
 * the field emptied itself under the cursor, and it did so a beat after the
 * typing, which is the hardest kind of bug to believe when it happens to you.
 *
 * The fix is not to cancel more, but to apply less. The difference between what
 * the request was built from and what came back is exactly what the backend
 * contributed; only that is applied, and only where the form still has nothing of
 * its own. These are the cases that says so.
 */
import { describe, expect, it } from "vitest";

import { DgEntry } from "../api/client";
import { mergeDerived } from "./DangerousGoodsStep";

function entry(products: Record<string, unknown>[]): DgEntry {
  return { line_id: 1, vehicle: "", products: products as DgEntry["products"] };
}

describe("mergeDerived", () => {
  it("neemt over wat de afleiding heeft ingevuld", () => {
    const sent = [entry([{ un_number: "1203" }])];
    const derived = [entry([{ un_number: "1203", class: "3", packing_group: "II" }])];
    expect(mergeDerived(sent, sent, derived)[0].products[0]).toEqual({
      un_number: "1203",
      class: "3",
      packing_group: "II",
    });
  });

  it("laat staan wat de gebruiker intussen typte", () => {
    // The whole point. The request left with an empty total; the user filled it
    // in while the reply was in the air.
    const sent = [entry([{ un_number: "1203", adr_total_quantity: "" }])];
    const current = [entry([{ un_number: "1203", adr_total_quantity: "250" }])];
    const derived = [entry([{ un_number: "1203", adr_total_quantity: "", class: "3" }])];

    const merged = mergeDerived(current, sent, derived);
    expect(merged[0].products[0].adr_total_quantity).toBe("250");
    expect(merged[0].products[0].class).toBe("3");
  });

  it("overschrijft een handmatige correctie niet", () => {
    // Correcting a derived value is the same shape as filling an empty one, and
    // was the reason the derivation only ever completed blanks.
    const sent = [entry([{ un_number: "1203", technical_name: "" }])];
    const current = [entry([{ un_number: "1203", technical_name: "eigen naam" }])];
    const derived = [entry([{ un_number: "1203", technical_name: "afgeleide naam" }])];

    expect(mergeDerived(current, sent, derived)[0].products[0].technical_name)
      .toBe("eigen naam");
  });

  it("laat een antwoord vallen als de vorm intussen veranderde", () => {
    // A position added while the request was out shifts every index after it.
    // Applying the reply by index would move one product's data onto another,
    // and a new derivation is already on its way.
    const sent = [entry([{ un_number: "1203" }])];
    const current = [entry([{ un_number: "1203" }]), entry([{ un_number: "1263" }])];
    const derived = [entry([{ un_number: "1203", class: "3" }])];

    expect(mergeDerived(current, sent, derived)).toBe(current);
  });

  it("laat een antwoord vallen als er een product bij kwam", () => {
    const sent = [entry([{ un_number: "1203" }])];
    const current = [entry([{ un_number: "1203" }, { un_number: "1263" }])];
    const derived = [entry([{ un_number: "1203", class: "3" }])];

    expect(mergeDerived(current, sent, derived)[0].products[0].class).toBeUndefined();
  });

  it("geeft dezelfde objecten terug als er niets te melden is", () => {
    // Identity matters here: a fresh object every keystroke would re-render the
    // whole step and cost the field its focus.
    const current = [entry([{ un_number: "1203", class: "3" }])];
    const merged = mergeDerived(current, current, current);
    expect(merged[0].products[0]).toBe(current[0].products[0]);
  });
});
