/**
 * A number field that hands you the whole number when you click it.
 *
 * A plain `<input type="number">` with a 1 in it puts the caret next to the 1
 * and leaves it there. To enter 12 you first type your number and *then* go
 * back to delete the 1 — every field, every time. Selecting the value on focus
 * makes the first keystroke replace it, which is what typing into a field that
 * already has a value almost always means.
 *
 * Why the mouse guard: with a click, the browser places the caret as the
 * default action of the click, and that would undo the selection made on
 * focus. Cancelling the mouse-up of *that one* click keeps the selection. The
 * flag is set on mouse-down and cleared as soon as it is used, so a second
 * click inside the field still places the caret normally — a user who wants to
 * edit one digit can, and drag-selecting still works. Keyboard focus (Tab)
 * never sets the flag, so nothing is cancelled there.
 *
 * `select()` rather than `setSelectionRange()` deliberately: Chrome throws on
 * the selection API for `type="number"`, but `select()` is supported.
 */
import { forwardRef, useRef, type InputHTMLAttributes } from "react";

const NumberInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function NumberInput({ onFocus, onMouseDown, onMouseUp, onBlur, ...rest }, ref) {
    const fromMouse = useRef(false);
    return (
      <input
        ref={ref}
        type="number"
        onMouseDown={(event) => {
          fromMouse.current = true;
          onMouseDown?.(event);
        }}
        onFocus={(event) => {
          event.currentTarget.select();
          onFocus?.(event);
        }}
        onMouseUp={(event) => {
          if (fromMouse.current) {
            fromMouse.current = false;
            event.preventDefault();
          }
          onMouseUp?.(event);
        }}
        onBlur={(event) => {
          fromMouse.current = false;
          onBlur?.(event);
        }}
        {...rest}
      />
    );
  },
);

export default NumberInput;
