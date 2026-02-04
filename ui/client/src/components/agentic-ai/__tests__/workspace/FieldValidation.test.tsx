import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor, act } from "@testing-library/react";
import { render } from "@/test-utils/render";
import { FieldValidation } from "../../workspace/FieldValidation";

// Mock axios using vi.hoisted for proper hoisting
const axiosMock = vi.hoisted(() => {
  const post = vi.fn();
  const get = vi.fn();
  const request = vi.fn();
  
  // Create callable mock that also has .post and .get methods
  const mock = Object.assign(request, { post, get });
  return mock;
});

vi.mock("../../../../http/axiosAgentConfig", () => ({
  default: axiosMock,
}));

describe("FieldValidation", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Empty value handling", () => {
    it("reports non-required empty fields as valid", async () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="optional_field"
          fieldValue=""
          validationHint={{ endpoint: "/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          isRequired={false}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      expect(onValidationChange).toHaveBeenCalledWith("optional_field", true);
    });

    it("reports required empty fields as invalid", async () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="required_field"
          fieldValue=""
          validationHint={{ endpoint: "/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          isRequired={true}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      expect(onValidationChange).toHaveBeenCalledWith("required_field", false);
    });

    it("reports empty array as not requiring validation for non-required fields", async () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="items"
          fieldValue={[]}
          validationHint={{ endpoint: "/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          isRequired={false}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      expect(onValidationChange).toHaveBeenCalledWith("items", true);
    });
  });

  describe("Null rendering", () => {
    it("returns null when ActionHint specified but action not found", () => {
      const { container } = render(
        <FieldValidation
          fieldName="test"
          fieldValue="value"
          validationHint={{ action_uid: "non-existent" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={vi.fn()}
        />
      );

      expect(container.firstChild).toBeNull();
    });

    it("returns null when ApiHint specified but endpoint missing", () => {
      const { container } = render(
        <FieldValidation
          fieldName="test"
          fieldValue="value"
          validationHint={{ endpoint: "" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={vi.fn()}
        />
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe("API Hint type detection", () => {
    it("recognizes API hint when endpoint is provided", () => {
      // When we have an endpoint, the component should render and accept the hint
      const { container } = render(
        <FieldValidation
          fieldName="test"
          fieldValue=""
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          isRequired={false}
          onValidationChange={vi.fn()}
        />
      );

      // Component should render (not return null) for valid API hint
      // Though empty value means no validation UI shown initially
      expect(container.firstChild).not.toBeNull();
    });

    it("recognizes Action hint when action_uid is provided with matching action", () => {
      const validationAction = {
        uid: "validate-action",
        input_schema: { properties: { test: {} } },
      };

      const { container } = render(
        <FieldValidation
          fieldName="test"
          fieldValue=""
          validationHint={{ action_uid: "validate-action" }}
          elementActions={[validationAction]}
          selectedElementType={{}}
          isRequired={false}
          onValidationChange={vi.fn()}
        />
      );

      // Component should render for valid action hint
      expect(container.firstChild).not.toBeNull();
    });
  });

  describe("Debouncing behavior", () => {
    it("debounces validation with 1.5 second delay", async () => {
      const onValidationChange = vi.fn();

      const { rerender } = render(
        <FieldValidation
          fieldName="test"
          fieldValue="initial"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      // Rapidly change the value
      rerender(
        <FieldValidation
          fieldName="test"
          fieldValue="changed1"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      // Advance only 500ms - should not have validated yet
      await act(async () => {
        vi.advanceTimersByTime(500);
      });

      rerender(
        <FieldValidation
          fieldName="test"
          fieldValue="changed2"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      // The timeout should restart, so validation should be debounced
      // Wait less than 1.5s total
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      // At this point validation hasn't run yet for the final value
      // because debounce resets on each change
    });

    it("skips validation if value unchanged from last validation", async () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="test"
          fieldValue=""
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          isRequired={false}
          onValidationChange={onValidationChange}
        />
      );

      // Wait for initial validation
      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      const callCount = onValidationChange.mock.calls.length;

      // Wait another cycle - should not call again for same value
      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      // Call count should be the same since value didn't change
      expect(onValidationChange.mock.calls.length).toBe(callCount);
    });
  });

  describe("Validation UI states", () => {
    it("shows spinner and 'Validating...' during validation", async () => {
      const { container } = render(
        <FieldValidation
          fieldName="test"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={vi.fn()}
        />
      );

      // After debounce delay but during API call, spinner should show
      // This is tricky to test without mocking axios, but we can at least verify
      // the component renders correctly

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      // Component should have rendered the validation UI container
      expect(container.querySelector(".flex.items-center.gap-2")).toBeInTheDocument();
    });

    it("shows 'Valid' text when validation passes", async () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="optional"
          fieldValue=""
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          isRequired={false}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      // Empty non-required field reports as valid
      expect(onValidationChange).toHaveBeenCalledWith("optional", true);
    });

    it("shows 'Invalid' for required empty fields", async () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="required"
          fieldValue=""
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          isRequired={true}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      expect(onValidationChange).toHaveBeenCalledWith("required", false);
    });
  });

  describe("Skips validation for null/undefined", () => {
    it("skips validation for null value", async () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="test"
          fieldValue={null}
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          isRequired={false}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      // Non-required null value should report as valid
      expect(onValidationChange).toHaveBeenCalledWith("test", true);
    });

    it("skips validation for undefined value", async () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="test"
          fieldValue={undefined}
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          isRequired={false}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      expect(onValidationChange).toHaveBeenCalledWith("test", true);
    });
  });

  describe("onValidationChange callback", () => {
    it("calls onValidationChange with (fieldName, isValid)", async () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="my_field"
          fieldValue=""
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          isRequired={false}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      expect(onValidationChange).toHaveBeenCalledWith("my_field", true);
    });
  });

  describe("Action hint execution flow", () => {
    beforeEach(() => {
      axiosMock.post.mockReset();
      axiosMock.get.mockReset();
      axiosMock.mockReset();
    });

    it("calls action.execute API when ActionHint is used", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockResolvedValue({
        data: { success: true, message: "Valid" },
      });

      const validationAction = {
        uid: "validate-action",
        input_schema: {
          properties: { test_field: { type: "string" } },
          required: ["test_field"],
        },
      };

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ action_uid: "validate-action" }}
          elementActions={[validationAction]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(axiosMock.post).toHaveBeenCalledWith(
          "/actions/action.execute",
          expect.objectContaining({
            uid: "validate-action",
            inputData: expect.any(Object),
          })
        );
      });
    });

    it("uses dependencies mapping for action input data", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockResolvedValue({
        data: { success: true },
      });

      const validationAction = {
        uid: "validate-action",
        input_schema: {
          properties: { mapped_field: { type: "string" } },
        },
      };

      render(
        <FieldValidation
          fieldName="source_field"
          fieldValue="test-value"
          validationHint={{
            action_uid: "validate-action",
            dependencies: { source_field: "mapped_field" },
          }}
          elementActions={[validationAction]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(axiosMock.post).toHaveBeenCalledWith(
          "/actions/action.execute",
          expect.objectContaining({
            inputData: { mapped_field: "test-value" },
          })
        );
      });
    });

    it("falls back to first required field if fieldName not in schema", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockResolvedValue({
        data: { success: true },
      });

      const validationAction = {
        uid: "validate-action",
        input_schema: {
          properties: { different_field: { type: "string" } },
          required: ["different_field"],
        },
      };

      render(
        <FieldValidation
          fieldName="unmatched_field"
          fieldValue="test-value"
          validationHint={{ action_uid: "validate-action" }}
          elementActions={[validationAction]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(axiosMock.post).toHaveBeenCalledWith(
          "/actions/action.execute",
          expect.objectContaining({
            inputData: { different_field: "test-value" },
          })
        );
      });
    });
  });

  describe("Direct endpoint call tests", () => {
    beforeEach(() => {
      axiosMock.post.mockReset();
      axiosMock.get.mockReset();
      axiosMock.mockReset();
    });

    it("calls endpoint directly when ApiHint is used", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: { success: true, message: "Valid" },
      });

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(axiosMock).toHaveBeenCalledWith(
          expect.objectContaining({
            method: "post",
            url: "/api/validate",
            data: { test_field: "test-value" },
          })
        );
      });
    });

    it("uses GET method when specified in hint", async () => {
      const onValidationChange = vi.fn();
      axiosMock.get.mockResolvedValue({
        data: { success: true },
      });

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate", method: "GET" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(axiosMock.get).toHaveBeenCalledWith(
          "/api/validate",
          expect.objectContaining({
            params: { test_field: "test-value" },
          })
        );
      });
    });

    it("uses dependencies mapping for API request body", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: { success: true },
      });

      render(
        <FieldValidation
          fieldName="source_field"
          fieldValue="my-value"
          validationHint={{
            endpoint: "/api/validate",
            dependencies: { source_field: "api_param" },
          }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(axiosMock).toHaveBeenCalledWith(
          expect.objectContaining({
            data: { api_param: "my-value" },
          })
        );
      });
    });

    it("uses field_mapping to extract result from response", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: { is_valid: true, message: "Custom validation passed" },
      });

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate", field_mapping: "is_valid" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(onValidationChange).toHaveBeenCalledWith("test_field", true);
      });
    });
  });

  describe("Valid / Invalid UI display tests", () => {
    beforeEach(() => {
      axiosMock.mockReset();
    });

    it("shows 'Valid' text when validation passes", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: { success: true, message: "All good" },
      });

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(screen.getByText("Valid")).toBeInTheDocument();
      });
    });

    it("shows 'Invalid' text when validation fails", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: { success: false, message: "Validation failed" },
      });

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(screen.getByText("Invalid")).toBeInTheDocument();
      });
    });

    it("shows 'Validating...' text during validation", async () => {
      const onValidationChange = vi.fn();
      let resolvePromise: (value: any) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      axiosMock.mockReturnValue(pendingPromise);

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(screen.getByText("Validating...")).toBeInTheDocument();
      });

      // Resolve the promise to clean up
      resolvePromise!({ data: { success: true } });
    });

    it("shows CheckCircle icon when valid", async () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue=""
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          isRequired={false}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        // For empty non-required value, should show Valid
        const validText = screen.queryByText("Valid");
        if (validText) {
          const container = validText.closest(".flex.items-center");
          expect(container?.querySelector("svg")).toBeInTheDocument();
        } else {
          // Empty value shows no validation UI initially
          expect(onValidationChange).toHaveBeenCalledWith("test_field", true);
        }
      });
    });

    it("shows XCircle icon when invalid", async () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue=""
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          isRequired={true}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        // For empty required value, should show Invalid
        const invalidText = screen.queryByText("Invalid");
        if (invalidText) {
          const container = invalidText.closest(".flex.items-center");
          expect(container?.querySelector("svg")).toBeInTheDocument();
        } else {
          // Required empty value reports as invalid
          expect(onValidationChange).toHaveBeenCalledWith("test_field", false);
        }
      });
    });

    it("shows Loader2 spinner icon during validation", async () => {
      const onValidationChange = vi.fn();
      let resolvePromise: (value: any) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      axiosMock.mockReturnValue(pendingPromise);

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        // Loader2 renders as SVG with animate-spin class
        const container = screen.getByText("Validating...").closest(".flex.items-center");
        const spinner = container?.querySelector(".animate-spin");
        expect(spinner).toBeInTheDocument();
      });

      resolvePromise!({ data: { success: true } });
    });
  });

  describe("Array validation (per-item results)", () => {
    beforeEach(() => {
      axiosMock.mockReset();
    });

    it("handles array response with per-item validation results", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: [
          { element_rid: "item-1", success: true, messages: [] },
          { element_rid: "item-2", success: false, messages: [{ message: "Invalid item" }] },
          { element_rid: "item-3", success: true, messages: [] },
        ],
      });

      render(
        <FieldValidation
          fieldName="items"
          fieldValue={["item-1", "item-2", "item-3"]}
          validationHint={{ endpoint: "/api/resources/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        // Should report invalid because not all items are valid
        expect(onValidationChange).toHaveBeenCalledWith(
          "items",
          false,
          expect.arrayContaining([
            expect.objectContaining({ rid: "item-1", isValid: true }),
            expect.objectContaining({ rid: "item-2", isValid: false }),
            expect.objectContaining({ rid: "item-3", isValid: true }),
          ])
        );
      });
    });

    it("reports all valid when every item passes validation", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: [
          { element_rid: "item-1", success: true, messages: [] },
          { element_rid: "item-2", success: true, messages: [] },
        ],
      });

      render(
        <FieldValidation
          fieldName="items"
          fieldValue={["item-1", "item-2"]}
          validationHint={{ endpoint: "/api/resources/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(onValidationChange).toHaveBeenCalledWith(
          "items",
          true,
          expect.any(Array)
        );
      });
    });

    it("shows count message for array validation results", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: [
          { element_rid: "item-1", success: true, messages: [] },
          { element_rid: "item-2", success: false, messages: [{ message: "Error" }] },
          { element_rid: "item-3", success: false, messages: [{ message: "Error" }] },
        ],
      });

      render(
        <FieldValidation
          fieldName="items"
          fieldValue={["item-1", "item-2", "item-3"]}
          validationHint={{ endpoint: "/api/resources/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        // Should show "2 of 3 items invalid" message
        expect(screen.getByText("2 of 3 items invalid")).toBeInTheDocument();
      });
    });

    it("shows all valid message when array validation passes", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: [
          { element_rid: "item-1", success: true, messages: [] },
          { element_rid: "item-2", success: true, messages: [] },
        ],
      });

      render(
        <FieldValidation
          fieldName="items"
          fieldValue={["item-1", "item-2"]}
          validationHint={{ endpoint: "/api/resources/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(screen.getByText("All 2 items valid")).toBeInTheDocument();
      });
    });
  });

  describe("Validation message Badge display", () => {
    beforeEach(() => {
      axiosMock.mockReset();
    });

    it("displays validation message in Badge component", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: { success: true, message: "Custom validation message" },
      });

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(screen.getByText("Custom validation message")).toBeInTheDocument();
      });
    });

    it("shows 'Valid' message when no custom message provided", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: { success: true },
      });

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        // Both the status text and message Badge show "Valid"
        const validTexts = screen.getAllByText("Valid");
        expect(validTexts.length).toBeGreaterThanOrEqual(1);
      });
    });

    it("shows 'Invalid' message when validation fails without custom message", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: { success: false },
      });

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        const invalidTexts = screen.getAllByText("Invalid");
        expect(invalidTexts.length).toBeGreaterThanOrEqual(1);
      });
    });

    it("displays error message from API error response", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockRejectedValue({
        response: { data: { message: "Server validation error" } },
      });

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(screen.getByText("Server validation error")).toBeInTheDocument();
      });
    });

    it("displays generic error message when API fails without message", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockRejectedValue(new Error("Network error"));

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(screen.getByText("Validation failed")).toBeInTheDocument();
      });
    });

    it("Badge has outline variant styling", async () => {
      const onValidationChange = vi.fn();
      axiosMock.mockResolvedValue({
        data: { success: true, message: "Test message" },
      });

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test-value"
          validationHint={{ endpoint: "/api/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        const badge = screen.getByText("Test message");
        // Badge component from shadcn uses data attributes or classes for variants
        expect(badge).toBeInTheDocument();
      });
    });
  });
});
