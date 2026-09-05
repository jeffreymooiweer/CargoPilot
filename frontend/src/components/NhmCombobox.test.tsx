/**
 * The NHM box: a code typed stays a code, a code picked becomes the value,
 * and a six-digit value is read back in words.
 */
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import NhmCombobox from "./NhmCombobox";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }),
}));

const steel = {
  code: "720851",
  en: "Flat-rolled products of iron or non-alloy steel, hot-rolled, > 10 mm",
  fr: "Produits laminés plats, en fer ou en aciers non alliés",
  nst: "10.1",
};

afterEach(() => vi.restoreAllMocks());

describe("NhmCombobox", () => {
  it("lists what the search answers and puts the picked code in the box", async () => {
    const search = vi.spyOn(api, "nhmSearch").mockResolvedValue({ results: [steel], count: 5640 });
    vi.spyOn(api, "nhmLookup").mockResolvedValue(steel);
    const onChange = vi.fn();
    render(<NhmCombobox value="" onChange={onChange} />);
    await userEvent.type(screen.getByRole("textbox"), "7208");
    await waitFor(() => expect(search).toHaveBeenCalledWith("7208"));
    await userEvent.click(await screen.findByRole("option"));
    expect(onChange).toHaveBeenLastCalledWith("720851");
  });

  it("reads a six-digit value back in words", async () => {
    vi.spyOn(api, "nhmLookup").mockResolvedValue(steel);
    render(<NhmCombobox value="720851" onChange={vi.fn()} />);
    await waitFor(() => expect(screen.getByTestId("nhm-label")).toHaveTextContent("Flat-rolled products"));
  });

  it("asks for no words while the value is not a code", async () => {
    const lookup = vi.spyOn(api, "nhmLookup");
    render(<NhmCombobox value="7208" onChange={vi.fn()} />);
    await act(async () => {});
    expect(lookup).not.toHaveBeenCalled();
    expect(screen.queryByTestId("nhm-label")).toBeNull();
  });
});
