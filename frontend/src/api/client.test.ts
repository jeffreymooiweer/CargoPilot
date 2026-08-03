/**
 * Wat de gebruiker te zien krijgt als de server de invoer weigert.
 *
 * Bij een 422 stuurt FastAPI geen zin maar een lijst met `{loc, msg}` per veld.
 * Die ging rechtstreeks naar `new Error()`, wat "[object Object]" opleverde:
 * de gebruiker zag dát er iets mis was, maar niet wat, en al helemaal niet
 * welk veld. Sinds v1.24.0 weigert de compliance-endpoint onbruikbare invoer,
 * dus dit is geen randgeval meer maar de normale weg.
 */
import { describe, expect, it } from "vitest";

import { describeDetail } from "./client";

describe("een validatiefout van FastAPI leesbaar maken", () => {
  it("noemt het veld en de reden", () => {
    const text = describeDetail([
      {
        loc: ["body", "entries", 0, "products", 1, "adr_total_quantity"],
        msg: "Value error, hoeveelheid '-5 L' moet groter dan nul zijn",
        type: "value_error",
      },
    ]);
    expect(text).toBe(
      "entries → 0 → products → 1 → adr_total_quantity: " +
        "hoeveelheid '-5 L' moet groter dan nul zijn",
    );
  });

  it("laat 'body' weg, want dat zegt een gebruiker niets", () => {
    expect(describeDetail([{ loc: ["body", "profiles", 0], msg: "onbekend profiel" }]))
      .toBe("profiles → 0: onbekend profiel");
  });

  it("zet meerdere fouten onder elkaar", () => {
    const text = describeDetail([
      { loc: ["body", "profiles", 0], msg: "onbekend profiel" },
      { loc: ["body", "entries", 0], msg: "iets anders" },
    ]);
    expect(text.split("\n")).toHaveLength(2);
  });

  it("laat een gewone tekstmelding met rust", () => {
    expect(describeDetail("entries required")).toBe("entries required");
  });

  it("valt terug op een nette zin als er niets bruikbaars in zit", () => {
    expect(describeDetail(undefined)).toBe("Request failed");
    expect(describeDetail([])).toBe("Request failed");
    expect(describeDetail({})).toBe("Request failed");
  });

  it("levert nooit [object Object] op", () => {
    for (const detail of [[{ loc: ["body"], msg: "x" }], [{}], {}, null, 42]) {
      expect(describeDetail(detail)).not.toContain("[object Object]");
    }
  });
});
