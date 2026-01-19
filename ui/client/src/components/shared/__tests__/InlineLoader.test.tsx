import { describe, it, expect } from "vitest";
import { render } from "@/test-utils/render";
import { InlineLoader } from "../InlineLoader";

describe("InlineLoader", () => {
  it("renders a spinner element", () => {
    const { container } = render(<InlineLoader />);
    expect(container.querySelector("div")).toBeInTheDocument();
  });
});

