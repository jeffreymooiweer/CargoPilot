/**
 * The paste box fills only what is still empty, and says what it did.
 *
 * The server reads formats; this component decides placement. The one rule
 * that must never break: a value the user already typed is never overwritten
 * by whatever the confirmation e-mail happens to contain.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import CarrierConfirmationBox from "./CarrierConfirmationBox";
import { api } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options?.fields ? `${key} ${options.fields}` : key,
    i18n: { language: "nl" },
  }),
}));

afterEach(() => vi.restoreAllMocks());

async function openAndRead(text = "AWB 057-12345675") {
  await userEvent.click(screen.getByRole("button", { name: /carrier.title/ }));
  await userEvent.type(screen.getByPlaceholderText("carrier.placeholder"), text);
  await userEvent.click(screen.getByRole("button", { name: "carrier.read" }));
}

describe("CarrierConfirmationBox", () => {
  it("fills the empty fields with what was found", async () => {
    vi.spyOn(api, "parseCarrierConfirmation").mockResolvedValue({
      found: { awb_number: "057-12345675", booking_number: "BK12345" },
    });
    const onChange = vi.fn();
    render(<CarrierConfirmationBox values={{}} onChange={onChange} />);
    await openAndRead();
    await waitFor(() =>
      expect(onChange).toHaveBeenCalledWith({
        awb_number: "057-12345675",
        booking_number: "BK12345",
      }),
    );
    expect(screen.getByText(/carrier.filled/)).toBeInTheDocument();
  });

  it("never overwrites what the user already typed", async () => {
    vi.spyOn(api, "parseCarrierConfirmation").mockResolvedValue({
      found: { awb_number: "057-12345675", booking_number: "BK12345" },
    });
    const onChange = vi.fn();
    render(
      <CarrierConfirmationBox values={{ awb_number: "999-00000000" }} onChange={onChange} />,
    );
    await openAndRead();
    await waitFor(() => expect(onChange).toHaveBeenCalled());
    const next = onChange.mock.calls[0][0];
    expect(next.awb_number).toBe("999-00000000");
    expect(next.booking_number).toBe("BK12345");
    expect(screen.getByText(/carrier.kept/)).toBeInTheDocument();
  });

  it("says so when nothing recognisable was found", async () => {
    vi.spyOn(api, "parseCarrierConfirmation").mockResolvedValue({ found: {} });
    const onChange = vi.fn();
    render(<CarrierConfirmationBox values={{}} onChange={onChange} />);
    await openAndRead("thanks for your business");
    expect(await screen.findByText("carrier.foundNone")).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });
});
