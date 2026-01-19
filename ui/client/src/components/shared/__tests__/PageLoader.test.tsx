import { describe, it, expect } from "vitest";
import { render } from "@/test-utils/render";
import { PageLoader } from "../PageLoader";

describe("PageLoader", () => {
  it("renders a loading spinner container", () => {
    const { container } = render(<PageLoader />);
    expect(container.querySelector("div")).toBeInTheDocument();
  });
});

