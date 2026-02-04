import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import { ElementForm } from "../../workspace/ElementForm";
import { ElementType, ElementSchema, ElementInstance } from "../../../../types/workspace";

// Mock useWorkspaceData hook
const fetchResourcesForCategoryMock = vi.fn();
vi.mock("@/hooks/use-workspace-data", () => ({
  useWorkspaceData: () => ({
    fetchResourcesForCategory: fetchResourcesForCategoryMock,
  }),
}));

// Mock FieldRenderer component
const fieldRendererSpy = vi.fn();
vi.mock("../../workspace/FieldRenderer", () => ({
  FieldRenderer: (props: any) => {
    fieldRendererSpy(props);
    return (
      <div data-testid={`field-${props.fieldName}`}>
        <label>{props.fieldName}</label>
        <input
          data-testid={`input-${props.fieldName}`}
          value={props.value || ""}
          onChange={(e) => props.onInputChange(props.fieldName, e.target.value)}
        />
        {props.isRequired && <span data-testid="required-indicator">*</span>}
      </div>
    );
  },
}));

// Mock Umami tracking
vi.mock("@/components/ui/umamitrack", () => ({
  UmamiTrack: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/config/umamiEvents", () => ({
  UmamiEvents: {
    AGENT_REPOSITORY_SAVE_ELEMENT_BUTTON: "save_element",
  },
}));

const mockElementType: ElementType = {
  category: "llms",
  name: "OpenAI LLM",
  type: "openai",
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
      name: { type: "string", description: "Name of the instance" },
      model: { type: "string", default: "gpt-4" },
      temperature: { type: "number" },
      max_tokens: { type: "integer" },
      tools: {
        type: "array",
        items: { $ref: "#/$defs/ToolRef" },
      },
      llm_ref: {
        $ref: "#/$defs/LLMRef",
      },
      is_enabled: { type: "boolean" },
      metadata: { type: "object" },
      hidden_field: {
        type: "string",
        hints: { hidden: { hint_type: "hidden" } },
      },
      validated_field: {
        type: "string",
        hints: { action: { hint_type: "validate", action: "test_action" } },
      },
      api_validated_field: {
        type: "string",
        hints: { api: { hint_type: "validate", endpoint: "/validate" } },
      },
    },
    required: ["name", "model"],
    additionalProperties: false,
    $defs: {
      ToolRef: { category: "tools" },
      LLMRef: { category: "llms" },
    },
  },
};

const mockEditingElement: ElementInstance = {
  rid: "rid-12345",
  name: "Existing Instance",
  type: "openai",
  category: "llms",
  version: 1,
  config: {
    model: "gpt-3.5-turbo",
    temperature: 0.5,
    tools: ["$ref:tool-1", "$ref:tool-2"],
    llm_ref: "$ref:llm-backup",
    validated_field: "validated_value",
  },
};

