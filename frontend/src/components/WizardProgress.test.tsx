/**
 * The progress bar, and what it is allowed to be a way back to.
 *
 * It was informative only: it said where you were and offered nothing, so the
 * only way to an earlier step was pressing Back once per step and forward
 * again afterwards — which the baseline measured as four step changes to
 * correct one field. A step somebody has already been on can be gone back to
 * from here.
 *
 * The restraint is the point of the test: the step you are on is not a link to
 * itself, and a step nobody has reached is not offered at all. Offering it
 * would be a way to skip the steps in between, and there is nothing on it to
 * go back *to*.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import WizardProgress from "./WizardProgress";

const STEPS = [
  { n: 1, key: "lines" as const, label: "Goederen" },
  { n: 2, key: "details" as const, label: "Zendinggegevens" },
  { n: 3, key: "export" as const, label: "Export" },
];

describe("going back from the progress bar", () => {
  it("a visited step is something you can press", async () => {
    const onGoTo = vi.fn();
    render(
      <WizardProgress steps={STEPS} currentStep={3} visited={["lines", "details", "export"]} onGoTo={onGoTo} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Goederen" }));
    expect(onGoTo).toHaveBeenCalledWith("lines");
  });

  it("the step you are on is not a link to itself", () => {
    render(
      <WizardProgress steps={STEPS} currentStep={3} visited={["lines", "details", "export"]} onGoTo={vi.fn()} />,
    );
    expect(screen.queryByRole("button", { name: "Export" })).toBeNull();
  });

  it("a step nobody has reached is not offered", () => {
    render(<WizardProgress steps={STEPS} currentStep={1} visited={["lines"]} onGoTo={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Zendinggegevens" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Export" })).toBeNull();
  });

  it("without a handler it stays what it was: a picture of where you are", () => {
    render(<WizardProgress steps={STEPS} currentStep={2} visited={["lines", "details"]} />);
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getByLabelText("Goederen")).toBeInTheDocument();
  });

  it("says which step is the current one", () => {
    render(<WizardProgress steps={STEPS} currentStep={2} visited={["lines", "details"]} onGoTo={vi.fn()} />);
    const current = document.querySelector("[aria-current=step]");
    expect(current).toHaveTextContent("Zendinggegevens");
  });
});
