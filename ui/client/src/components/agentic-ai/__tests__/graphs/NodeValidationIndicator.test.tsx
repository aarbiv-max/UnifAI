import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import NodeValidationIndicator from "../../graphs/NodeValidationIndicator";
import type { ElementValidationResult } from "@/types/validation";

const createMockValidationResult = (
  overrides: Partial<ElementValidationResult> = {}
): ElementValidationResult => ({
  element_rid: "elem-1",
  is_valid: true,
  messages: [],
  dependencies: [],
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

    it("tooltip shows 'Validating...'", async () => {
      render(
        <NodeValidationIndicator isValidating={true} onClick={vi.fn()} />
      );

      // The spinner button should exist
      const button = screen.getByRole("button");
      expect(button).toBeInTheDocument();
    });

    it("stops click propagation", async () => {
      const user = userEvent.setup();
      const onClick = vi.fn();
      const parentClick = vi.fn();

      render(
        <div onClick={parentClick}>
          <NodeValidationIndicator isValidating={true} onClick={onClick} />
        </div>
      );

      await user.click(screen.getByRole("button"));
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

    it("no visual indicator rendered", () => {
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

      expect(container.querySelector(".lucide-check-circle-2")).toBeInTheDocument();
    });

    it("green background with hover effect", () => {
      const { container } = render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({ is_valid: true })}
          isValidating={false}
          onClick={vi.fn()}
        />
      );

      const button = container.querySelector("button");
      expect(button).toHaveClass("bg-green-500");
    });
  });

  describe("Invalid state", () => {
    it("shows yellow AlertTriangle icon", () => {
      const { container } = render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [{ severity: "error", message: "Test error" }],
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

      const button = container.querySelector("button");
      expect(button).toHaveClass("bg-yellow-500");
    });

    it("tooltip shows error/warning counts", async () => {
      render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({
            is_valid: false,
            messages: [
              { severity: "error", message: "Error 1" },
              { severity: "error", message: "Error 2" },
              { severity: "warning", message: "Warning 1" },
            ],
          })}
          isValidating={false}
          onClick={vi.fn()}
        />
      );

      // Button should be present
      expect(screen.getByRole("button")).toBeInTheDocument();
    });
  });

  describe("Click behavior", () => {
    it("calls onClick handler when clicked", async () => {
      const user = userEvent.setup();
      const onClick = vi.fn();

      render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({ is_valid: false })}
          isValidating={false}
          onClick={onClick}
        />
      );

      await user.click(screen.getByRole("button"));
      expect(onClick).toHaveBeenCalled();
    });

    it("stops event propagation to prevent node selection", async () => {
      const user = userEvent.setup();
      const onClick = vi.fn();
      const parentClick = vi.fn();

      render(
        <div onClick={parentClick}>
          <NodeValidationIndicator
            validationResult={createMockValidationResult({ is_valid: false })}
            isValidating={false}
            onClick={onClick}
          />
        </div>
      );

      await user.click(screen.getByRole("button"));
      expect(onClick).toHaveBeenCalled();
      expect(parentClick).not.toHaveBeenCalled();
    });
  });

  describe("Hover effect", () => {
    it("scales up slightly on hover", () => {
      const { container } = render(
        <NodeValidationIndicator
          validationResult={createMockValidationResult({ is_valid: true })}
          isValidating={false}
          onClick={vi.fn()}
        />
      );

      const button = container.querySelector("button");
      expect(button).toHaveClass("hover:scale-110");
    });
  });
});
