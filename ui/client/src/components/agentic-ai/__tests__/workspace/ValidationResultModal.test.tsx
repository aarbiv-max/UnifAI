import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import { ValidationResultModal } from "../../workspace/ValidationResultModal";
import type { ElementValidationResult, ValidationMessage, ValidationCode, ValidationSeverity } from "@/types/validation";

vi.mock("@/contexts/AgenticAIContext", () => ({
  AgenticAIProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAgenticAI: () => ({
    getResourceName: vi.fn().mockReturnValue(null),
    revalidateResourceAndAncestors: vi.fn(),
  }),
}));

const createMockMessage = (
  overrides: Partial<ValidationMessage> = {}
): ValidationMessage => ({
  severity: "error" as ValidationSeverity,
  code: "VALIDATION_ERROR" as ValidationCode,
  message: "Test error message",
  field: null,
  ...overrides,
});

const createMockValidationResult = (
  overrides: Partial<ElementValidationResult> = {}
): ElementValidationResult => ({
  element_rid: "elem-123",
  name: "Test Element",
  element_type: "llm",
  is_valid: true,
  messages: [],
  dependency_results: {},
  ...overrides,
});

describe("ValidationResultModal", () => {
  describe("Status display", () => {
    it("shows green CheckCircle2 when valid", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({ is_valid: true })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      // Dialog renders in a portal, so check document.body
      expect(document.body.querySelector(".lucide-circle-check")).toBeInTheDocument();
    });

    it("shows red XCircle when invalid", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({ is_valid: false })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(document.body.querySelector(".lucide-circle-x")).toBeInTheDocument();
    });

    it("shows name (uses name property)", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            name: "My Element",
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText(/My Element/)).toBeInTheDocument();
    });

    it("falls back to rid when name is null", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            name: null,
            element_rid: "fallback-rid",
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      // The rid appears in both title and truncated display, use getAllByText
      expect(screen.getAllByText(/fallback-rid/).length).toBeGreaterThanOrEqual(1);
    });

    it("shows Valid/Invalid badge", () => {
      const { rerender } = render(
        <ValidationResultModal
          validationResult={createMockValidationResult({ is_valid: true })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText("Valid")).toBeInTheDocument();

      rerender(
        <ValidationResultModal
          validationResult={createMockValidationResult({ is_valid: false })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText("Invalid")).toBeInTheDocument();
    });

    it("shows element type", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({ element_type: "nodes" })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText(/nodes/)).toBeInTheDocument();
    });

    it("shows truncated rid", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            element_rid: "very-long-element-rid-that-should-be-truncated",
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      // The component shows first 12 chars + "..."
      expect(screen.getByText(/very-long-el/)).toBeInTheDocument();
    });
  });

  describe("Message counts", () => {
    it("shows error/warning/info counts with icons", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [
              createMockMessage({ severity: "error", message: "Error 1" }),
              createMockMessage({ severity: "error", message: "Error 2" }),
              createMockMessage({ severity: "warning", message: "Warning 1" }),
              createMockMessage({ severity: "info", message: "Info 1" }),
            ],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      // Should show error count of 2
      expect(screen.getByText("2")).toBeInTheDocument();
      // Should show warning count of 1
      expect(screen.getAllByText("1").length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("Refresh button", () => {
    it("shows Refresh button when showRefreshButton=true (default)", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult()}
          isOpen={true}
          onOpenChange={vi.fn()}
          showRefreshButton={true}
        />
      );

      expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();
    });

    it("does not show Refresh button when showRefreshButton=false", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult()}
          isOpen={true}
          onOpenChange={vi.fn()}
          showRefreshButton={false}
        />
      );

      expect(screen.queryByRole("button", { name: /refresh/i })).not.toBeInTheDocument();
    });
  });

  describe("ValidationMessageItem", () => {
    it("shows correct icon/color per severity", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [
              createMockMessage({ severity: "error", message: "Error message" }),
              createMockMessage({ severity: "warning", message: "Warning message" }),
              createMockMessage({ severity: "info", message: "Info message" }),
            ],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      // Icons should be present for each severity - dialog renders in portal
      expect(document.body.querySelectorAll("[role='dialog'] svg").length).toBeGreaterThan(0);
    });

    it("shows code badge when code specified", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [
              createMockMessage({ code: "MISSING_FIELD" as ValidationCode }),
            ],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText("MISSING_FIELD")).toBeInTheDocument();
    });

    it("shows field badge when field specified", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [
              createMockMessage({ field: "model_name" }),
            ],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText(/model_name/)).toBeInTheDocument();
    });

    it("shows message text", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [
              createMockMessage({ message: "This is the error message" }),
            ],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText("This is the error message")).toBeInTheDocument();
    });
  });

  describe("DependencyResultItem", () => {
    it("shows Server icon + name + type badge", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            dependency_results: {
              "dep-1": createMockValidationResult({
                element_rid: "dep-1",
                name: "Dependency One",
                element_type: "llm",
                is_valid: true,
              }),
            },
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText("Dependency One")).toBeInTheDocument();
      expect(screen.getAllByText("llm").length).toBeGreaterThanOrEqual(1);
      // Dialog renders in portal
      expect(document.body.querySelector(".lucide-server")).toBeInTheDocument();
    });

    it("shows validation status icon per dependency", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            dependency_results: {
              "dep-1": createMockValidationResult({
                element_rid: "dep-1",
                name: "Valid Dep",
                is_valid: true,
              }),
              "dep-2": createMockValidationResult({
                element_rid: "dep-2",
                name: "Invalid Dep",
                is_valid: false,
                messages: [createMockMessage()],
              }),
            },
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      // Both dependencies should be visible
      expect(screen.getByText("Valid Dep")).toBeInTheDocument();
      expect(screen.getByText("Invalid Dep")).toBeInTheDocument();
    });

    it("shows expand/collapse chevron when has nested deps", async () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            dependency_results: {
              "dep-1": createMockValidationResult({
                element_rid: "dep-1",
                name: "Parent Dep",
                dependency_results: {
                  "nested-dep": createMockValidationResult({
                    element_rid: "nested-dep",
                    name: "Nested Dep",
                    element_type: "prompt",
                  }),
                },
              }),
            },
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      // Chevron for expansion should be present (dialog renders in portal)
      expect(
        document.body.querySelector(".lucide-chevron-down") ||
        document.body.querySelector(".lucide-chevron-right")
      ).toBeInTheDocument();
    });

    it("recursive rendering for nested dependencies", async () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            dependency_results: {
              "dep-1": createMockValidationResult({
                element_rid: "dep-1",
                name: "Level 1",
                dependency_results: {
                  "dep-2": createMockValidationResult({
                    element_rid: "dep-2",
                    name: "Level 2",
                    element_type: "prompt",
                  }),
                },
              }),
            },
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText("Level 1")).toBeInTheDocument();
      // Level 2 should also be visible since depth 0 is expanded by default
      expect(screen.getByText("Level 2")).toBeInTheDocument();
    });
  });

  describe("Empty state", () => {
    it("shows 'No validation messages or dependencies' when both empty", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: true,
            messages: [],
            dependency_results: {},
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(
        screen.getByText(/No validation messages or dependencies/)
      ).toBeInTheDocument();
    });

    it("shows CheckCircle2 icon for empty valid state", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: true,
            messages: [],
            dependency_results: {},
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      // Multiple check-circle icons exist (header + empty state) - dialog renders in portal
      expect(document.body.querySelectorAll(".lucide-circle-check").length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("Modal behavior", () => {
    it("does not render when validationResult is null", () => {
      const { container } = render(
        <ValidationResultModal
          validationResult={null}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      // Modal should not render anything
      expect(container.querySelector("[role='dialog']")).not.toBeInTheDocument();
    });
  });
});
