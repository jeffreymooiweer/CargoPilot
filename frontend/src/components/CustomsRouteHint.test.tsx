/**
 * The route decides the customs conditions; the hint says so, or nothing.
 *
 * Three things are pinned: a verdict the server gives is shown with its
 * ground and the two country codes; "unknown" shows nothing at all, so a
 * route the reader could not place leaves the field as it was; and the hook
 * asks only when a route field is filled, debounced, and swallows a failed
 * request rather than letting it reach the form.
 */
import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, CustomsVerdict } from "../api/client";
import CustomsRouteHint, { useCustomsRoute } from "./CustomsRouteHint";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "nl" },
  }),
}));

const entering: CustomsVerdict = {
  field: "ens_mrn",
  applies: "yes",
  reason: "ens_entering",
  origin: "US",
  destination: "NL",
};

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("CustomsRouteHint", () => {
  it("shows the verdict with its ground and the route it was read from", () => {
    render(<CustomsRouteHint verdict={entering} />);
    expect(screen.getByText("customsRoute.applies")).toBeInTheDocument();
    expect(screen.getByText("customsRoute.ens_entering")).toBeInTheDocument();
  });

  it("shows an exemption in its own tone", () => {
    render(<CustomsRouteHint verdict={{ ...entering, field: "aes_itn", applies: "exempt", reason: "aes_canada" }} />);
    expect(screen.getByText("customsRoute.exempt")).toBeInTheDocument();
    expect(screen.getByText("customsRoute.aes_canada")).toBeInTheDocument();
  });

  it("says nothing when the route could not be placed", () => {
    const { container } = render(<CustomsRouteHint verdict={{ ...entering, applies: "unknown", reason: "ens_unknown" }} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("says nothing without a verdict", () => {
    const { container } = render(<CustomsRouteHint verdict={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("useCustomsRoute", () => {
  it("does not ask while no route field is filled", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(api, "customsRoute");
    const { result } = renderHook(() => useCustomsRoute({ consignor_name: "Verzender BV" }));
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    expect(spy).not.toHaveBeenCalled();
    expect(result.current).toEqual({});
  });

  it("asks once the route is filled, with the route fields only, after a pause", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(api, "customsRoute").mockResolvedValue({ verdicts: { ens_mrn: entering } });
    const values = { consignor_name: "Verzender BV", loading_point: "New York (USNYC), NY, US", discharge_point: "Rotterdam (NLRTM), ZH, NL" };
    const { result } = renderHook(() => useCustomsRoute(values));
    expect(spy).not.toHaveBeenCalled();
    await act(async () => {
      vi.advanceTimersByTime(400);
    });
    expect(spy).toHaveBeenCalledWith({ loading_point: values.loading_point, discharge_point: values.discharge_point });
    vi.useRealTimers();
    await waitFor(() => expect(result.current.ens_mrn).toEqual(entering));
  });

  it("keeps a failed request away from the form", async () => {
    vi.useFakeTimers();
    vi.spyOn(api, "customsRoute").mockRejectedValue(new Error("down"));
    const { result } = renderHook(() => useCustomsRoute({ loading_point: "somewhere" }));
    await act(async () => {
      vi.advanceTimersByTime(400);
    });
    vi.useRealTimers();
    await waitFor(() => expect(result.current).toEqual({}));
  });
});
