import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { render } from "@/test-utils/render";
import { FieldValidation } from "../../workspace/FieldValidation";

// Mock axios
const axiosMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  __esModule: true,
  default: vi.fn(),
}));

vi.mock("../../../http/axiosAgentConfig", () => ({
  default: axiosMock,
}));

describe("FieldValidation", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    axiosMock.get.mockReset();
    axiosMock.post.mockReset();
    axiosMock.default.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Debouncing", () => {
    it("debounces validation (1.5 second delay after value change)", async () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test value"
          validationHint={{ endpoint: "/validate", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      // Should not validate immediately
      expect(axiosMock.post).not.toHaveBeenCalled();

      // Advance time by 1.5 seconds
      vi.advanceTimersByTime(1500);

      // Now validation should be triggered
      await waitFor(() => {
        expect(axiosMock.post).toHaveBeenCalled();
      });
    });

    it("skips validation for empty/null/undefined values", () => {
      const onValidationChange = vi.fn();

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue=""
          validationHint={{ endpoint: "/validate" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      // Should not call API for empty value
      expect(axiosMock.post).not.toHaveBeenCalled();
    });

    it("skips validation if value unchanged from last validation", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockResolvedValue({ data: { success: true } });

      const { rerender } = render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test"
          validationHint={{ endpoint: "/validate", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(axiosMock.post).toHaveBeenCalledTimes(1);
      });

      // Re-render with same value
      rerender(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test"
          validationHint={{ endpoint: "/validate", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      // Should not call API again for same value
      expect(axiosMock.post).toHaveBeenCalledTimes(1);
    });
  });

  describe("Empty value handling", () => {
    it("reports non-required empty fields as valid", () => {
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

      vi.advanceTimersByTime(1500);

      expect(onValidationChange).toHaveBeenCalledWith("optional_field", true);
    });

    it("reports required empty fields as invalid", () => {
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

      vi.advanceTimersByTime(1500);

      expect(onValidationChange).toHaveBeenCalledWith("required_field", false);
    });
  });

  describe("Action validation", () => {
    it("finds validation action by uid", async () => {
      const onValidationChange = vi.fn();
      const validationAction = {
        uid: "validate-action",
        input_schema: { properties: { value: {} } },
      };

      axiosMock.post.mockResolvedValue({ data: { success: true } });

      render(
        <FieldValidation
          fieldName="test_field"
          fieldValue="test"
          validationHint={{ action_uid: "validate-action" }}
          elementActions={[validationAction]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(axiosMock.post).toHaveBeenCalledWith(
          "/actions/action.execute",
          expect.objectContaining({ uid: "validate-action" })
        );
      });
    });

    it("maps field value using dependencies mapping", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockResolvedValue({ data: { success: true } });

      render(
        <FieldValidation
          fieldName="model_name"
          fieldValue="gpt-4"
          validationHint={{
            action_uid: "validate-model",
            dependencies: { model_name: "model_id" },
          }}
          elementActions={[{ uid: "validate-model", input_schema: {} }]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(axiosMock.post).toHaveBeenCalledWith(
          "/actions/action.execute",
          expect.objectContaining({
            inputData: expect.objectContaining({ model_id: "gpt-4" }),
          })
        );
      });
    });
  });

  describe("API validation", () => {
    it("calls endpoint directly for API hints", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockResolvedValue({ data: { success: true } });

      render(
        <FieldValidation
          fieldName="api_key"
          fieldValue="key-123"
          validationHint={{ endpoint: "/api/validate-key", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(axiosMock.post).toHaveBeenCalled();
      });
    });

    it("uses GET method when hint.method === 'GET'", async () => {
      const onValidationChange = vi.fn();
      axiosMock.get.mockResolvedValue({ data: { success: true } });

      render(
        <FieldValidation
          fieldName="check_field"
          fieldValue="value"
          validationHint={{ endpoint: "/api/check", method: "GET", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(axiosMock.get).toHaveBeenCalled();
      });
    });
  });

  describe("UI states", () => {
    it("shows spinner + 'Validating...' during validation", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(
        <FieldValidation
          fieldName="test"
          fieldValue="test"
          validationHint={{ endpoint: "/validate", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(screen.getByText("Validating...")).toBeInTheDocument();
      });
    });

    it("shows green CheckCircle + 'Valid' when valid", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockResolvedValue({ data: { success: true } });

      const { container } = render(
        <FieldValidation
          fieldName="test"
          fieldValue="test"
          validationHint={{ endpoint: "/validate", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(screen.getByText("Valid")).toBeInTheDocument();
        expect(container.querySelector(".text-green-400")).toBeInTheDocument();
      });
    });

    it("shows red XCircle + 'Invalid' when invalid", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockResolvedValue({ data: { success: false, message: "Invalid value" } });

      const { container } = render(
        <FieldValidation
          fieldName="test"
          fieldValue="bad"
          validationHint={{ endpoint: "/validate", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(screen.getByText("Invalid")).toBeInTheDocument();
        expect(container.querySelector(".text-red-400")).toBeInTheDocument();
      });
    });

    it("shows validation message in Badge", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockResolvedValue({
        data: { success: false, message: "Custom error message" },
      });

      render(
        <FieldValidation
          fieldName="test"
          fieldValue="bad"
          validationHint={{ endpoint: "/validate", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(screen.getByText("Custom error message")).toBeInTheDocument();
      });
    });
  });

  describe("Array validation", () => {
    it("handles array validation (per-item results)", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockResolvedValue({
        data: [
          { element_rid: "item-1", success: true, messages: [] },
          { element_rid: "item-2", success: false, messages: [{ message: "Invalid" }] },
        ],
      });

      render(
        <FieldValidation
          fieldName="items"
          fieldValue={["item-1", "item-2"]}
          validationHint={{ endpoint: "/validate", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(onValidationChange).toHaveBeenCalledWith(
          "items",
          false,
          expect.arrayContaining([
            expect.objectContaining({ rid: "item-1", isValid: true }),
            expect.objectContaining({ rid: "item-2", isValid: false }),
          ])
        );
      });
    });

    it("reports all-valid only when every item passes", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockResolvedValue({
        data: [
          { element_rid: "item-1", success: true },
          { element_rid: "item-2", success: true },
        ],
      });

      render(
        <FieldValidation
          fieldName="items"
          fieldValue={["item-1", "item-2"]}
          validationHint={{ endpoint: "/validate", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(onValidationChange).toHaveBeenCalledWith("items", true, expect.any(Array));
      });
    });
  });

  describe("Callback behavior", () => {
    it("calls onValidationChange with (fieldName, isValid)", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockResolvedValue({ data: { success: true } });

      render(
        <FieldValidation
          fieldName="my_field"
          fieldValue="value"
          validationHint={{ endpoint: "/validate", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(onValidationChange).toHaveBeenCalledWith("my_field", true);
      });
    });

    it("reports false on validation error/exception", async () => {
      const onValidationChange = vi.fn();
      axiosMock.post.mockRejectedValue(new Error("Network error"));

      render(
        <FieldValidation
          fieldName="test"
          fieldValue="value"
          validationHint={{ endpoint: "/validate", field_mapping: "success" }}
          elementActions={[]}
          selectedElementType={{}}
          onValidationChange={onValidationChange}
        />
      );

      vi.advanceTimersByTime(1500);

      await waitFor(() => {
        expect(onValidationChange).toHaveBeenCalledWith("test", false);
      });
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
});
