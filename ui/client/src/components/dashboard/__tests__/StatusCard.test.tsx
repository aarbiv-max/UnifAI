import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import StatusCard from "../StatusCard";
import { render } from "@/test-utils/render";

describe("StatusCard", () => {
  it("renders title, value, and status items", () => {
    render(
      <StatusCard
        title="Jobs"
        value="42"
        icon={<span>+</span>}
        iconBgColor="bg-blue-500"
        statusItems={[
          { label: "Active", value: "10", color: "green-500" },
        ]}
      />,
    );

    expect(screen.getByText("Jobs")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
  });
});

