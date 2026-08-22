/**
 * Clicking a number field hands you the number.
 *
 * A field with a 1 in it used to put the caret beside the 1 and leave it: to
 * enter 12 you typed your number and then went back to delete the 1. Every
 * field, every time. What is pinned here is the selection on focus, and the
 * two ways that could go wrong: cancelling the click that would otherwise undo
 * the selection, and *not* cancelling any later click, so someone who wants to
 * edit one digit still can.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import NumberInput from "./NumberInput";

function renderInput(props: Record<string, unknown> = {}) {
  render(<NumberInput aria-label="amount" defaultValue={1} {...props} />);
  const input = screen.getByLabelText("amount") as HTMLInputElement;
  const select = vi.spyOn(input, "select");
  return { input, select };
}

describe("NumberInput", () => {
  it("is a number field", () => {
    const { input } = renderInput();
    expect(input).toHaveAttribute("type", "number");
  });

  it("selects what is in it as soon as it takes focus", () => {
    const { input, select } = renderInput();
    fireEvent.focus(input);
    expect(select).toHaveBeenCalledTimes(1);
  });

  it("cancels the click that would put the caret back", () => {
    const { input } = renderInput();
    fireEvent.mouseDown(input);
    fireEvent.focus(input);
    const prevented = !fireEvent.mouseUp(input);
    expect(prevented).toBe(true);
  });

  it("leaves a second click alone, so one digit can still be edited", () => {
    const { input } = renderInput();
    fireEvent.mouseDown(input);
    fireEvent.focus(input);
    fireEvent.mouseUp(input);
    // Already focused: no focus event this time, and the caret may be placed.
    const prevented = !fireEvent.mouseUp(input);
    expect(prevented).toBe(false);
  });

  it("does not cancel a click after focusing by keyboard", () => {
    const { input } = renderInput();
    fireEvent.focus(input); // Tab, no mouse
    const prevented = !fireEvent.mouseUp(input);
    expect(prevented).toBe(false);
  });

  it("still calls the handlers it was given", () => {
    const onFocus = vi.fn();
    const onChange = vi.fn();
    const { input } = renderInput({ onFocus, onChange });
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "12" } });
    expect(onFocus).toHaveBeenCalled();
    expect(onChange).toHaveBeenCalled();
  });
});
