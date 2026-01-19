import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { StatusBadge } from "../StatusBadge";
import { render } from "@/test-utils/render";

describe("StatusBadge", () => {
  it("renders pending when status is undefined", () => {
    render(<StatusBadge status={undefined} />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("renders active label for ACTIVE status", () => {
    render(<StatusBadge status="ACTIVE" />);
    expect(screen.getByText("In Progress")).toBeInTheDocument();
  });
});

