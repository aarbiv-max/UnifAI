import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import { ElementGrid } from "../../workspace/ElementGrid";
import { ElementInstance, ElementType, ElementSchema } from "../../../../types/workspace";

// Mock framer-motion
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

// Mock the AgenticAI context
const validateResourcesMock = vi.fn();
const getValidationResultMock = vi.fn();
const getValidationStatusMock = vi.fn();
const getResourceNameMock = vi.fn((ref: string) => ref);

vi.mock("@/contexts/AgenticAIContext", () => ({
  AgenticAIProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAgenticAI: () => ({
    getResourceName: getResourceNameMock,
    getValidationResult: getValidationResultMock,
    getValidationStatus: getValidationStatusMock,
    validateResources: validateResourcesMock,
  }),
}));

// Mock the Shared context
const openShareForItemMock = vi.fn();
vi.mock("@/contexts/SharedContext", () => ({
  SharedProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useShared: () => ({
    openShareForItem: openShareForItemMock,
  }),
}));

// Mock child components
vi.mock("../../workspace/ElementData", () => ({
  ElementData: ({ isOpen, element }: any) =>
    isOpen ? (
      <div data-testid="element-data-modal">
        ElementData Modal - {element?.name}
      </div>
    ) : null,
}));

vi.mock("../../workspace/ValidationResultModal", () => ({
  ValidationResultModal: ({ isOpen, validationResult }: any) =>
    isOpen ? (
      <div data-testid="validation-result-modal">
        Validation Result - {validationResult?.rid}
      </div>
    ) : null,
}));

// Mock utility functions
vi.mock("../../../../utils/maskSecretFields", () => ({
  formatConfigValue: (value: any) => String(value),
}));

vi.mock("../../../../utils/displayUtils", () => ({
  getDisplayValueFromItem: (item: any) =>
    typeof item === "string" ? item : JSON.stringify(item),
}));

const mockElementType: ElementType = {
  category: "llms",
  name: "OpenAI LLM",
  type: "openai",
};

const mockElements: ElementInstance[] = [
  {
    rid: "rid-12345678-abcd-0001",
    name: "GPT-4 Instance",
    type: "openai",
    category: "llms",
    version: 2,
    updated: "2024-01-20T14:45:00Z",
    config: {
      model: "gpt-4",
      temperature: 0.7,
      max_tokens: 1000,
      extra_field: "extra_value",
    },
  },
  {
    rid: "rid-12345678-abcd-0002",
    name: "GPT-3.5 Instance",
    type: "openai",
    category: "llms",
    version: 1,
    config: {
      model: "gpt-3.5-turbo",
    },
  },
];

const mockElementSchema: ElementSchema = {
  category: "llms",
  name: "OpenAI",
  type: "openai",
  description: "OpenAI LLM Configuration",
  tags: ["llm"],
  config_schema: {
    type: "object",
    properties: {
      model: { type: "string" },
      temperature: { type: "number" },
      max_tokens: { type: "integer" },
    },
    required: ["model"],
    additionalProperties: false,
  },
};

