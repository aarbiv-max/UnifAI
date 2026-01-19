import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfirmDialog } from "../ConfirmDialog";
import { render } from "@/test-utils/render";

describe("ConfirmDialog", () => {
  it("renders content and handles actions", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onCancel = vi.fn();

    render(
      <ConfirmDialog
        open
        title="Delete item"
        message="This action cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Keep"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );

    expect(screen.getByText("Delete item")).toBeInTheDocument();
    expect(screen.getByText("This action cannot be undone.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Keep" }));
    expect(onCancel).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("shows loading state", () => {
    render(
      <ConfirmDialog
        open
        title="Processing"
        message="Please wait"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        loading
      />,
    );

    expect(screen.getByRole("button", { name: "Processing..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
  });
});

