/**
 * Het nalevingspaneel: wat er op het scherm staat moet bij de invoer horen die
 * er nú staat.
 *
 * Dat klinkt vanzelfsprekend, maar het is precies waar dit soort schermen
 * stukgaat. Een uitkomst is groen, de gebruiker verhoogt een hoeveelheid, en
 * het groen blijft staan omdat niemand het heeft weggehaald. Of twee controles
 * lopen tegelijk en de tráágste — die bij oudere invoer hoort — komt als
 * laatste binnen en wint. In beide gevallen ziet de gebruiker een geldige
 * uitslag voor een zending die niet meer bestaat.
 *
 * Deze tests draaien op een nagebootste API zodat het gedrag van het paneel
 * wordt vastgelegd en niet dat van de rekenlaag; die heeft haar eigen tests.
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

/** De debounce laten aflopen binnen act(), zodat React de statuswijziging
 * verwerkt zoals in de browser. */
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

    expect(check).not.toHaveBeenCalled(); // nog binnen de debounce
    await tick();
    await waitFor(() => expect(check).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/compliance.totalPoints/)).toHaveTextContent("300");
  });

  it("wist de vorige uitkomst zodra de invoer verandert", async () => {
    vi.spyOn(api, "dgCompliance").mockResolvedValue(result(300));
    const view = render(<DgCompliancePanel entries={entries("20 L")} profiles={["ADR"]} />);
    await tick();
    expect(await screen.findByText(/compliance.totalPoints/)).toBeInTheDocument();

    // Meer benzine: de oude uitslag hoort per direct weg te zijn, nog vóór de
    // nieuwe controle is teruggekomen. Blijven staan zou een geldige uitslag
    // tonen voor een zending die niet meer bestaat.
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
    // De eerste controle blijft hangen; de tweede is er meteen. Wint de eerste
    // alsnog omdat hij later binnenkomt, dan staat er een uitkomst op het
    // scherm die bij invoer van twee wijzigingen geleden hoort.
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
    // De bevindingen zijn ermee gerekend, dus de gebruiker moet dit eerst zien.
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
    // DOCUMENT_POSITION_FOLLOWING: de scheidingsbevinding komt ná de melding
    // over de verlopen editie.
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
    // De 3.5.5-waarschuwing (1000 colli) hoort in dezelfde sectie te staan.
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
    // Een fout mag niet achter een dichtgeklapte kop schuilgaan.
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
    // De kop verzwijgt niets: het aantal staat erin.
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
