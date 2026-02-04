import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import { AgentCardVisualization } from "../../workspace/AgentCardVisualization";

// Mock data
const mockAgentCard = {
  name: "Test Agent",
  version: "1.0.0",
  description: "A test agent for unit testing",
  skills: [
    {
      id: "skill-1",
      name: "TestSkill",
      description: "A test skill",
      tags: ["test", "mock", "example"],
      examples: ["Example 1", "Example 2"],
      input_modes: ["text", "json"],
      output_modes: ["text", "html"],
      security: [{ auth: ["oauth2"] }],
    },
    {
      id: "skill-2",
      name: "AnotherSkill",
      description: "Another skill for testing",
      tags: ["another"],
      examples: null,
      input_modes: null,
      output_modes: null,
      security: null,
    },
  ],
};

const mockAgentCardNoSkills = {
  name: "Simple Agent",
  version: "2.0.0",
  description: "An agent without skills",
  skills: [],
};

const mockAgentCardMinimal = {
  name: "Minimal Agent",
  version: "0.1.0",
};

describe("AgentCardVisualization", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading state", () => {
    it("shows spinner and 'Loading agent card...' message when isLoading is true", () => {
      render(<AgentCardVisualization agentCard={null} isLoading={true} />);

      expect(screen.getByText("Loading agent card...")).toBeInTheDocument();
      // Check for spinner element (animate-spin class)
      const spinner = document.querySelector(".animate-spin");
      expect(spinner).toBeInTheDocument();
    });

    it("uses gradient background for loading card", () => {
      const { container } = render(
        <AgentCardVisualization agentCard={null} isLoading={true} />
      );

      const card = container.querySelector('[class*="bg-gradient-to-br"]');
      expect(card).toBeInTheDocument();
      expect(card).toHaveClass("from-blue-950/30");
      expect(card).toHaveClass("to-purple-950/30");
    });
  });

  describe("No agent card state", () => {
    it("shows Info icon and 'No agent card available' when agentCard is null", () => {
      render(<AgentCardVisualization agentCard={null} isLoading={false} />);

      expect(screen.getByText("No agent card available.")).toBeInTheDocument();
    });

    it("uses appropriate background styling for empty state", () => {
      const { container } = render(
        <AgentCardVisualization agentCard={null} isLoading={false} />
      );

      const card = container.querySelector('[class*="bg-background-dark"]');
      expect(card).toBeInTheDocument();
    });
  });

  describe("Agent header display", () => {
    it("displays agent name prominently", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      expect(screen.getByText("Test Agent")).toBeInTheDocument();
    });

    it("shows version badge with 'v' prefix", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      expect(screen.getByText("v1.0.0")).toBeInTheDocument();
    });

    it("shows green checkmark icon", () => {
      const { container } = render(
        <AgentCardVisualization agentCard={mockAgentCard} />
      );

      // CheckCircle2 icon should have text-green-400 class
      const checkIcon = container.querySelector(".text-green-400");
      expect(checkIcon).toBeInTheDocument();
    });

    it("shows 'A2A Agent Node' subtitle", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      expect(screen.getByText("A2A Agent Node")).toBeInTheDocument();
    });

    it("displays description text", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      expect(
        screen.getByText("A test agent for unit testing")
      ).toBeInTheDocument();
    });

    it("shows skill count indicator", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      expect(screen.getByText("2 skills available")).toBeInTheDocument();
    });

    it("shows singular 'skill' when only one skill", () => {
      const singleSkillCard = {
        ...mockAgentCard,
        skills: [mockAgentCard.skills[0]],
      };
      render(<AgentCardVisualization agentCard={singleSkillCard} />);

      expect(screen.getByText("1 skill available")).toBeInTheDocument();
    });

    it("does not show description when not provided", () => {
      render(<AgentCardVisualization agentCard={mockAgentCardMinimal} />);

      expect(
        screen.queryByText("A test agent for unit testing")
      ).not.toBeInTheDocument();
    });
  });

  describe("Skills section", () => {
    it("renders 'Available Skills' heading with icon", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      expect(screen.getByText("Available Skills")).toBeInTheDocument();
    });

    it("shows skill cards for each skill", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      expect(screen.getByText("TestSkill")).toBeInTheDocument();
      expect(screen.getByText("AnotherSkill")).toBeInTheDocument();
    });

    it("each skill card shows index badge", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      expect(screen.getByText("#1")).toBeInTheDocument();
      expect(screen.getByText("#2")).toBeInTheDocument();
    });

    it("each skill card shows name", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      expect(screen.getByText("TestSkill")).toBeInTheDocument();
      expect(screen.getByText("AnotherSkill")).toBeInTheDocument();
    });

    it("each skill card shows description", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      expect(screen.getByText("A test skill")).toBeInTheDocument();
      expect(
        screen.getByText("Another skill for testing")
      ).toBeInTheDocument();
    });

    it("each skill card shows tags", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      expect(screen.getByText("test")).toBeInTheDocument();
      expect(screen.getByText("mock")).toBeInTheDocument();
      expect(screen.getByText("example")).toBeInTheDocument();
      expect(screen.getByText("another")).toBeInTheDocument();
    });

    it("shows skill ID in subtle text", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      expect(screen.getByText("ID: skill-1")).toBeInTheDocument();
      expect(screen.getByText("ID: skill-2")).toBeInTheDocument();
    });

    it("does not render skills section when no skills", () => {
      render(<AgentCardVisualization agentCard={mockAgentCardNoSkills} />);

      expect(screen.queryByText("Available Skills")).not.toBeInTheDocument();
    });
  });

  describe("Skill card expansion", () => {
    it("'View Details' button shown when additional info exists", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      // First skill has additional info
      expect(screen.getByText("View Details")).toBeInTheDocument();
    });

    it("'View Details' button not shown when no additional info", () => {
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      // Should only have one "View Details" button (for skill-1)
      const viewDetailsButtons = screen.getAllByText("View Details");
      expect(viewDetailsButtons).toHaveLength(1);
    });

    it("toggles expanded state on click", async () => {
      const user = userEvent.setup();
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      const viewDetailsButton = screen.getByText("View Details");
      await user.click(viewDetailsButton);

      // After clicking, should show "Hide Details"
      expect(screen.getByText("Hide Details")).toBeInTheDocument();

      // Click again to collapse
      await user.click(screen.getByText("Hide Details"));
      expect(screen.getByText("View Details")).toBeInTheDocument();
    });

    it("shows examples with quote styling when expanded", async () => {
      const user = userEvent.setup();
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      await user.click(screen.getByText("View Details"));

      expect(screen.getByText('"Example 1"')).toBeInTheDocument();
      expect(screen.getByText('"Example 2"')).toBeInTheDocument();
    });

    it("shows input modes badges (green) when expanded", async () => {
      const user = userEvent.setup();
      const { container } = render(
        <AgentCardVisualization agentCard={mockAgentCard} />
      );

      await user.click(screen.getByText("View Details"));

      // "text" appears in both input and output modes, so we check for presence of multiple
      const textBadges = screen.getAllByText("text");
      expect(textBadges.length).toBeGreaterThan(0);
      expect(screen.getByText("json")).toBeInTheDocument();

      // Input modes should have green styling
      const greenBadges = container.querySelectorAll('[class*="text-green-300"]');
      expect(greenBadges.length).toBeGreaterThan(0);
    });

    it("shows output modes badges (orange) when expanded", async () => {
      const user = userEvent.setup();
      const { container } = render(
        <AgentCardVisualization agentCard={mockAgentCard} />
      );

      await user.click(screen.getByText("View Details"));

      expect(screen.getByText("html")).toBeInTheDocument();

      // Output modes should have orange styling
      const orangeBadges = container.querySelectorAll(
        '[class*="text-orange-300"]'
      );
      expect(orangeBadges.length).toBeGreaterThan(0);
    });

    it("shows security requirements as JSON when expanded", async () => {
      const user = userEvent.setup();
      render(<AgentCardVisualization agentCard={mockAgentCard} />);

      await user.click(screen.getByText("View Details"));

      expect(screen.getByText("Security Requirements")).toBeInTheDocument();
      // Check for JSON content
      expect(screen.getByText(/"auth"/)).toBeInTheDocument();
    });
  });
});
