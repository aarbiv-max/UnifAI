import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import ProjectCard from "../ProjectCard";
import { render } from "@/test-utils/render";

describe("ProjectCard", () => {
  it("renders project details", () => {
    render(
      <ProjectCard
        name="My Project"
        shortName="MP"
        icon="project"
        updatedTime="yesterday"
        processingPercentage={75}
        color="primary"
        isActive
        sources={3}
        documents={12}
      />,
    );

    expect(screen.getByText("My Project")).toBeInTheDocument();
    expect(screen.getByText("Updated yesterday")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("3 Sources")).toBeInTheDocument();
    expect(screen.getByText("12k Documents")).toBeInTheDocument();
  });
});