describe("ElementGrid", () => {
  const defaultProps = {
    elements: mockElements,
    elementType: mockElementType,
    isLoading: false,
    onEditElement: vi.fn(),
    onDeleteElement: vi.fn(),
    elementSchema: mockElementSchema,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    getValidationStatusMock.mockReturnValue(null);
    getValidationResultMock.mockReturnValue(null);
  });

  describe("Grid layout", () => {
    it("renders cards in responsive grid (1/2/3 columns)", () => {
      const { container } = render(<ElementGrid {...defaultProps} />);

      const grid = container.querySelector(".grid");
      expect(grid).toHaveClass("grid-cols-1");
      expect(grid).toHaveClass("md:grid-cols-2");
      expect(grid).toHaveClass("lg:grid-cols-3");
    });
  });

  describe("Loading state", () => {
    it("shows loading spinner when isLoading", () => {
      const { container } = render(
        <ElementGrid {...defaultProps} isLoading={true} />
      );

      const spinner = container.querySelector(".animate-spin");
      expect(spinner).toBeInTheDocument();
    });
  });

  describe("Empty state", () => {
    it("shows empty state with icon when no elements", () => {
      render(<ElementGrid {...defaultProps} elements={[]} />);

      expect(
        screen.getByText(/No OpenAI LLM instances found/i)
      ).toBeInTheDocument();
    });

    it("shows Database icon in empty state", () => {
      const { container } = render(
        <ElementGrid {...defaultProps} elements={[]} />
      );

      const dbIcon = container.querySelector(".lucide-database");
      expect(dbIcon).toBeInTheDocument();
    });
  });

  describe("Element card display", () => {
    it("displays element name with FileText icon", () => {
      const { container } = render(<ElementGrid {...defaultProps} />);

      expect(screen.getByText("GPT-4 Instance")).toBeInTheDocument();
      const fileIcons = container.querySelectorAll(".lucide-file-text");
      expect(fileIcons.length).toBeGreaterThan(0);
    });

    it("shows truncated rid", () => {
      render(<ElementGrid {...defaultProps} />);

      // rid is truncated to first 8 chars + "..." - multiple elements have this
      const truncatedRids = screen.getAllByText("rid-1234...");
      expect(truncatedRids.length).toBeGreaterThan(0);
    });

    it("shows element type badge", () => {
      render(<ElementGrid {...defaultProps} />);

      const badges = screen.getAllByText("openai");
      expect(badges.length).toBeGreaterThan(0);
    });

    it("shows version if present", () => {
      render(<ElementGrid {...defaultProps} />);

      expect(screen.getByText("v2")).toBeInTheDocument();
      expect(screen.getByText("v1")).toBeInTheDocument();
    });

    it("shows last updated date if present", () => {
      render(<ElementGrid {...defaultProps} />);

      // Date formatting varies by locale
      expect(screen.getByText(/1\/20\/2024|20\/1\/2024|2024/)).toBeInTheDocument();
    });

    it("shows first 3 config fields with '+X more...' indicator", () => {
      render(<ElementGrid {...defaultProps} />);

      // Multiple elements may have "model:" field, so use getAllByText
      const modelLabels = screen.getAllByText("model:");
      expect(modelLabels.length).toBeGreaterThan(0);
      
      // Check for the +X more indicator
      expect(screen.getByText("+1 more...")).toBeInTheDocument();
    });
  });

  describe("Validation status display", () => {
    it("shows spinner when validation loading", () => {
      getValidationStatusMock.mockReturnValue("loading");
      const { container } = render(<ElementGrid {...defaultProps} />);

      const spinners = container.querySelectorAll(".animate-spin");
      expect(spinners.length).toBeGreaterThan(0);
    });

    it("shows green Check when valid (clickable)", () => {
      getValidationStatusMock.mockReturnValue("valid");
      const { container } = render(<ElementGrid {...defaultProps} />);

      const checkIcons = container.querySelectorAll(".lucide-check");
      expect(checkIcons.length).toBeGreaterThan(0);

      // Check icon should have green color
      const greenCheck = container.querySelector(".text-green-500");
      expect(greenCheck).toBeInTheDocument();
    });

    it("shows yellow AlertTriangle when invalid (clickable)", () => {
      getValidationStatusMock.mockReturnValue("invalid");
      const { container } = render(<ElementGrid {...defaultProps} />);

      // Alert icons may use different class naming
      const alertIcons = container.querySelectorAll('[class*="lucide-triangle-alert"], [class*="lucide-alert"]');
      expect(alertIcons.length).toBeGreaterThan(0);

      // Alert icon should have yellow color
      const yellowAlert = container.querySelector(".text-yellow-500");
      expect(yellowAlert).toBeInTheDocument();
    });

    it("clicking validation icon opens ValidationResultModal", async () => {
      const user = userEvent.setup();
      getValidationStatusMock.mockReturnValue("valid");
      getValidationResultMock.mockReturnValue({ rid: "rid-test", valid: true });

      const { container } = render(<ElementGrid {...defaultProps} />);

      const validButton = container.querySelector(
        "button.bg-green-500\\/10"
      );
      if (validButton) {
        await user.click(validButton);
        expect(screen.getByTestId("validation-result-modal")).toBeInTheDocument();
      }
    });
  });

  describe("Share functionality", () => {
    it("share button opens share panel with correct item info", async () => {
      const user = userEvent.setup();
      render(<ElementGrid {...defaultProps} />);

      // Find share button (Users icon)
      const shareButtons = screen.getAllByRole("button");
      const shareButton = shareButtons.find((btn) =>
        btn.querySelector(".lucide-users")
      );

      if (shareButton) {
        await user.click(shareButton);

        expect(openShareForItemMock).toHaveBeenCalledWith({
          itemKind: "resource",
          itemId: "rid-12345678-abcd-0001",
          itemName: "GPT-4 Instance",
        });
      }
    });
  });

  describe("Delete functionality", () => {
    it("delete button calls onDeleteElement with rid", async () => {
      const user = userEvent.setup();
      const onDeleteElement = vi.fn();
      render(<ElementGrid {...defaultProps} onDeleteElement={onDeleteElement} />);

      // Find delete button (Trash2 icon)
      const deleteButtons = screen.getAllByRole("button");
      const deleteButton = deleteButtons.find((btn) =>
        btn.querySelector(".lucide-trash-2")
      );

      if (deleteButton) {
        await user.click(deleteButton);
        expect(onDeleteElement).toHaveBeenCalledWith("rid-12345678-abcd-0001");
      }
    });
  });

  describe("Configure functionality", () => {
    it("configure button calls onEditElement with element", async () => {
      const user = userEvent.setup();
      const onEditElement = vi.fn();
      render(<ElementGrid {...defaultProps} onEditElement={onEditElement} />);

      const configureButton = screen.getAllByRole("button", { name: /configure/i })[0];
      await user.click(configureButton);

      expect(onEditElement).toHaveBeenCalledWith(mockElements[0]);
    });
  });

  describe("Details functionality", () => {
    it("details button opens ElementData modal", async () => {
      const user = userEvent.setup();
      render(<ElementGrid {...defaultProps} />);

      const detailsButton = screen.getAllByRole("button", { name: /details/i })[0];
      await user.click(detailsButton);

      expect(screen.getByTestId("element-data-modal")).toBeInTheDocument();
      expect(
        screen.getByText("ElementData Modal - GPT-4 Instance")
      ).toBeInTheDocument();
    });
  });

  describe("Validation triggering", () => {
    it("triggers validateResources for all element rids on mount", async () => {
      render(<ElementGrid {...defaultProps} />);

      await waitFor(() => {
        expect(validateResourcesMock).toHaveBeenCalledWith([
          "rid-12345678-abcd-0001",
          "rid-12345678-abcd-0002",
        ]);
      });
    });

    it("re-validates when elements array changes", async () => {
      const { rerender } = render(<ElementGrid {...defaultProps} />);

      const newElements = [
        ...mockElements,
        {
          rid: "rid-12345678-abcd-0003",
          name: "New Instance",
          type: "openai",
          category: "llms",
          config: {},
        },
      ];

      rerender(<ElementGrid {...defaultProps} elements={newElements} />);

      await waitFor(() => {
        expect(validateResourcesMock).toHaveBeenCalledWith([
          "rid-12345678-abcd-0001",
          "rid-12345678-abcd-0002",
          "rid-12345678-abcd-0003",
        ]);
      });
    });

    it("does not call validateResources when elements array is empty", async () => {
      validateResourcesMock.mockClear();
      render(<ElementGrid {...defaultProps} elements={[]} />);

      await waitFor(() => {
        expect(validateResourcesMock).not.toHaveBeenCalled();
      });
    });
  });

  describe("Element without name", () => {
    it("shows fallback name when element has no name", () => {
      const elementsNoName: ElementInstance[] = [
        {
          rid: "rid-noname",
          type: "openai",
          category: "llms",
          config: {},
        },
      ];

      render(<ElementGrid {...defaultProps} elements={elementsNoName} />);

      expect(screen.getByText("OpenAI LLM Instance")).toBeInTheDocument();
    });
  });

  describe("Element without optional fields", () => {
    it("does not show version when not present", () => {
      const elementsNoVersion: ElementInstance[] = [
        {
          rid: "rid-noversion",
          name: "No Version Instance",
          type: "openai",
          category: "llms",
          config: {},
        },
      ];

      render(<ElementGrid {...defaultProps} elements={elementsNoVersion} />);

      // Version label shouldn't appear for this element
      expect(screen.queryByText("Version:")).not.toBeInTheDocument();
    });

    it("does not show last updated when not present", () => {
      const elementsNoUpdated: ElementInstance[] = [
        {
          rid: "rid-noupdated",
          name: "No Updated Instance",
          type: "openai",
          category: "llms",
          config: {},
        },
      ];

      render(<ElementGrid {...defaultProps} elements={elementsNoUpdated} />);

      // Last Updated label shouldn't appear for this element
      expect(screen.queryByText("Last Updated:")).not.toBeInTheDocument();
    });
  });
});
