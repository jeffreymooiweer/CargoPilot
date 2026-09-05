/**
 * A goods line picked from the articles library seeds its dangerous goods
 * product with what the library knows — and only with that.
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
