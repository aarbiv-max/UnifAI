import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Pagination } from "../Pagination";
import { render } from "@/test-utils/render";

describe("Pagination", () => {
  it("renders page information and item range", () => {
    render(
      <Pagination
        pageIndex={0}
        pageCount={5}
        pageSize={10}
        totalItems={45}
        onPreviousPage={vi.fn()}
        onNextPage={vi.fn()}
        canPreviousPage={false}
        canNextPage={true}
        itemName="rows"
      />,
    );

    const info = screen.getByText((_, element) => {
      if (!element || element.tagName !== "SPAN") {
        return false;
      }
      const text = element.textContent ?? "";
      return (
        text.includes("Page 1 of 5") && text.includes("rows 1-10 out of 45")
      );
    });
    expect(info).toBeInTheDocument();
  });

  it("invokes callbacks and respects disabled states", async () => {
    const user = userEvent.setup();
    const onPreviousPage = vi.fn();
    const onNextPage = vi.fn();

    render(
      <Pagination
        pageIndex={1}
        pageCount={3}
        pageSize={10}
        totalItems={30}
        onPreviousPage={onPreviousPage}
        onNextPage={onNextPage}
        canPreviousPage={false}
        canNextPage={true}
      />,
    );

    const prevButton = screen.getByRole("button", { name: "Previous" });
    const nextButton = screen.getByRole("button", { name: "Next" });

    expect(prevButton).toBeDisabled();
    await user.click(nextButton);
    expect(onNextPage).toHaveBeenCalledTimes(1);
    expect(onPreviousPage).not.toHaveBeenCalled();
  });
});

