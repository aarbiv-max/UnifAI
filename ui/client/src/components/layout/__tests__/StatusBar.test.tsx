import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import StatusBar from "../StatusBar";
import { render } from "@/test-utils/render";

describe("StatusBar", () => {
  it("renders system status and API version", () => {
    render(<StatusBar />);

    expect(screen.getByText("System active")).toBeInTheDocument();
    expect(screen.getByText("API v2.4.1")).toBeInTheDocument();
  });
});

