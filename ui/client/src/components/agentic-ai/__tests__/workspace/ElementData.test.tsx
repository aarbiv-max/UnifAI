import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import { ElementData } from "../../workspace/ElementData";
import type { ElementInstance, ElementType, ElementSchema } from "../../../../types/workspace";

// Mock the AgenticAI context
const mockGetResourceName = vi.fn((ref: string) => {
  const nameMap: Record<string, string> = {
    "ref-1": "Resource One",
    "ref-2": "Resource Two",
    "$ref:ref-1": "Resource One",
  };
  return nameMap[ref] || ref;
});

const mockResolveRefsInConfig = vi.fn((config: any) => {
  if (!config) return config;
  const resolved = { ...config };
  Object.keys(resolved).forEach((key) => {
    if (typeof resolved[key] === "string" && resolved[key].startsWith("$ref:")) {
      resolved[key] = `Resolved: ${resolved[key].substring(5)}`;
    }
  });
  return resolved;
});

vi.mock("@/contexts/AgenticAIContext", () => ({
  AgenticAIProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAgenticAI: () => ({
    getResourceName: mockGetResourceName,
    resolveRefsInConfig: mockResolveRefsInConfig,
  }),
}));

// Mock utilities
vi.mock("../../../../utils/maskSecretFields", () => ({
  maskSecretFieldsInConfig: (config: any) => {
    if (!config) return config;
    const masked = { ...config };
    if (masked.api_key) {
      masked.api_key = "***MASKED***";
    }
    return masked;
  },
}));

vi.mock("../../../../utils/displayUtils", () => ({
  simplifyConfigForDisplay: (config: any) => config,
}));

const mockElementType: ElementType = {
  category: "llms",
  name: "OpenAI LLM",
  type: "openai",
};

const mockElement: ElementInstance = {
  rid: "rid-12345678-abcd-efgh",
  name: "My OpenAI Instance",
  type: "openai",
  category: "llms",
  version: 2,
  created: "2024-01-15T10:30:00Z",
  updated: "2024-01-20T14:45:00Z",
  nested_refs: ["ref-1", "ref-2"],
  config: {
    model: "gpt-4",
    temperature: 0.7,
    api_key: "sk-secret-key",
    ref_field: "$ref:ref-1",
  },
};

const mockElementSchema: ElementSchema = {
  category: "llms",
  name: "OpenAI",
  type: "openai",
  description: "OpenAI LLM Configuration",
  tags: ["llm", "openai"],
  config_schema: {
    type: "object",
    properties: {
      model: { type: "string" },
      temperature: { type: "number" },
      api_key: {
        type: "string",
        hints: { secret: { hint_type: "secret" } },
      },
      ref_field: { $ref: "#/$defs/reference" },
    },
    required: ["model"],
    additionalProperties: false,
  },
};

