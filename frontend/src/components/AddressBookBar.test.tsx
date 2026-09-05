/**
 * The address book on the details step: picking fills the party's fields,
 * saving puts what is there into the book, and the carrier's one field is
 * split and joined at its first line.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AddressBookBar, { PARTIES, entryFrom, fillFrom } from "./AddressBookBar";
import { ToastProvider } from "../toast/ToastProvider";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options?.party ? `${key}:${options.party}` : options?.name ? `${key}:${options.name}` : key,
    i18n: { language: "nl" },
  }),
}));

const api = vi.hoisted(() => ({
  addresses: vi.fn(),
  saveAddress: vi.fn(),
}));
vi.mock("../api/client", () => ({ api }));

const book = [
  { id: 1, name: "Afzender BV", address: "Havenweg 1\n3000 AA Rotterdam", contact: "+31 10 000" },
  { id: 2, name: "Ontvanger GmbH", address: "Hafenstrasse 4\n47119 Duisburg", contact: "" },
];
const labels = { consignor: "Afzender", consignee: "Geadresseerde", carrier: "Vervoerder" };

beforeEach(() => {
  vi.clearAllMocks();
  api.addresses.mockResolvedValue(book);
  api.saveAddress.mockImplementation(async (entry: { name: string }) => ({ id: 3, address: "", contact: "", ...entry }));
});

function renderBar(values: Record<string, string>, onChange = vi.fn()) {
  render(
    <ToastProvider>
      <AddressBookBar values={values} onChange={onChange} labels={labels} />
    </ToastProvider>,
  );
  return onChange;
}

describe("het adresboek op de gegevensstap", () => {
  it("vult de velden van de gekozen partij", async () => {
    const onChange = renderBar({ consignor_name: "", shipment_reference: "CP-1" });
    const picker = await screen.findByLabelText("addressBook.pick:Geadresseerde");
    await waitFor(() => expect(picker).not.toBeDisabled());
    await userEvent.selectOptions(picker, "2");
    expect(onChange).toHaveBeenCalledWith({
      consignor_name: "",
      shipment_reference: "CP-1",
      consignee_name: "Ontvanger GmbH",
      consignee_address: "Hafenstrasse 4\n47119 Duisburg",
      consignee_contact: "",
    });
  });

  it("bewaart wat er staat onder de naam van de partij, en niet zonder naam", async () => {
    renderBar({ consignor_name: "Nieuw BV", consignor_address: "Straat 1", consignor_contact: "x@y", consignee_name: "  " });
    await screen.findByLabelText("addressBook.pick:Afzender");
    expect(screen.getByRole("button", { name: "addressBook.saveTitle:Geadresseerde" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "addressBook.saveTitle:Afzender" }));
    await waitFor(() =>
      expect(api.saveAddress).toHaveBeenCalledWith({ name: "Nieuw BV", address: "Straat 1", contact: "x@y" }),
    );
    // The new entry is in the picker straight away, in its place.
    const picker = screen.getByLabelText("addressBook.pick:Afzender") as HTMLSelectElement;
    await waitFor(() => expect(Array.from(picker.options).map((o) => o.text)).toContain("Nieuw BV"));
  });

  it("voegt voor de vervoerder naam en adres samen, en splitst ze weer", () => {
    const carrier = PARTIES[2];
    expect(fillFrom(carrier, book[0], {})).toEqual({ carrier_name: "Afzender BV\nHavenweg 1\n3000 AA Rotterdam" });
    expect(entryFrom(carrier, { carrier_name: "Trucks NV\nKade 9\nAntwerpen" })).toEqual({
      name: "Trucks NV", address: "Kade 9\nAntwerpen", contact: "",
    });
  });
});
