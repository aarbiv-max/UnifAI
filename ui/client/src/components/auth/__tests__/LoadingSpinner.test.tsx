import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import LoadingSpinner from "../LoadingSpinner";
import { render } from "@/test-utils/render";

describe("LoadingSpinner", () => {
  it("renders default message", () => {
    render(<LoadingSpinner />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders custom message", () => {
    render(<LoadingSpinner message="Working..." />);
    expect(screen.getByText("Working...")).toBeInTheDocument();
  });
});

