/**
 * The description box keeps a copy of what you typed, and that copy has to come
 * back from the parent.
 *
 * The box holds the text in its own state while you type — it needs it for the
 * catalogue search — and until v1.54.0 it never looked at the `value` prop
 * again after the first render. With one box on screen that is invisible: the
 * parent's value and the local copy are updated on the same keystroke and never
 * disagree.
 *
 * The detail panel put a *second* box on the same line. Type in one and the
 * other still showed the old text; touch the stale one and it wrote that old
 * text back over what you had just entered. So this is not a tidiness fix — it
 * is a line that silently reverts.
 */
import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import EquipmentCombobox from "./EquipmentCombobox";
import { api } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "nl" },
  }),
}));

beforeEach(() => {
  vi.spyOn(api, "listEquipment").mockResolvedValue([]);
  vi.spyOn(api, "catalogSearch").mockResolvedValue({ results: [] });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("de omschrijvingsbox", () => {
  it("volgt een waarde die van buitenaf verandert", () => {
    const { rerender } = render(<EquipmentCombobox value="Balk" onChange={() => {}} />);
    expect(screen.getByRole("textbox")).toHaveValue("Balk");

    // The parent changed it — because the same line was edited in the detail
    // panel, or because a line was duplicated onto this row.
    rerender(<EquipmentCombobox value="Buis" onChange={() => {}} />);
    expect(screen.getByRole("textbox")).toHaveValue("Buis");
  });

  it("laat typen ongemoeid", async () => {
    // The regression a naive sync would cause: the parent echoes every
    // keystroke back, and a box that resets on every echo cannot be typed in.
    function Controlled() {
      const [value, setValue] = useState("");
      return <EquipmentCombobox value={value} onChange={(next) => setValue(next)} />;
    }
    render(<Controlled />);

    await userEvent.type(screen.getByRole("textbox"), "Stalen balk");
    expect(screen.getByRole("textbox")).toHaveValue("Stalen balk");
  });
});