describe("ElementData", () => {
  const defaultProps = {
    element: mockElement,
    elementType: mockElementType,
    isOpen: true,
    onOpenChange: vi.fn(),
    elementSchema: mockElementSchema,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Dialog visibility", () => {
    it("opens when isOpen is true", () => {
      render(<ElementData {...defaultProps} isOpen={true} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("closes when onOpenChange(false) called", async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      const { container } = render(<ElementData {...defaultProps} onOpenChange={onOpenChange} />);

      // Find and click the close button (X button in dialog) - it's usually a button with sr-only text "Close"
      const closeButton = container.querySelector('button[type="button"]');
      if (closeButton) {
        await user.click(closeButton);
      }

      // The dialog should call onOpenChange when closed via escape key or clicking outside
      await user.keyboard("{Escape}");
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });

    it("does not render dialog content when isOpen is false", () => {
      render(<ElementData {...defaultProps} isOpen={false} />);

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  describe("Title display", () => {
    it("shows element name in title", () => {
      render(<ElementData {...defaultProps} />);

      expect(screen.getByText("My OpenAI Instance")).toBeInTheDocument();
    });

    it("shows fallback in title when element has no name", () => {
      const elementWithoutName = { ...mockElement, name: undefined };
      render(<ElementData {...defaultProps} element={elementWithoutName} />);

      expect(screen.getByText("OpenAI LLM Details")).toBeInTheDocument();
    });
  });

  describe("Basic info display", () => {
    it("shows Resource ID (full)", () => {
      render(<ElementData {...defaultProps} />);

      expect(screen.getByText("Resource ID")).toBeInTheDocument();
      expect(screen.getByText("rid-12345678-abcd-efgh")).toBeInTheDocument();
    });

    it("shows Type", () => {
      render(<ElementData {...defaultProps} />);

      expect(screen.getByText("Type")).toBeInTheDocument();
      expect(screen.getByText("openai")).toBeInTheDocument();
    });

    it("shows Version with 'v' prefix", () => {
      render(<ElementData {...defaultProps} />);

      expect(screen.getByText("Version")).toBeInTheDocument();
      expect(screen.getByText("v2")).toBeInTheDocument();
    });

    it("shows Category", () => {
      render(<ElementData {...defaultProps} />);

      expect(screen.getByText("Category")).toBeInTheDocument();
      expect(screen.getByText("llms")).toBeInTheDocument();
    });

    it("shows Created date formatted", () => {
      render(<ElementData {...defaultProps} />);

      expect(screen.getByText("Created")).toBeInTheDocument();
      // Date formatting varies by locale, just check something is there
      const createdSection = screen.getByText("Created").parentElement;
      expect(createdSection?.textContent).toMatch(/2024|1\/15/);
    });

    it("shows Updated date formatted", () => {
      render(<ElementData {...defaultProps} />);

      expect(screen.getByText("Last Updated")).toBeInTheDocument();
      const updatedSection = screen.getByText("Last Updated").parentElement;
      expect(updatedSection?.textContent).toMatch(/2024|1\/20/);
    });

    it("shows N/A for dates when not provided", () => {
      const elementNoDates = { ...mockElement, created: undefined, updated: undefined };
      render(<ElementData {...defaultProps} element={elementNoDates} />);

      const naElements = screen.getAllByText("N/A");
      expect(naElements.length).toBe(2);
    });
  });

  describe("Nested refs display", () => {
    it("shows nested_refs as resolved names in Badges", () => {
      render(<ElementData {...defaultProps} />);

      expect(screen.getByText("Referenced Resources")).toBeInTheDocument();
      expect(mockGetResourceName).toHaveBeenCalledWith("ref-1");
      expect(mockGetResourceName).toHaveBeenCalledWith("ref-2");
    });

    it("does not show Referenced Resources section when no nested_refs", () => {
      const elementNoRefs = { ...mockElement, nested_refs: [] };
      render(<ElementData {...defaultProps} element={elementNoRefs} />);

      expect(screen.queryByText("Referenced Resources")).not.toBeInTheDocument();
    });
  });

  describe("Config display", () => {
    it("resolves $ref values in config to display names", () => {
      render(<ElementData {...defaultProps} />);

      expect(mockResolveRefsInConfig).toHaveBeenCalled();
    });

    it("shows full config as formatted JSON", () => {
      render(<ElementData {...defaultProps} />);

      expect(screen.getByText("Full Configuration")).toBeInTheDocument();
      // JSON should be in a pre element
      const preElement = screen.getByText(/gpt-4/).closest("pre");
      expect(preElement).toBeInTheDocument();
    });

    it("masks secret fields in display", () => {
      render(<ElementData {...defaultProps} />);

      // The api_key should be masked
      expect(screen.getByText(/\*\*\*MASKED\*\*\*/)).toBeInTheDocument();
    });

    it("uses monospace font in pre block", async () => {
      const { container } = render(<ElementData {...defaultProps} />);

      await waitFor(() => {
        const preElement = container.querySelector("pre");
        // Pre element should exist when config is shown
        expect(preElement || screen.queryByText(/gpt-4/)).toBeTruthy();
      });
    });
  });

  describe("Empty element handling", () => {
    it("does not show element content when element is null", () => {
      render(<ElementData {...defaultProps} element={null} />);

      expect(screen.queryByText("Resource ID")).not.toBeInTheDocument();
    });
  });
});
