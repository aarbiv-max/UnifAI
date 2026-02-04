import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import { CategorySidebar } from "../../workspace/CategorySidebar";
import { ElementCategory, ElementType } from "../../../../types/workspace";

// Mock data
const mockElementType1: ElementType = {
  category: "nodes",
  name: "ReactAgent",
  type: "react_agent",
};

const mockElementType2: ElementType = {
  category: "nodes",
  name: "ToolAgent",
  type: "tool_agent",
};

const mockElementType3: ElementType = {
  category: "llms",
  name: "OpenAI",
  type: "openai",
};

const mockElementType4: ElementType = {
  category: "tools",
  name: "SearchTool",
  type: "search_tool",
};

const mockElementType5: ElementType = {
  category: "retrievers",
  name: "VectorRetriever",
  type: "vector_retriever",
};

const mockElementType6: ElementType = {
  category: "providers",
  name: "APIProvider",
  type: "api_provider",
};

const mockElementType7: ElementType = {
  category: "conditions",
  name: "IfCondition",
  type: "if_condition",
};

const mockCategories: ElementCategory[] = [
  {
    category: "nodes",
    elements: [mockElementType1, mockElementType2],
  },
  {
    category: "llms",
    elements: [mockElementType3],
  },
  {
    category: "tools",
    elements: [mockElementType4],
  },
  {
    category: "retrievers",
    elements: [mockElementType5],
  },
  {
    category: "providers",
    elements: [mockElementType6],
  },
  {
    category: "conditions",
    elements: [mockElementType7],
  },
];

