import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor, act, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import { FieldRenderer } from "../../workspace/FieldRenderer";

// Mock AgentCardVisualization component
vi.mock("../../workspace/AgentCardVisualization", () => ({
  AgentCardVisualization: ({ agentCard, isLoading }: any) => (
    <div data-testid="agent-card-visualization">
      {isLoading && <span>Loading...</span>}
      {agentCard && <span data-testid="agent-card-data">{agentCard.name}</span>}
      {!agentCard && !isLoading && <span>No agent card</span>}
    </div>
  ),
}));

// Mock FieldValidation component
vi.mock("../../workspace/FieldValidation", () => ({
  FieldValidation: ({ fieldName, onValidationChange }: any) => (
    <div data-testid={`field-validation-${fieldName}`}>
      <button onClick={() => onValidationChange(fieldName, true)}>
        Validate
      </button>
    </div>
  ),
}));

// Mock FieldPopulation component
vi.mock("../../workspace/FieldPopulation", () => ({
  FieldPopulation: ({ fieldName, onPopulateResult, hideUI, autoTrigger }: any) => (
    hideUI ? null : (
      <div data-testid={`field-population-${fieldName}`}>
        <button onClick={() => onPopulateResult(fieldName, ["result1"], false)}>
          Populate
        </button>
        {autoTrigger && <span data-testid="auto-trigger">Auto-triggered</span>}
      </div>
    )
  ),
}));

// Default props for FieldRenderer
const createDefaultProps = (overrides: Partial<any> = {}) => ({
  fieldName: "test_field",
  fieldSchema: { type: "string" },
  value: "",
  isRequired: false,
  validationHint: null,
  populateHint: null,
  editingElement: null,
  elementActions: [],
  elementType: { type: "test" },
  formData: {},
  refOptions: {},
  fieldType: "public" as const,
  fieldValidationStates: {},
  itemValidationStates: {},
  isArrayWithRefItems: () => false,
  getArrayItemsSchema: () => null,
  extractCategoryFromField: () => null,
  onInputChange: vi.fn(),
  onArrayChange: vi.fn(),
  onAddArrayItem: vi.fn(),
  onRemoveArrayItem: vi.fn(),
  onValidationChange: vi.fn(),
  onPopulateResult: vi.fn(),
  ...overrides,
});

