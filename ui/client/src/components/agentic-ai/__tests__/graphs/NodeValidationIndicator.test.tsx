import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import NodeValidationIndicator from "../../graphs/NodeValidationIndicator";
import type { ElementValidationResult, ValidationMessage, ValidationCode, ValidationSeverity } from "@/types/validation";

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
  element_rid: "elem-1",
  element_type: "llm",
  name: "Test Element",
  is_valid: true,
  messages: [],
  dependency_results: {},
  ...overrides,
});

describe("NodeValidationIndicator", () => {
  describe("Validating state", () => {
    it("shows spinner when isValidating is true", () => {
      const { container } = render(
        <NodeValidationIndicator isValidating={true} onClick={vi.fn()} />
      );

      expect(container.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("stops click propagation while validating", async () => {
      const user = userEvent.setup();
      const parentClick = vi.fn();

      const { container } = render(
        <div onClick={parentClick}>
          <NodeValidationIndicator isValidating={true} onClick={vi.fn()} />
        </div>
      );

      // The component renders divs with stopPropagation on click
      // Click on the outer flex container which has the onClick handler
      const flexContainer = container.querySelector(".flex.items-center.justify-center");
      if (flexContainer) {
        await user.click(flexContainer);
      }
      // With isValidating=true, clicks stop propagation
      expect(parentClick).not.toHaveBeenCalled();
    });
  });

  describe("No validation result", () => {
    it("returns null when validationResult is undefined", () => {
      const { container } = render(
        <NodeValidationIndicator
          validationResult={undefined}
          isValidating={false}
          onClick={vi.fn()}
        />
      );

      expect(container.firstChild).toBeNull();
    });

    it("no visual indicator rendered when no result and not validating", () => {
      const { container } = render(
        <NodeValidationIndicator isValidating={false} onClick={vi.fn()} />
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe("Valid state", () => {
    it("shows green CheckCircle2 icon", () => {
      const { container } = render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({ is_valid: true })}
          isValidating={false}
          onClick={vi.fn()}
        />
      );

      // lucide uses "lucide-circle-check" class
      expect(container.querySelector(".lucide-circle-check")).toBeInTheDocument();
    });

    it("green background with hover effect", () => {
      const { container } = render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({ is_valid: true })}
          isValidating={false}
          onClick={vi.fn()}
        />
      );

      // Component uses div elements with bg-green-500/20 class
      const indicator = container.querySelector("[class*='bg-green-500']");
      expect(indicator).toBeInTheDocument();
    });
  });

  describe("Invalid state", () => {
    it("shows yellow AlertTriangle icon", () => {
      const { container } = render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [createMockMessage({ severity: "error" })],
          })}
          isValidating={false}
          onClick={vi.fn()}
        />
      );

      expect(container.querySelector(".lucide-triangle-alert")).toBeInTheDocument();
    });

    it("yellow background with hover effect", () => {
      const { container } = render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [],
          })}
          isValidating={false}
          onClick={vi.fn()}
        />
      );

      const indicator = container.querySelector("[class*='bg-yellow-500']");
      expect(indicator).toBeInTheDocument();
    });
  });

  describe("Click behavior", () => {
    it("calls onClick handler when clicked", async () => {
      const user = userEvent.setup();
      const onClick = vi.fn();

      const { container } = render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({ is_valid: false })}
          isValidating={false}
          onClick={onClick}
        />
      );

      // Click on the clickable div
      const clickable = container.querySelector(".cursor-pointer");
      if (clickable) {
        await user.click(clickable);
      }
      expect(onClick).toHaveBeenCalled();
    });

    it("stops event propagation to prevent node selection", async () => {
      const user = userEvent.setup();
      const onClick = vi.fn();
      const parentClick = vi.fn();

      const { container } = render(
        <div onClick={parentClick}>
          <NodeValidationIndicator
            validationResult={createMockValidationResult({ is_valid: false })}
            isValidating={false}
            onClick={onClick}
          />
        </div>
      );

      const clickable = container.querySelector(".cursor-pointer");
      if (clickable) {
        await user.click(clickable);
      }
      expect(onClick).toHaveBeenCalled();
      expect(parentClick).not.toHaveBeenCalled();
    });
  });

  describe("Hover effect", () => {
    it("has scale transition class for hover", () => {
      const { container } = render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({ is_valid: true })}
          isValidating={false}
          onClick={vi.fn()}
        />
      );

      const element = container.querySelector("[class*='hover:scale-110']");
      expect(element).toBeInTheDocument();
    });
  });

  describe("Tooltip content", () => {
    it("wraps validating indicator in SimpleTooltip", () => {
      const { container } = render(
        <NodeValidationIndicator isValidating={true} onClick={vi.fn()} />
      );

      // SimpleTooltip adds data-state attribute to trigger element
      const tooltipTrigger = container.querySelector("[data-state]");
      expect(tooltipTrigger).toBeInTheDocument();
    });

    it("wraps valid indicator in SimpleTooltip", () => {
      const { container } = render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({ is_valid: true })}
          isValidating={false}
          onClick={vi.fn()}
        />
      );

      const tooltipTrigger = container.querySelector("[data-state]");
      expect(tooltipTrigger).toBeInTheDocument();
    });

    it("wraps invalid indicator in SimpleTooltip", () => {
      const { container } = render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [
              createMockMessage({ severity: "error" }),
              createMockMessage({ severity: "error" }),
              createMockMessage({ severity: "warning" }),
            ],
          })}
          isValidating={false}
          onClick={vi.fn()}
        />
      );

      const tooltipTrigger = container.querySelector("[data-state]");
      expect(tooltipTrigger).toBeInTheDocument();
    });

    it("tooltip trigger is present for hover interaction", () => {
      const { container } = render(
        <NodeValidationIndicator isValidating={true} onClick={vi.fn()} />
      );

      // Tooltip trigger element with data-state exists
      const indicator = container.querySelector(".p-1[data-state]");
      expect(indicator).toBeInTheDocument();
      // Tooltip content is passed to SimpleTooltip, which handles hover display
    });
  });
});