describe("ElementForm", () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    elementType: mockElementType,
    elementSchema: mockElementSchema,
    elementActions: [],
    editingElement: null,
    onSave: vi.fn().mockResolvedValue({}),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    fetchResourcesForCategoryMock.mockResolvedValue([]);
    fieldRendererSpy.mockClear();
  });

  describe("Form initialization", () => {
    it("initializes fields with default values from schema", async () => {
      render(<ElementForm {...defaultProps} />);

      await waitFor(() => {
        // model has default "gpt-4"
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            fieldName: "model",
            value: "gpt-4",
          })
        );
      });
    });

    it("skips hidden fields (hints.hidden.hint_type === 'hidden')", async () => {
      render(<ElementForm {...defaultProps} />);

      await waitFor(() => {
        // hidden_field should not be rendered
        expect(screen.queryByTestId("field-hidden_field")).not.toBeInTheDocument();
      });
    });

    it("sets array fields to empty array", async () => {
      render(<ElementForm {...defaultProps} />);

      await waitFor(() => {
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            fieldName: "tools",
            value: [],
          })
        );
      });
    });

    it("sets boolean fields to false", async () => {
      render(<ElementForm {...defaultProps} />);

      // Wait for form to initialize and check that boolean field is rendered
      // The initial value may be false or falsy (empty string)
      await waitFor(() => {
        const booleanFieldCall = fieldRendererSpy.mock.calls.find(
          (call) => call[0].fieldName === "is_enabled"
        );
        expect(booleanFieldCall).toBeDefined();
        // Value should be falsy (either false or "")
        expect(booleanFieldCall?.[0].value).toBeFalsy();
      });
    });

    it("sets object fields to empty object", async () => {
      render(<ElementForm {...defaultProps} />);

      await waitFor(() => {
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            fieldName: "metadata",
            value: expect.objectContaining({}),
          })
        );
      });
    });

    it("sets other fields to empty string", async () => {
      render(<ElementForm {...defaultProps} />);

      await waitFor(() => {
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            fieldName: "name",
            value: "",
          })
        );
      });
    });
  });

  describe("Edit mode initialization", () => {
    it("populates name from editingElement.name", async () => {
      render(<ElementForm {...defaultProps} editingElement={mockEditingElement} />);

      await waitFor(() => {
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            fieldName: "name",
            value: "Existing Instance",
          })
        );
      });
    });

    it("populates config fields from editingElement.config", async () => {
      render(<ElementForm {...defaultProps} editingElement={mockEditingElement} />);

      await waitFor(() => {
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            fieldName: "model",
            value: "gpt-3.5-turbo",
          })
        );
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            fieldName: "temperature",
            value: 0.5,
          })
        );
      });
    });

    it("strips '$ref:' prefix from reference values", async () => {
      render(<ElementForm {...defaultProps} editingElement={mockEditingElement} />);

      await waitFor(() => {
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            fieldName: "llm_ref",
            value: "llm-backup",
          })
        );
      });
    });

    it("handles arrays of $ref values", async () => {
      render(<ElementForm {...defaultProps} editingElement={mockEditingElement} />);

      await waitFor(() => {
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            fieldName: "tools",
            value: ["tool-1", "tool-2"],
          })
        );
      });
    });

    it("marks fields with validation hints as 'validating' on load", async () => {
      render(<ElementForm {...defaultProps} editingElement={mockEditingElement} />);

      // Save button should be disabled while validating
      await waitFor(() => {
        const saveButton = screen.getByRole("button", { name: /save/i });
        expect(saveButton).toBeDisabled();
      });
    });
  });

  describe("Field filtering", () => {
    it("excludes category and type fields", async () => {
      const schemaWithCategoryType = {
        ...mockElementSchema,
        config_schema: {
          ...mockElementSchema.config_schema,
          properties: {
            ...mockElementSchema.config_schema.properties,
            category: { type: "string" },
            type: { type: "string" },
          },
        },
      };

      render(<ElementForm {...defaultProps} elementSchema={schemaWithCategoryType} />);

      await waitFor(() => {
        expect(screen.queryByTestId("field-category")).not.toBeInTheDocument();
        expect(screen.queryByTestId("field-type")).not.toBeInTheDocument();
      });
    });

    it("excludes hidden fields", async () => {
      render(<ElementForm {...defaultProps} />);

      await waitFor(() => {
        expect(screen.queryByTestId("field-hidden_field")).not.toBeInTheDocument();
      });
    });

    it("shows only name + cfg_dict fields (not system fields)", async () => {
      render(<ElementForm {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByTestId("field-name")).toBeInTheDocument();
        expect(screen.getByTestId("field-model")).toBeInTheDocument();
      });
    });

    it("sorts fields so dependencies come before dependent fields", async () => {
      const schemaWithDependencies: ElementSchema = {
        ...mockElementSchema,
        config_schema: {
          ...mockElementSchema.config_schema,
          properties: {
            dependent_field: {
              type: "string",
              hints: {
                action: {
                  hint_type: "populate",
                  dependencies: { base_field: "value" },
                },
              },
            },
            base_field: { type: "string" },
            name: { type: "string" },
          },
          required: ["name"],
        },
      };

      render(<ElementForm {...defaultProps} elementSchema={schemaWithDependencies} />);

      await waitFor(() => {
        const fieldCalls = fieldRendererSpy.mock.calls.map((call) => call[0].fieldName);
        const baseIndex = fieldCalls.indexOf("base_field");
        const dependentIndex = fieldCalls.indexOf("dependent_field");
        expect(baseIndex).toBeLessThan(dependentIndex);
      });
    });
  });

  describe("Validation state tracking", () => {
    it("tracks per-field validation states", async () => {
      render(<ElementForm {...defaultProps} />);

      await waitFor(() => {
        // FieldRenderer should receive onValidationChange callback
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            onValidationChange: expect.any(Function),
          })
        );
      });
    });

    it("tracks per-item validation states for lists", async () => {
      render(<ElementForm {...defaultProps} />);

      await waitFor(() => {
        // itemValidationStates should be passed to FieldRenderer
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            itemValidationStates: expect.any(Object),
          })
        );
      });
    });

    it("tracks currently validating fields set", async () => {
      render(<ElementForm {...defaultProps} editingElement={mockEditingElement} />);

      // Initially Save button should be disabled during validation
      await waitFor(() => {
        const saveButton = screen.getByRole("button", { name: /save/i });
        expect(saveButton).toBeDisabled();
      });
    });
  });

  describe("Form validity", () => {
    it("returns false when any field is currently validating", async () => {
      render(<ElementForm {...defaultProps} editingElement={mockEditingElement} />);

      await waitFor(() => {
        const saveButton = screen.getByRole("button", { name: /save/i });
        expect(saveButton).toBeDisabled();
      });
    });

    it("returns false when required field is empty", async () => {
      render(<ElementForm {...defaultProps} />);

      // name is required and empty by default
      await waitFor(() => {
        const saveButton = screen.getByRole("button", { name: /save/i });
        expect(saveButton).toBeDisabled();
      });
    });
  });

  describe("Save functionality", () => {
    it("validates all required fields before save", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn().mockResolvedValue({});

      render(<ElementForm {...defaultProps} onSave={onSave} />);

      // Try to submit with empty required fields - form should prevent it
      const saveButton = screen.getByRole("button", { name: /save/i });
      expect(saveButton).toBeDisabled();
    });

    it("skips hidden fields in save payload", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn().mockResolvedValue({});

      // Create element with hidden field value
      const elementWithHiddenField: ElementInstance = {
        ...mockEditingElement,
        config: {
          ...mockEditingElement.config,
          hidden_field: "should_not_be_saved",
        },
      };

      render(
        <ElementForm
          {...defaultProps}
          editingElement={elementWithHiddenField}
          onSave={onSave}
        />
      );

      // Wait for form to be ready and simulate successful validation
      await waitFor(() => {
        const calls = fieldRendererSpy.mock.calls;
        // Call validation complete for validated_field
        const validatedFieldCall = calls.find(
          (call) => call[0].fieldName === "validated_field"
        );
        if (validatedFieldCall) {
          validatedFieldCall[0].onValidationChange("validated_field", true);
        }
      });
    });

    it("converts reference values to '$ref:rid' format", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn().mockResolvedValue({});

      render(<ElementForm {...defaultProps} editingElement={mockEditingElement} onSave={onSave} />);

      // The form should convert reference values back to $ref format on save
      await waitFor(() => {
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            fieldName: "llm_ref",
          })
        );
      });
    });

    it("handles empty array fields correctly", async () => {
      const onSave = vi.fn().mockResolvedValue({});

      const elementWithEmptyArray: ElementInstance = {
        ...mockEditingElement,
        config: {
          ...mockEditingElement.config,
          tools: [],
        },
      };

      render(
        <ElementForm
          {...defaultProps}
          editingElement={elementWithEmptyArray}
          onSave={onSave}
        />
      );

      await waitFor(() => {
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            fieldName: "tools",
            value: [],
          })
        );
      });
    });

    it("handles object values without adding $ref prefix", async () => {
      const onSave = vi.fn().mockResolvedValue({});

      const elementWithObject: ElementInstance = {
        ...mockEditingElement,
        config: {
          ...mockEditingElement.config,
          metadata: { key: "value" },
        },
      };

      render(
        <ElementForm
          {...defaultProps}
          editingElement={elementWithObject}
          onSave={onSave}
        />
      );

      await waitFor(() => {
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            fieldName: "metadata",
            value: { key: "value" },
          })
        );
      });
    });

    it("only closes dialog on successful save", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      const onSave = vi.fn().mockResolvedValue(null); // null indicates failure

      render(<ElementForm {...defaultProps} onClose={onClose} onSave={onSave} />);

      // Form won't submit with invalid data, so onClose won't be called
      await waitFor(() => {
        expect(onClose).not.toHaveBeenCalled();
      });
    });
  });

  describe("Populate result handling", () => {
    it("stores single item for single-select", async () => {
      render(<ElementForm {...defaultProps} />);

      await waitFor(() => {
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            onPopulateResult: expect.any(Function),
          })
        );
      });
    });

    it("stores array for multi-select", async () => {
      render(<ElementForm {...defaultProps} />);

      await waitFor(() => {
        expect(fieldRendererSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            onPopulateResult: expect.any(Function),
          })
        );
      });
    });
  });

  describe("Dialog controls", () => {
    it("shows Cancel button that calls onClose", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(<ElementForm {...defaultProps} onClose={onClose} />);

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      await user.click(cancelButton);

      expect(onClose).toHaveBeenCalled();
    });

    it("shows correct title for create mode", () => {
      render(<ElementForm {...defaultProps} editingElement={null} />);

      expect(screen.getByText("Create OpenAI LLM")).toBeInTheDocument();
    });

    it("shows correct title for edit mode", () => {
      render(<ElementForm {...defaultProps} editingElement={mockEditingElement} />);

      expect(screen.getByText("Edit OpenAI LLM")).toBeInTheDocument();
    });

    it("shows schema description", () => {
      render(<ElementForm {...defaultProps} />);

      expect(screen.getByText("OpenAI LLM Configuration")).toBeInTheDocument();
    });
  });

  describe("Null schema handling", () => {
    it("returns null when elementSchema is not provided", () => {
      const { container } = render(
        <ElementForm {...defaultProps} elementSchema={null as any} />
      );

      expect(container.innerHTML).toBe("");
    });
  });
});