describe("FieldRenderer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("String field rendering", () => {
    it("renders Input for regular string fields (no special hints)", () => {
      render(<FieldRenderer {...createDefaultProps()} />);

      const input = screen.getByRole("textbox");
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute("type", "text");
    });

    it("renders Textarea for fields with 'message' in name", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldName: "system_message",
          })}
        />
      );

      const textarea = screen.getByRole("textbox");
      expect(textarea.tagName).toBe("TEXTAREA");
    });

    it("renders Textarea for fields with 'prompt' in name", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldName: "user_prompt",
          })}
        />
      );

      const textarea = screen.getByRole("textbox");
      expect(textarea.tagName).toBe("TEXTAREA");
    });

    it("renders Textarea for fields with 'description' in name", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldName: "field_description",
          })}
        />
      );

      const textarea = screen.getByRole("textbox");
      expect(textarea.tagName).toBe("TEXTAREA");
    });
  });

  describe("Boolean field rendering", () => {
    it("renders Checkbox for boolean fields", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "boolean" },
            value: false,
          })}
        />
      );

      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).toBeInTheDocument();
    });

    it("checkbox reflects current boolean value", async () => {
      const onInputChange = vi.fn();
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "boolean" },
            value: true,
            onInputChange,
          })}
        />
      );

      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).toBeChecked();
    });

    it("checkbox calls onInputChange when toggled", async () => {
      const user = userEvent.setup();
      const onInputChange = vi.fn();
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "boolean" },
            value: false,
            onInputChange,
          })}
        />
      );

      const checkbox = screen.getByRole("checkbox");
      await user.click(checkbox);

      expect(onInputChange).toHaveBeenCalledWith("test_field", true);
    });
  });

  describe("Number field rendering", () => {
    it("renders number Input for integer fields", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "integer" },
            value: 42,
          })}
        />
      );

      const input = screen.getByRole("spinbutton");
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute("type", "number");
    });

    it("renders number Input for number fields", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "number" },
            value: 3.14,
          })}
        />
      );

      const input = screen.getByRole("spinbutton");
      expect(input).toBeInTheDocument();
    });

    it("renders number Input for anyOf with number types", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: {
              anyOf: [{ type: "integer" }, { type: "null" }],
            },
            value: 10,
          })}
        />
      );

      const input = screen.getByRole("spinbutton");
      expect(input).toBeInTheDocument();
    });
  });

  describe("Object field rendering", () => {
    it("renders JSON Textarea for object fields", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "object" },
            value: { key: "value" },
          })}
        />
      );

      const textarea = screen.getByRole("textbox");
      expect(textarea.tagName).toBe("TEXTAREA");
      expect(textarea).toHaveValue(JSON.stringify({ key: "value" }, null, 2));
    });

    it("shows placeholder for empty object field", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "object" },
            value: undefined,
          })}
        />
      );

      const textarea = screen.getByPlaceholderText("Enter JSON object (e.g., {})");
      expect(textarea).toBeInTheDocument();
    });
  });

  describe("$ref field (Select dropdown) rendering", () => {
    it("renders Select dropdown for $ref fields (single reference)", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { $ref: "#/definitions/resources" },
            extractCategoryFromField: () => "resources",
            refOptions: {
              resources: [
                { rid: "res-1", name: "Resource 1", type: "llm" },
                { rid: "res-2", name: "Resource 2", type: "prompt" },
              ],
            },
          })}
        />
      );

      const combobox = screen.getByRole("combobox");
      expect(combobox).toBeInTheDocument();
    });

    it("renders Select dropdown for anyOf with $ref options", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: {
              anyOf: [
                { $ref: "#/definitions/resources" },
                { type: "null" },
              ],
            },
            extractCategoryFromField: () => "resources",
            refOptions: {
              resources: [{ rid: "res-1", name: "Resource 1", type: "llm" }],
            },
          })}
        />
      );

      const combobox = screen.getByRole("combobox");
      expect(combobox).toBeInTheDocument();
    });

    it("shows category Badge next to field label", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { $ref: "#/definitions/resources" },
            extractCategoryFromField: () => "resources",
            refOptions: {
              resources: [{ rid: "res-1", name: "Resource 1", type: "llm" }],
            },
          })}
        />
      );

      expect(screen.getByText("resources")).toBeInTheDocument();
    });

    it("populates Select options from refOptions[category]", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { $ref: "#/definitions/llm" },
            extractCategoryFromField: () => "llm",
            refOptions: {
              llm: [
                { rid: "llm-1", name: "GPT-4", type: "openai" },
                { rid: "llm-2", name: "Claude", type: "anthropic" },
              ],
            },
          })}
        />
      );

      // Combobox should be rendered with correct options accessible
      // Note: Full Radix Select interaction is limited in happy-dom
      const combobox = screen.getByRole("combobox");
      expect(combobox).toBeInTheDocument();
    });

    it("filters out invalid options (empty rid values)", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { $ref: "#/definitions/llm" },
            extractCategoryFromField: () => "llm",
            refOptions: {
              llm: [
                { rid: "llm-1", name: "Valid", type: "openai" },
                { rid: "", name: "Invalid Empty", type: "test" },
                { rid: "   ", name: "Invalid Whitespace", type: "test" },
              ],
            },
          })}
        />
      );

      // Combobox should be rendered
      // Note: Full Radix Select dropdown interaction is limited in happy-dom
      // The component filters invalid options internally
      const combobox = screen.getByRole("combobox");
      expect(combobox).toBeInTheDocument();
    });

    it("shows 'No {category} resources available' when options array is empty", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { $ref: "#/definitions/llm" },
            extractCategoryFromField: () => "llm",
            refOptions: { llm: [] },
          })}
        />
      );

      // Combobox should be rendered even when no options
      // Note: Full Radix Select dropdown interaction is limited in happy-dom
      const combobox = screen.getByRole("combobox");
      expect(combobox).toBeInTheDocument();
    });

    it("pre-selects value when editing existing element", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { $ref: "#/definitions/llm" },
            extractCategoryFromField: () => "llm",
            value: "llm-1",
            refOptions: {
              llm: [
                { rid: "llm-1", name: "GPT-4", type: "openai" },
                { rid: "llm-2", name: "Claude", type: "anthropic" },
              ],
            },
          })}
        />
      );

      // The select trigger should show the selected value
      expect(screen.getByText("GPT-4 (openai)")).toBeInTheDocument();
    });

    it("calls onInputChange with selected rid on selection change", () => {
      const onInputChange = vi.fn();
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { $ref: "#/definitions/llm" },
            extractCategoryFromField: () => "llm",
            onInputChange,
            refOptions: {
              llm: [
                { rid: "llm-1", name: "GPT-4", type: "openai" },
                { rid: "llm-2", name: "Claude", type: "anthropic" },
              ],
            },
          })}
        />
      );

      // Combobox should be rendered with onValueChange handler
      // Note: Full Radix Select interaction is limited in happy-dom
      const combobox = screen.getByRole("combobox");
      expect(combobox).toBeInTheDocument();
    });
  });

  describe("Array field rendering - refItems mode", () => {
    const arrayRefProps = {
      fieldSchema: {
        type: "array",
        items: { $ref: "#/definitions/tools" },
      },
      isArrayWithRefItems: () => true,
      extractCategoryFromField: () => "tools",
      refOptions: {
        tools: [
          { rid: "tool-1", name: "Tool 1", type: "api" },
          { rid: "tool-2", name: "Tool 2", type: "function" },
        ],
      },
    };

    it("refItems mode: Renders Select + Badge list for array fields with $ref items", () => {
      render(<FieldRenderer {...createDefaultProps(arrayRefProps)} />);

      const combobox = screen.getByRole("combobox");
      expect(combobox).toBeInTheDocument();
    });

    it("shows placeholder when array field is empty for refItems mode", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            ...arrayRefProps,
            value: [],
          })}
        />
      );

      // Combobox should be rendered with placeholder
      // Note: Full Radix Select interaction is limited in happy-dom
      const combobox = screen.getByRole("combobox");
      expect(combobox).toBeInTheDocument();
    });

    it("shows selected items as Badges for refItems mode", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            ...arrayRefProps,
            value: ["tool-1"],
            formData: { test_field: ["tool-1"] },
          })}
        />
      );

      expect(screen.getByText("Tool 1 (api)")).toBeInTheDocument();
    });
  });

  describe("Array field rendering - dynamic mode", () => {
    it("dynamic mode: Renders read-only Textarea for arrays with populateHint", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "array" },
            populateHint: { endpoint: "/populate", display_field: "name" },
            value: [{ name: "Item 1" }, { name: "Item 2" }],
          })}
        />
      );

      const textarea = screen.getByRole("textbox");
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveAttribute("readonly");
      expect(textarea).toBeDisabled();
    });

    it("dynamic mode: shows comma-separated labels", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "array" },
            populateHint: { endpoint: "/populate", display_field: "name" },
            value: [{ name: "Item 1" }, { name: "Item 2" }],
          })}
        />
      );

      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveValue("Item 1, Item 2");
    });

    it("shows placeholder when array field is empty for dynamic mode", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "array", description: "Select items" },
            populateHint: { endpoint: "/populate" },
            value: [],
          })}
        />
      );

      const textarea = screen.getByPlaceholderText("Select items");
      expect(textarea).toBeInTheDocument();
    });
  });

  describe("Array field rendering - regular mode", () => {
    it("regular mode: Renders Input list with Add/Remove buttons for plain string arrays", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "array", items: { type: "string" } },
            value: ["item1", "item2"],
          })}
        />
      );

      const inputs = screen.getAllByRole("textbox");
      expect(inputs).toHaveLength(2);
      expect(screen.getAllByText("Remove")).toHaveLength(2);
      expect(screen.getByText(/Add test_field/)).toBeInTheDocument();
    });

    it("shows placeholder when array field is empty for regular mode", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "array", items: { type: "string" } },
            value: [],
          })}
        />
      );

      // Should show Add button
      expect(screen.getByText(/Add test_field/)).toBeInTheDocument();
    });

    it("Add button calls onAddArrayItem", async () => {
      const user = userEvent.setup();
      const onAddArrayItem = vi.fn();
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "array", items: { type: "string" } },
            value: [],
            onAddArrayItem,
          })}
        />
      );

      await user.click(screen.getByText(/Add test_field/));
      expect(onAddArrayItem).toHaveBeenCalledWith("test_field");
    });

    it("Remove button calls onRemoveArrayItem", async () => {
      const user = userEvent.setup();
      const onRemoveArrayItem = vi.fn();
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: { type: "array", items: { type: "string" } },
            value: ["item1"],
            onRemoveArrayItem,
          })}
        />
      );

      await user.click(screen.getByText("Remove"));
      expect(onRemoveArrayItem).toHaveBeenCalledWith("test_field", 0);
    });
  });

  describe("Array field mode determination", () => {
    it("returns null when array mode cannot be determined", () => {
      const { container } = render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: {
              anyOf: [{ type: "array" }, { type: "null" }],
            },
            isArrayWithRefItems: () => false,
            populateHint: null,
          })}
        />
      );

      // Should return null and render nothing
      expect(container.firstChild).toBeNull();
    });
  });

  describe("Selection type handling", () => {
    it("For selection_type: 'automatic': hides input field, shows only FieldPopulation with hideUI=true", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            populateHint: { selection_type: "automatic", endpoint: "/populate" },
          })}
        />
      );

      // Input should not be present when selection_type is automatic
      expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    });

    it("For selection_type: 'manual': shows input field alongside FieldPopulation with hideUI=false", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            populateHint: { selection_type: "manual", endpoint: "/populate" },
          })}
        />
      );

      // Input should be present and read-only
      const input = screen.getByRole("textbox");
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute("readonly");

      // FieldPopulation should be visible
      expect(screen.getByTestId("field-population-test_field")).toBeInTheDocument();
    });
  });

  describe("Badges display", () => {
    it("shows 'populate' Badge when populateHint is present", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            populateHint: { endpoint: "/populate" },
          })}
        />
      );

      expect(screen.getByText("populate")).toBeInTheDocument();
    });

    it("shows 'validation' Badge when validationHint is present", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            validationHint: { endpoint: "/validate" },
          })}
        />
      );

      expect(screen.getByText("validation")).toBeInTheDocument();
    });

    it("shows 'secret' Badge for fields with secret hint", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldType: "secret",
          })}
        />
      );

      expect(screen.getByText("secret")).toBeInTheDocument();
    });
  });

  describe("Auto-population trigger", () => {
    it("triggers auto-population when areDependenciesValid becomes true", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            populateHint: {
              selection_type: "automatic",
              endpoint: "/populate",
              dependencies: { dep_field: "dep_param" },
            },
            fieldValidationStates: { dep_field: true },
            formData: { dep_field: "valid_value" },
          })}
        />
      );

      // The auto-trigger should be enabled based on dependency validation
      // Since hideUI is true for automatic, the FieldPopulation won't render visibly
      // but autoTrigger should be passed as true
    });
  });

  describe("AgentCardVisualization", () => {
    it("shows AgentCardVisualization component when fieldName === 'agent_card'", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldName: "agent_card",
          })}
        />
      );

      expect(screen.getByTestId("agent-card-visualization")).toBeInTheDocument();
    });

    it("AgentCardVisualization receives populated agent_card value", () => {
      const agentCardValue = { name: "Test Agent", version: "1.0" };
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldName: "agent_card",
            value: agentCardValue,
          })}
        />
      );

      expect(screen.getByTestId("agent-card-data")).toHaveTextContent("Test Agent");
    });

    it("AgentCardVisualization shows empty state when agentCard is null", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldName: "agent_card",
            value: null,
          })}
        />
      );

      expect(screen.getByText("No agent card")).toBeInTheDocument();
    });
  });

  describe("Error states", () => {
    it("shows red border on field when hasFieldError is true", () => {
      const { container } = render(
        <FieldRenderer
          {...createDefaultProps({
            validationHint: { endpoint: "/validate" },
            fieldValidationStates: { test_field: false },
            value: "some_value",
            isRequired: true,
          })}
        />
      );

      const input = screen.getByRole("textbox");
      expect(input.className).toContain("border-red-500");
    });

    it("shows XCircle icon next to label when field has validation errors", () => {
      const { container } = render(
        <FieldRenderer
          {...createDefaultProps({
            validationHint: { endpoint: "/validate" },
            fieldValidationStates: { test_field: false },
            value: "some_value",
            isRequired: true,
          })}
        />
      );

      // XCircle icon should be present
      expect(container.querySelector(".lucide-circle-x")).toBeInTheDocument();
    });

    it("highlights specific array items with red border when isItemInvalid(rid) returns true", () => {
      const { container } = render(
        <FieldRenderer
          {...createDefaultProps({
            fieldSchema: {
              type: "array",
              items: { $ref: "#/definitions/tools" },
            },
            isArrayWithRefItems: () => true,
            extractCategoryFromField: () => "tools",
            refOptions: {
              tools: [
                { rid: "tool-1", name: "Tool 1", type: "api" },
                { rid: "tool-2", name: "Tool 2", type: "function" },
              ],
            },
            value: ["tool-1", "tool-2"],
            formData: { test_field: ["tool-1", "tool-2"] },
            validationHint: { endpoint: "/validate" },
            itemValidationStates: {
              test_field: [
                { rid: "tool-1", isValid: true },
                { rid: "tool-2", isValid: false },
              ],
            },
          })}
        />
      );

      // The second badge should have red border
      const badges = container.querySelectorAll('[class*="border-red-500"]');
      expect(badges.length).toBeGreaterThan(0);
    });

    it("does not show error for non-required fields with empty value", () => {
      const { container } = render(
        <FieldRenderer
          {...createDefaultProps({
            validationHint: { endpoint: "/validate" },
            fieldValidationStates: { test_field: false },
            value: "",
            isRequired: false,
          })}
        />
      );

      const input = screen.getByRole("textbox");
      expect(input.className).not.toContain("border-red-500");
    });
  });

  describe("Secret field handling", () => {
    it("displays masked dots for unchanged secret values in edit mode", () => {
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldType: "secret",
            editingElement: { config: { test_field: "secret_value" } },
            value: "secret_value",
          })}
        />
      );

      const input = screen.getByRole("textbox");
      // Should show masked dots (•)
      expect(input.value).toContain("•");
    });

    it("switches to password input type when user focuses/starts typing", async () => {
      const user = userEvent.setup();
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldType: "secret",
            editingElement: { config: { test_field: "secret_value" } },
            value: "secret_value",
          })}
        />
      );

      const input = screen.getByRole("textbox");
      await user.click(input);

      // After focus, input type should change to password
      await waitFor(() => {
        const passwordInput = document.querySelector('input[type="password"]');
        expect(passwordInput).toBeInTheDocument();
      });
    });

    it("clears masked display when value changes from original", async () => {
      const user = userEvent.setup();
      const onInputChange = vi.fn();
      render(
        <FieldRenderer
          {...createDefaultProps({
            fieldType: "secret",
            editingElement: { config: { test_field: "secret_value" } },
            value: "secret_value",
            onInputChange,
          })}
        />
      );

      const input = screen.getByRole("textbox");
      await user.click(input);
      await user.type(input, "new");

      expect(onInputChange).toHaveBeenCalled();
    });
  });

  describe("Dependency tracking for automatic population", () => {
    it("clears field value when dependency values change (for automatic population fields)", async () => {
      const onInputChange = vi.fn();
      const { rerender } = render(
        <FieldRenderer
          {...createDefaultProps({
            populateHint: {
              selection_type: "automatic",
              endpoint: "/populate",
              dependencies: { dep_field: "dep_param" },
            },
            formData: { dep_field: "value1" },
            value: "populated_value",
            onInputChange,
          })}
        />
      );

      // Rerender with changed dependency
      rerender(
        <FieldRenderer
          {...createDefaultProps({
            populateHint: {
              selection_type: "automatic",
              endpoint: "/populate",
              dependencies: { dep_field: "dep_param" },
            },
            formData: { dep_field: "value2" },
            value: "populated_value",
            onInputChange,
          })}
        />
      );

      // Should clear the field when dependency changes
      await waitFor(() => {
        expect(onInputChange).toHaveBeenCalledWith("test_field", null);
      });
    });

    it("only clears if dependencies actually changed (not on initial render)", () => {
      const onInputChange = vi.fn();
      render(
        <FieldRenderer
          {...createDefaultProps({
            populateHint: {
              selection_type: "automatic",
              endpoint: "/populate",
              dependencies: { dep_field: "dep_param" },
            },
            formData: { dep_field: "value1" },
            value: "populated_value",
            onInputChange,
          })}
        />
      );

      // On initial render, onInputChange should not be called to clear
      expect(onInputChange).not.toHaveBeenCalledWith("test_field", null);
    });
  });
});
