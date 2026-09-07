/**
 * What the dangerous goods step starts from, and who it believes.
 *
 * Three sources feed one product, and the order between them is the point:
 * what the person shipping the goods stated on the line beats what the
 * articles library holds, which beats what the recogniser read out of the
 * description. Everything none of them supplies stays empty for the tables.
 */
import { describe, expect, it } from "vitest";

import type { LineItem } from "../api/client";
import { buildDgEntries } from "./DangerousGoodsStep";

const base: LineItem = {
  line_id: 1, raw: "", description: "Alkyd paint", output_description: "Alkyd paint", quantity: 4, unit: "pcs",
  material: null, product_type: null, weight_each_kg: null, weight_total_kg: null, material_volume_m3: null,
  transport_volume_m3: null, length_cm: null, width_cm: null, height_cm: null, status: "ok", messages: [], include: true,
  dangerous_goods: true, detected_un_numbers: ["1263"],
};

describe("een artikel op de goederenregel", () => {
  it("zet wat de bibliotheek weet in het product, en niet meer", () => {
    const [entry] = buildDgEntries([{
      ...base,
      article: { code: "PAINT-25", name: "Alkyd paint", un_number: "1263", proper_shipping_name: "PAINT",
                 technical_name: "", class: "3", packing_group: "II", type_of_package: "jerrican", net_per_package: "25 L" },
    }]);
    const product = entry.products[0];
    expect(product.un_number).toBe("1263");
    expect(product.proper_shipping_name).toBe("PAINT");
    expect(product.packing_group).toBe("II");
    expect(product.type_of_package).toBe("jerrican");
    expect(product.net_mass_liters_per_package).toBe("25 L");
    expect(product.quantity_packages).toBe("4");
    // Nothing the library did not say.
    expect(product.technical_name ?? "").toBe("");
  });

  it("laat een regel zonder artikel zoals hij was", () => {
    const [entry] = buildDgEntries([base]);
    expect(entry.products[0]).toMatchObject({ un_number: "1263", proper_shipping_name: "", packing_group: "" });
  });
});

describe("de stof zoals hij op de regel is ingevuld", () => {
  it("wint van de herkenning, want de afzender heeft hem getypt", () => {
    const [entry] = buildDgEntries(
      [base],
      [{ confirmed_un: "1993", proper_shipping_name: "BRANDBARE VLOEISTOF, N.E.G.", packing_group: "III" }],
    );
    expect(entry.products[0]).toMatchObject({
      un_number: "1993",
      proper_shipping_name: "BRANDBARE VLOEISTOF, N.E.G.",
      packing_group: "III",
    });
  });

  it("wint ook van het artikel, op de velden die hij noemt", () => {
    const [entry] = buildDgEntries(
      [{
        ...base,
        article: { code: "PAINT-25", name: "Alkyd paint", un_number: "1263", proper_shipping_name: "PAINT",
                   technical_name: "", class: "3", packing_group: "II", type_of_package: "jerrican",
                   net_per_package: "25 L" },
      }],
      [{ packing_group: "III", type_of_package: "vat" }],
    );
    // What the line says, where it says it; the article for the rest.
    expect(entry.products[0]).toMatchObject({
      un_number: "1263",
      proper_shipping_name: "PAINT",
      packing_group: "III",
      type_of_package: "vat",
    });
  });

  it("telt de verpakkingen ook zonder artikel, want dat is het aantal van de regel", () => {
    const [entry] = buildDgEntries([base]);
    expect(entry.products[0].quantity_packages).toBe("4");
  });

  it("laat leeg wat de regel niet zegt, zodat de tabellen het invullen", () => {
    const [entry] = buildDgEntries([base], [{ confirmed_un: "1993" }]);
    expect(entry.products[0].proper_shipping_name).toBe("");
    expect(entry.products[0].packing_group).toBe("");
  });
});
