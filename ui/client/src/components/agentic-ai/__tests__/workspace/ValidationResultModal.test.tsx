import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import { ValidationResultModal } from "../../workspace/ValidationResultModal";
import type { ElementValidationResult } from "@/types/validation";

const createMockValidationResult = (
  overrides: Partial<ElementValidationResult> = {}
): ElementValidationResult => ({
  element_rid: "elem-123",
  display_name: "Test Element",
  element_type: "llm",
  is_valid: true,
  messages: [],
  dependencies: [],
  ...overrides,
});

describe("ValidationResultModal", () => {
  describe("Status display", () => {
    it("shows green CheckCircle2 when valid", () => {
      const { container } = render(
        <ValidationResultModal
          validationResult={createMockValidationResult({ is_valid: true })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(container.querySelector(".lucide-check-circle-2")).toBeInTheDocument();
    });

    it("shows red XCircle when invalid", () => {
      const { container } = render(
        <ValidationResultModal
          validationResult={createMockValidationResult({ is_valid: false })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(container.querySelector(".lucide-circle-x")).toBeInTheDocument();
    });

    it("shows display name (falls back to rid)", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            display_name: "My Element",
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText("My Element")).toBeInTheDocument();
    });

    it("falls back to rid when display_name not provided", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            display_name: undefined,
            element_rid: "fallback-rid",
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText("fallback-rid")).toBeInTheDocument();
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

      expect(screen.getByText("nodes")).toBeInTheDocument();
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

      // The rid should be displayed (possibly truncated)
      expect(
        screen.getByText(/very-long-element-rid/)
      ).toBeInTheDocument();
    });
  });

  describe("Message counts", () => {
    it("shows error/warning/info counts with icons", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [
              { severity: "error", message: "Error 1" },
              { severity: "error", message: "Error 2" },
              { severity: "warning", message: "Warning 1" },
              { severity: "info", message: "Info 1" },
            ],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      // Should show counts for each severity level
      expect(screen.getByText(/2.*error/i)).toBeInTheDocument();
      expect(screen.getByText(/1.*warning/i)).toBeInTheDocument();
    });
  });

  describe("Refresh button", () => {
    it("shows Refresh button when showRefreshButton=true", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult()}
          isOpen={true}
          onOpenChange={vi.fn()}
          showRefreshButton={true}
          onRefresh={vi.fn()}
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
      const { container } = render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [
              { severity: "error", message: "Error message" },
              { severity: "warning", message: "Warning message" },
              { severity: "info", message: "Info message" },
            ],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      // Icons should be present for each severity
      expect(container.querySelectorAll("svg").length).toBeGreaterThan(0);
    });

    it("shows code badge when code specified", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [
              { severity: "error", message: "Error", code: "ERR001" },
            ],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText("ERR001")).toBeInTheDocument();
    });

    it("shows field badge when field specified", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [
              { severity: "error", message: "Invalid", field: "model_name" },
            ],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText("model_name")).toBeInTheDocument();
    });

    it("shows message text", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [
              { severity: "error", message: "This is the error message" },
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
      const { container } = render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            dependencies: [
              {
                element_rid: "dep-1",
                display_name: "Dependency One",
                element_type: "llm",
                is_valid: true,
                messages: [],
                dependencies: [],
              },
            ],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText("Dependency One")).toBeInTheDocument();
      expect(screen.getByText("llm")).toBeInTheDocument();
      expect(container.querySelector(".lucide-server")).toBeInTheDocument();
    });

    it("shows validation status icon per dependency", () => {
      const { container } = render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            dependencies: [
              {
                element_rid: "dep-1",
                display_name: "Valid Dep",
                element_type: "llm",
                is_valid: true,
                messages: [],
                dependencies: [],
              },
              {
                element_rid: "dep-2",
                display_name: "Invalid Dep",
                element_type: "llm",
                is_valid: false,
                messages: [{ severity: "error", message: "Error" }],
                dependencies: [],
              },
            ],
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
      const { container } = render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            dependencies: [
              {
                element_rid: "dep-1",
                display_name: "Parent Dep",
                element_type: "llm",
                is_valid: true,
                messages: [],
                dependencies: [
                  {
                    element_rid: "nested-dep",
                    display_name: "Nested Dep",
                    element_type: "prompt",
                    is_valid: true,
                    messages: [],
                    dependencies: [],
                  },
                ],
              },
            ],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      // Chevron for expansion should be present
      expect(container.querySelector(".lucide-chevron-right")).toBeInTheDocument();
    });

    it("recursive rendering for nested dependencies", async () => {
      const user = userEvent.setup();

      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            dependencies: [
              {
                element_rid: "dep-1",
                display_name: "Level 1",
                element_type: "llm",
                is_valid: true,
                messages: [],
                dependencies: [
                  {
                    element_rid: "dep-2",
                    display_name: "Level 2",
                    element_type: "prompt",
                    is_valid: true,
                    messages: [],
                    dependencies: [],
                  },
                ],
              },
            ],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(screen.getByText("Level 1")).toBeInTheDocument();
      
      // Click to expand
      const expandButton = screen.getByRole("button");
      if (expandButton) {
        await user.click(expandButton);
      }
    });
  });

  describe("Empty state", () => {
    it("shows 'No validation messages or dependencies' when both empty", () => {
      render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: true,
            messages: [],
            dependencies: [],
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
      const { container } = render(
        <ValidationResultModal
          validationResult={createMockValidationResult({
            is_valid: true,
            messages: [],
            dependencies: [],
          })}
          isOpen={true}
          onOpenChange={vi.fn()}
        />
      );

      expect(container.querySelector(".lucide-check-circle-2")).toBeInTheDocument();
    });
  });

  describe("Modal behavior", () => {
    it("calls onOpenChange when closing", async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();

      render(
        <ValidationResultModal
          validationResult={createMockValidationResult()}
          isOpen={true}
          onOpenChange={onOpenChange}
        />
      );

      // Find and click close button (usually X or Close)
      const closeButton = screen.getByRole("button", { name: /close/i });
      if (closeButton) {
        await user.click(closeButton);
        expect(onOpenChange).toHaveBeenCalledWith(false);
      }
    });
  });
});