describe("CategorySidebar", () => {
  const defaultProps = {
    categories: mockCategories,
    selectedCategory: null,
    selectedElementType: null,
    onElementTypeSelect: vi.fn(),
    isLoading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering categories", () => {
    it("renders list of categories from props", () => {
      render(<CategorySidebar {...defaultProps} />);

      // Check display names are rendered
      expect(screen.getByText(/Agents/)).toBeInTheDocument();
      expect(screen.getByText(/LLMs/)).toBeInTheDocument();
      expect(screen.getByText(/Tools/)).toBeInTheDocument();
      expect(screen.getByText(/Retrievers/)).toBeInTheDocument();
      expect(screen.getByText(/Providers/)).toBeInTheDocument();
      expect(screen.getByText(/Conditions/)).toBeInTheDocument();
    });

    it("shows correct icon for nodes category (Bot)", () => {
      const { container } = render(<CategorySidebar {...defaultProps} />);

      // Bot icon should be present
      const botIcons = container.querySelectorAll(".lucide-bot");
      expect(botIcons.length).toBeGreaterThan(0);
    });

    it("shows correct icon for llms category (Brain)", () => {
      const { container } = render(<CategorySidebar {...defaultProps} />);

      const brainIcons = container.querySelectorAll(".lucide-brain");
      expect(brainIcons.length).toBeGreaterThan(0);
    });

    it("shows correct icon for tools category (Wrench)", () => {
      const { container } = render(<CategorySidebar {...defaultProps} />);

      const wrenchIcons = container.querySelectorAll(".lucide-wrench");
      expect(wrenchIcons.length).toBeGreaterThan(0);
    });

    it("shows correct icon for retrievers category (Search)", () => {
      const { container } = render(<CategorySidebar {...defaultProps} />);

      const searchIcons = container.querySelectorAll(".lucide-search");
      expect(searchIcons.length).toBeGreaterThan(0);
    });

    it("shows correct icon for providers category (Server)", () => {
      const { container } = render(<CategorySidebar {...defaultProps} />);

      const serverIcons = container.querySelectorAll(".lucide-server");
      expect(serverIcons.length).toBeGreaterThan(0);
    });

    it("shows correct icon for conditions category (GitBranch)", () => {
      const { container } = render(<CategorySidebar {...defaultProps} />);

      const gitBranchIcons = container.querySelectorAll(".lucide-git-branch");
      expect(gitBranchIcons.length).toBeGreaterThan(0);
    });

    it("shows category count '(X)' next to name", () => {
      render(<CategorySidebar {...defaultProps} />);

      // nodes has 2 elements
      expect(screen.getByText(/Agents \(2\)/)).toBeInTheDocument();
      // llms has 1 element
      expect(screen.getByText(/LLMs \(1\)/)).toBeInTheDocument();
    });
  });

  describe("Loading state", () => {
    it("shows loading spinner when isLoading and no categories", () => {
      const { container } = render(
        <CategorySidebar
          {...defaultProps}
          isLoading={true}
          categories={[]}
        />
      );

      const spinner = container.querySelector(".animate-spin");
      expect(spinner).toBeInTheDocument();
    });

    it("does not show loading spinner when isLoading but has categories", () => {
      const { container } = render(
        <CategorySidebar {...defaultProps} isLoading={true} />
      );

      // Should show categories, not loading
      expect(screen.getByText(/Agents/)).toBeInTheDocument();
    });
  });

  describe("Category expansion", () => {
    it("toggles category expansion on header click", async () => {
      const user = userEvent.setup();
      render(<CategorySidebar {...defaultProps} />);

      // Initially element types should not be visible
      expect(screen.queryByText("ReactAgent")).not.toBeInTheDocument();

      // Click to expand
      const agentsButton = screen.getByText(/Agents \(2\)/);
      await user.click(agentsButton);

      // Element types should now be visible
      expect(screen.getByText("ReactAgent")).toBeInTheDocument();
      expect(screen.getByText("ToolAgent")).toBeInTheDocument();
    });

    it("shows ChevronDown when expanded", async () => {
      const user = userEvent.setup();
      const { container } = render(<CategorySidebar {...defaultProps} />);

      const agentsButton = screen.getByText(/Agents \(2\)/);
      await user.click(agentsButton);

      const chevronDown = container.querySelector(".lucide-chevron-down");
      expect(chevronDown).toBeInTheDocument();
    });

    it("shows ChevronRight when collapsed", () => {
      const { container } = render(<CategorySidebar {...defaultProps} />);

      const chevronRight = container.querySelector(".lucide-chevron-right");
      expect(chevronRight).toBeInTheDocument();
    });

    it("stores expanded categories in state", async () => {
      const user = userEvent.setup();
      render(<CategorySidebar {...defaultProps} />);

      // Expand both nodes and llms
      await user.click(screen.getByText(/Agents \(2\)/));
      await user.click(screen.getByText(/LLMs \(1\)/));

      // Both should be expanded
      expect(screen.getByText("ReactAgent")).toBeInTheDocument();
      expect(screen.getByText("OpenAI")).toBeInTheDocument();

      // Click nodes again to collapse
      await user.click(screen.getByText(/Agents \(2\)/));

      // Nodes should be collapsed, llms still expanded
      expect(screen.queryByText("ReactAgent")).not.toBeInTheDocument();
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
    });
  });

  describe("Element type display", () => {
    it("shows element types indented under category when expanded", async () => {
      const user = userEvent.setup();
      const { container } = render(<CategorySidebar {...defaultProps} />);

      await user.click(screen.getByText(/Agents \(2\)/));

      // Check for indented container with border-l
      const indentedContainer = container.querySelector(".ml-4.border-l");
      expect(indentedContainer).toBeInTheDocument();
    });

    it("highlights selected element type with primary color", async () => {
      const user = userEvent.setup();
      render(
        <CategorySidebar
          {...defaultProps}
          selectedElementType={mockElementType1}
        />
      );

      await user.click(screen.getByText(/Agents \(2\)/));

      const selectedButton = screen.getByText("ReactAgent").closest("button");
      expect(selectedButton).toHaveClass("bg-primary");
    });

    it("calls onElementTypeSelect with (category, elementType) on click", async () => {
      const user = userEvent.setup();
      const onElementTypeSelect = vi.fn();
      render(
        <CategorySidebar
          {...defaultProps}
          onElementTypeSelect={onElementTypeSelect}
        />
      );

      await user.click(screen.getByText(/Agents \(2\)/));
      await user.click(screen.getByText("ReactAgent"));

      expect(onElementTypeSelect).toHaveBeenCalledWith("nodes", mockElementType1);
    });

    it("shows dot indicator before element type name", async () => {
      const user = userEvent.setup();
      const { container } = render(<CategorySidebar {...defaultProps} />);

      await user.click(screen.getByText(/Agents \(2\)/));

      // Look for dot indicator (rounded-full bg-gray-500)
      const dots = container.querySelectorAll(".rounded-full.bg-gray-500");
      expect(dots.length).toBeGreaterThan(0);
    });
  });

  describe("Unknown category handling", () => {
    it("uses fallback icon for unknown category", () => {
      const unknownCategory: ElementCategory = {
        category: "unknown",
        elements: [{ category: "unknown", name: "Unknown", type: "unknown" }],
      };

      const { container } = render(
        <CategorySidebar
          {...defaultProps}
          categories={[unknownCategory]}
        />
      );

      // Layers icon is the fallback
      const layersIcon = container.querySelector(".lucide-layers");
      expect(layersIcon).toBeInTheDocument();
    });

    it("capitalizes unknown category name", () => {
      const unknownCategory: ElementCategory = {
        category: "custom",
        elements: [{ category: "custom", name: "CustomElement", type: "custom" }],
      };

      render(
        <CategorySidebar
          {...defaultProps}
          categories={[unknownCategory]}
        />
      );

      expect(screen.getByText(/Custom \(1\)/)).toBeInTheDocument();
    });
  });
});
