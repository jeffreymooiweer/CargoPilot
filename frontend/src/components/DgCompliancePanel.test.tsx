/**
 * The compliance panel: what is on the screen has to belong to the input that is
 * there *now*.
 *
 * That sounds obvious, but it is precisely where screens like this come apart.
 * An outcome is green, the user increases a quantity, and the green stays
 * because nobody removed it. Or two checks run at once and the *slower* one —
 * belonging to older input — comes in last and wins. In both cases the user sees
 * a valid result for a consignment that no longer exists.
 *
 * These tests run on a mocked API so that the behaviour of the panel is
 * recorded and not that of the calculation layer; that has tests of its own.
 */
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DgCompliancePanel from "./DgCompliancePanel";
import { api, DgComplianceResult, DgEntry } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key} ${JSON.stringify(options)}` : key,
    i18n: { language: "nl" },
  }),
}));

function entries(quantity: string): DgEntry[] {
  return [
    {
      vehicle: "WAGEN-1",
      products: [
        {
          un_number: "1203",
          proper_shipping_name: "BENZINE",
          class: "3",
          packing_group: "II",
          transport_category: "2",
          adr_total_quantity: quantity,
        },
      ],
    } as unknown as DgEntry,
  ];
}

function result(totalPoints: number): DgComplianceResult {
  return {
    adr_points: {
      rows: [],
      total_points: totalPoints,
      threshold: 1000,
      status: totalPoints > 1000 ? "above_threshold" : "exempt_possible",
      category0_products: [],
      incomplete_products: [],
      quantity_units_note: "",
      exempt_provisions: [],
      still_required: [],
    },
  } as unknown as DgComplianceResult;
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

/** Let the debounce elapse inside act(), so React processes the state change
 * the way it does in the browser. */
async function tick(ms = 500) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("het resultaat hoort bij de invoer die er nu staat", () => {
  it("controleert vanzelf na de debounce, zonder dat er geklikt wordt", async () => {
    const check = vi.spyOn(api, "dgCompliance").mockResolvedValue(result(300));
    render(<DgCompliancePanel entries={entries("20 L")} profiles={["ADR"]} />);

    expect(check).not.toHaveBeenCalled(); // still inside the debounce
    await tick();
    await waitFor(() => expect(check).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/compliance.totalPoints/)).toHaveTextContent("300");
  });

  it("wist de vorige uitkomst zodra de invoer verandert", async () => {
    vi.spyOn(api, "dgCompliance").mockResolvedValue(result(300));
    const view = render(<DgCompliancePanel entries={entries("20 L")} profiles={["ADR"]} />);
    await tick();
    expect(await screen.findByText(/compliance.totalPoints/)).toBeInTheDocument();

    // More petrol: the old result should be gone immediately, before the new
    // check has even come back. Leaving it would show a valid result for a
    // consignment that no longer exists.
    view.rerender(<DgCompliancePanel entries={entries("600 L")} profiles={["ADR"]} />);
    expect(screen.queryByText(/compliance.totalPoints/)).not.toBeInTheDocument();
  });

  it("controleert opnieuw na een wijziging", async () => {
    const check = vi.spyOn(api, "dgCompliance").mockResolvedValue(result(300));
    const view = render(<DgCompliancePanel entries={entries("20 L")} profiles={["ADR"]} />);
    await tick();
    await waitFor(() => expect(check).toHaveBeenCalledTimes(1));

    view.rerender(<DgCompliancePanel entries={entries("600 L")} profiles={["ADR"]} />);
    await tick();
    await waitFor(() => expect(check).toHaveBeenCalledTimes(2));

    const lastCall = check.mock.calls[1][0] as DgEntry[];
    expect((lastCall[0] as never as { products: { adr_total_quantity: string }[] })
      .products[0].adr_total_quantity).toBe("600 L");
  });

  it("laat een trage oudere reactie de nieuwere niet overschrijven", async () => {
    // The first check hangs; the second is there straight away. If the first
    // wins anyway because it arrives later, the screen shows an outcome
    // belonging to input from two changes ago.
    let releaseFirst: (value: DgComplianceResult) => void = () => {};
    const slowFirst = new Promise<DgComplianceResult>((resolve) => {
      releaseFirst = resolve;
    });
    const check = vi
      .spyOn(api, "dgCompliance")
      .mockReturnValueOnce(slowFirst)
      .mockResolvedValueOnce(result(1200));

    const view = render(<DgCompliancePanel entries={entries("20 L")} profiles={["ADR"]} />);
    await tick();
    await waitFor(() => expect(check).toHaveBeenCalledTimes(1));

    view.rerender(<DgCompliancePanel entries={entries("600 L")} profiles={["ADR"]} />);
    await tick();
    await waitFor(() => expect(check).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(/compliance.totalPoints/)).toHaveTextContent("1200");

    releaseFirst(result(300));
    await tick(50);

    expect(screen.getByText(/compliance.totalPoints/)).toHaveTextContent("1200");
    expect(screen.getByText(/compliance.totalPoints/)).not.toHaveTextContent("300");
  });
});

describe("een validatiefout van de server", () => {
  it("komt leesbaar op het scherm en niet als [object Object]", async () => {
    vi.spyOn(api, "dgCompliance").mockRejectedValue(
      new Error("producten → 0 → adr_total_quantity: hoeveelheid '-5 L' moet groter dan nul zijn"),
    );
    render(<DgCompliancePanel entries={entries("-5 L")} profiles={["ADR"]} />);
    await tick();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("adr_total_quantity");
    expect(alert).toHaveTextContent("groter dan nul");
    expect(alert.textContent).not.toContain("[object Object]");
  });

  it("laat geen oude uitkomst naast de foutmelding staan", async () => {
    const check = vi.spyOn(api, "dgCompliance").mockResolvedValue(result(300));
    const view = render(<DgCompliancePanel entries={entries("20 L")} profiles={["ADR"]} />);
    await tick();
    expect(await screen.findByText(/compliance.totalPoints/)).toBeInTheDocument();

    check.mockRejectedValueOnce(new Error("adr_total_quantity: moet groter dan nul zijn"));
    view.rerender(<DgCompliancePanel entries={entries("-5 L")} profiles={["ADR"]} />);
    await tick();

    await screen.findByRole("alert");
    expect(screen.queryByText(/compliance.totalPoints/)).not.toBeInTheDocument();
  });
});

describe("een verlopen regelset", () => {
  it("staat bovenaan, vóór de inhoudelijke bevindingen", async () => {
    // The findings were computed with it, so the user has to see this first.
    vi.spyOn(api, "dgCompliance").mockResolvedValue({
      rule_set_warnings: [{
        rule: "IATA DGR — luchtvracht",
        severity: "warning",
        message: "67e editie (2026) is verlopen op 2026-12-31.",
        products: "IATA",
      }],
      iata_segregation: [{
        rule: "IATA 9.3.2", severity: "warning", message: "iets over scheiding", products: "UN 1203",
      }],
    } as unknown as DgComplianceResult);

    render(<DgCompliancePanel entries={entries("20 L")} profiles={["IATA"]} />);
    await tick();

    const stale = await screen.findByText("IATA DGR — luchtvracht");
    const segregation = await screen.findByText("IATA 9.3.2");
    // DOCUMENT_POSITION_FOLLOWING: the segregation finding comes *after* the
    // message about the expired edition.
    expect(stale.compareDocumentPosition(segregation) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy();
  });

  it("toont waar de uitkomst mee is gerekend", async () => {
    vi.spyOn(api, "dgCompliance").mockResolvedValue({
      regulatory_manifest: {
        manifest_id: "37dcc090baea0915",
        editions: { iata: "67e editie (2026)" },
        expired: [],
      },
    } as unknown as DgComplianceResult);

    render(<DgCompliancePanel entries={entries("20 L")} profiles={["IATA"]} />);
    await tick();

    expect(await screen.findByText(/compliance.manifest/)).toHaveTextContent("37dcc090baea0915");
  });
});

describe("de LQ/EQ-toets van 3.4 en 3.5", () => {
  it("toont per regel de LQ- en EQ-status met de bijbehorende melding", async () => {
    vi.spyOn(api, "dgCompliance").mockResolvedValue({
      lq_eq: {
        rows: [{
          product: "UN 1263 PAINT",
          position: "WAGEN-1",
          lq: {
            value: "5 L",
            status: "within_limits",
            message: "Binnen de grenzen van 3.4.",
          },
          eq: {
            code: "E2",
            status: "not_within",
            message: "De netto hoeveelheid per binnenverpakking is groter dan 30 g/ml.",
          },
        }],
        status: "checked",
        warnings: [{
          rule: "ADR/IMDG 3.5.5",
          severity: "warning",
          message: "Ten hoogste 1000 colli per voertuig of container.",
          products: "UN 1263 PAINT",
        }],
        basis: "ADR 3.4 / 3.5 (Tabel A kolom 7a/7b)",
        basis_note: null,
        note: "Binnen de grenzen vallen is niet hetzelfde als vrijgesteld zijn.",
      },
    } as unknown as DgComplianceResult);

    render(<DgCompliancePanel entries={entries("20 L")} profiles={["ADR"]} />);
    await tick();

    expect(await screen.findByText("compliance.lqEqTitle")).toBeInTheDocument();
    expect(screen.getByText(/LQ 5 L/)).toHaveTextContent("lqeqStatus.within_limits");
    expect(screen.getByText(/EQ E2/)).toHaveTextContent("lqeqStatus.not_within");
    expect(screen.getByText("Binnen de grenzen van 3.4.")).toBeInTheDocument();
    // The 3.5.5 warning (1000 packages) belongs in the same section.
    expect(screen.getByText("ADR/IMDG 3.5.5")).toBeInTheDocument();
    expect(screen.getByText(/vrijgesteld zijn/)).toBeInTheDocument();
  });

  it("verzwijgt de sectie wanneer er geen regels zijn beoordeeld", async () => {
    vi.spyOn(api, "dgCompliance").mockResolvedValue({
      lq_eq: {
        rows: [],
        status: "not_checked",
        warnings: [],
        basis: "ADR 3.4 / 3.5 (Tabel A kolom 7a/7b)",
        basis_note: null,
        note: "",
      },
    } as unknown as DgComplianceResult);

    render(<DgCompliancePanel entries={entries("20 L")} profiles={["ADR"]} />);
    await tick();

    expect(screen.queryByText("compliance.lqEqTitle")).not.toBeInTheDocument();
  });
});

describe("de inklapbare secties", () => {
  it("draagt de aantallen in de kop en klapt een sectie met fouten open", async () => {
    vi.spyOn(api, "dgCompliance").mockResolvedValue({
      imdg_segregation: [
        { rule: "IMDG 7.2.4", severity: "error", message: "scheiding vereist", products: "A × B" },
        { rule: "IMDG 16b", severity: "warning", message: "let op", products: "A" },
      ],
    } as unknown as DgComplianceResult);

    render(<DgCompliancePanel entries={entries("20 L")} profiles={["IMDG"]} />);
    await tick();

    expect(await screen.findByText(/1 × compliance.sevError/)).toBeInTheDocument();
    expect(screen.getByText(/1 × compliance.sevWarning/)).toBeInTheDocument();
    // An error must not hide behind a collapsed heading.
    const section = screen.getByText("IMDG 7.2.4").closest("details");
    expect(section?.open).toBe(true);
  });

  it("begint zonder fouten dichtgeklapt, maar de bevindingen blijven in de DOM", async () => {
    vi.spyOn(api, "dgCompliance").mockResolvedValue({
      imdg_segregation: [
        { rule: "IMDG 16b", severity: "warning", message: "let op", products: "A" },
      ],
    } as unknown as DgComplianceResult);

    render(<DgCompliancePanel entries={entries("20 L")} profiles={["IMDG"]} />);
    await tick();

    const section = screen.getByText("IMDG 16b").closest("details");
    expect(section?.open).toBe(false);
    // The heading conceals nothing: the count is in it.
    expect(screen.getByText(/1 × compliance.sevWarning/)).toBeInTheDocument();
  });
});

describe("wanneer het paneel niets te zeggen heeft", () => {
  it("toont het zichzelf niet zonder stoffen of zonder profiel", () => {
    const { container } = render(<DgCompliancePanel entries={[]} profiles={["ADR"]} />);
    expect(container).toBeEmptyDOMElement();

    const zonderProfiel = render(<DgCompliancePanel entries={entries("20 L")} profiles={[]} />);
    expect(zonderProfiel.container).toBeEmptyDOMElement();
  });
});

describe("de tunnelsectie", () => {
  function withTunnel(tunnel: Record<string, unknown>): DgComplianceResult {
    return { ...result(400), adr_tunnel: tunnel } as unknown as DgComplianceResult;
  }

  it("toont de code van de hele lading en de codes waaruit hij volgt", async () => {
    vi.spyOn(api, "dgCompliance").mockResolvedValue(
      withTunnel({
        rows: [
          { product: "UN 1203", code: "D/E" },
          { product: "UN 1017", code: "C/D" },
        ],
        code: "C/D",
        restricted_categories: ["D", "E"],
        explosive_mass_kg: null,
        status: "derived",
        message: "De meest restrictieve code van de hele lading is C/D.",
        basis: "ADR 8.6.3 / 8.6.4",
        note: "Berekend voor vervoer in colli.",
      }),
    );
    render(<DgCompliancePanel entries={entries("400")} profiles={["ADR"]} />);

    await waitFor(() =>
      expect(screen.getByText(/meest restrictieve code/)).toBeInTheDocument(),
    );
    // Both the derived code and the codes it was derived from: a user who
    // disagrees has to be able to see where the answer came from.
    expect(screen.getByText("(C/D)")).toBeInTheDocument();
    expect(screen.getByText(/UN 1203/)).toBeInTheDocument();
    expect(screen.getByText(/UN 1017/)).toBeInTheDocument();
  });

  it("blijft staan als er juist geen beperking geldt", async () => {
    // 8.6.3.3: a consignment inside the 1.1.3.6 exemption gets no code, and an
    // empty section would read as "not checked" rather than as an answer.
    vi.spyOn(api, "dgCompliance").mockResolvedValue(
      withTunnel({
        rows: [{ product: "UN 1203", code: "D/E" }],
        code: null,
        restricted_categories: [],
        explosive_mass_kg: null,
        status: "exempt",
        message: "Alle goederen worden overeenkomstig 1.1.3 vervoerd.",
        basis: "ADR 8.6.3 / 8.6.4",
        note: "Berekend voor vervoer in colli.",
      }),
    );
    render(<DgCompliancePanel entries={entries("200")} profiles={["ADR"]} />);

    await waitFor(() =>
      expect(screen.getByText(/overeenkomstig 1.1.3/)).toBeInTheDocument(),
    );
    expect(screen.getByText("compliance.tunnelStatus.exempt")).toBeInTheDocument();
  });
});
