import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import WorkflowStatusBanner, { WorkflowBannerMessages } from "../WorkflowStatusBanner";
import { render } from "@/test-utils/render";

describe("WorkflowStatusBanner", () => {
  it("renders the provided message and title", () => {
    render(
      <WorkflowStatusBanner
        variant="info"
        title="Heads up"
        message="Something happened"
      />,
    );

    expect(screen.getByText("Heads up: Something happened")).toBeInTheDocument();
  });

  it("renders predefined banner message", () => {
    const message = WorkflowBannerMessages.validating;
    render(
      <WorkflowStatusBanner
        variant={message.variant}
        title={message.title}
        message={message.message}
      />,
    );

    expect(screen.getByText("Validating workflow...")).toBeInTheDocument();
  });
});

