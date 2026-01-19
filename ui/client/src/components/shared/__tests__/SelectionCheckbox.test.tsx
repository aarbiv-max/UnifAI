import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SelectionCheckbox } from "../SelectionCheckbox";
import { render } from "@/test-utils/render";

describe("SelectionCheckbox", () => {
  it("calls onCheckedChange when toggled", async () => {
    const user = userEvent.setup();
    const onCheckedChange = vi.fn();

    render(
      <SelectionCheckbox checked={false} onCheckedChange={onCheckedChange} />,
    );

    await user.click(screen.getByRole("checkbox"));
    expect(onCheckedChange).toHaveBeenCalledWith(true);
  });
});

