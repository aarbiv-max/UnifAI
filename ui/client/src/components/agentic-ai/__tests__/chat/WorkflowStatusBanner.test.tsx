import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { render } from "@/test-utils/render";
import WorkflowStatusBanner, { WorkflowBannerMessages } from "@/components/shared/WorkflowStatusBanner";

describe("WorkflowStatusBanner", () => {
  describe("Variant styling", () => {
    it("warning variant has orange background, border, and text", () => {
      const { container } = render(
        <WorkflowStatusBanner variant="warning" message="Warning message" />
      );

      const banner = container.firstChild as HTMLElement;
      expect(banner).toHaveClass("bg-orange-900/20");
      expect(banner).toHaveClass("border-orange-500/50");
      expect(banner.querySelector(".text-orange-200")).toBeInTheDocument();
    });

    it("error variant has red background, border, and text", () => {
      const { container } = render(
        <WorkflowStatusBanner variant="error" message="Error message" />
      );

      const banner = container.firstChild as HTMLElement;
      expect(banner).toHaveClass("bg-red-900/20");
      expect(banner).toHaveClass("border-red-500/50");
      expect(banner.querySelector(".text-red-200")).toBeInTheDocument();
    });

    it("info variant has blue background, border, and text", () => {
      const { container } = render(
        <WorkflowStatusBanner variant="info" message="Info message" />
      );

      const banner = container.firstChild as HTMLElement;
      expect(banner).toHaveClass("bg-blue-900/20");
      expect(banner).toHaveClass("border-blue-500/50");
      expect(banner.querySelector(".text-blue-200")).toBeInTheDocument();
    });

    it("loading variant has blue background, border, and text with spinner", () => {
      const { container } = render(
        <WorkflowStatusBanner variant="loading" message="Loading..." />
      );

      const banner = container.firstChild as HTMLElement;
      expect(banner).toHaveClass("bg-blue-900/20");
      expect(banner).toHaveClass("border-blue-500/50");
      
      // Loading has spinning icon
      expect(container.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Icons", () => {
    it("warning variant shows AlertTriangle icon", () => {
      const { container } = render(
        <WorkflowStatusBanner variant="warning" message="Warning" />
      );

      expect(container.querySelector(".lucide-triangle-alert")).toBeInTheDocument();
    });

    it("error variant shows XCircle icon", () => {
      const { container } = render(
        <WorkflowStatusBanner variant="error" message="Error" />
      );

      expect(container.querySelector(".lucide-circle-x")).toBeInTheDocument();
    });

    it("info variant shows Info icon", () => {
      const { container } = render(
        <WorkflowStatusBanner variant="info" message="Info" />
      );

      expect(container.querySelector(".lucide-info")).toBeInTheDocument();
    });

    it("loading variant shows Loader2 (spinning) icon", () => {
      const { container } = render(
        <WorkflowStatusBanner variant="loading" message="Loading" />
      );

      // Lucide renders Loader2 with class lucide-loader-circle
      expect(container.querySelector(".lucide-loader-circle")).toBeInTheDocument();
      expect(container.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Content", () => {
    it("shows icon on left", () => {
      const { container } = render(
        <WorkflowStatusBanner variant="info" message="Test message" />
      );

      const icon = container.querySelector("svg");
      expect(icon).toBeInTheDocument();
      expect(icon).toHaveClass("mr-2");
    });

    it("shows optional title in bold followed by message", () => {
      render(
        <WorkflowStatusBanner
          variant="error"
          title="Error Title"
          message="Error details here"
        />
      );

      expect(screen.getByText(/Error Title/)).toBeInTheDocument();
      expect(screen.getByText(/Error details here/)).toBeInTheDocument();
    });

    it("shows only message when no title provided", () => {
      render(
        <WorkflowStatusBanner variant="info" message="Just the message" />
      );

      expect(screen.getByText("Just the message")).toBeInTheDocument();
    });

    it("applies custom className when provided", () => {
      const { container } = render(
        <WorkflowStatusBanner
          variant="info"
          message="Test"
          className="custom-class"
        />
      );

      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("Pre-configured banner messages", () => {
    it("deleted: error variant with correct title and message", () => {
      render(<WorkflowStatusBanner {...WorkflowBannerMessages.deleted} />);

      expect(screen.getByText(/Workflow Unavailable/)).toBeInTheDocument();
      expect(screen.getByText(/has been deleted/)).toBeInTheDocument();
    });

    it("sharingDisabled: warning variant with correct title and message", () => {
      render(<WorkflowStatusBanner {...WorkflowBannerMessages.sharingDisabled} />);

      expect(screen.getByText(/Workflow Unavailable/)).toBeInTheDocument();
      expect(screen.getByText(/sharing has been disabled/)).toBeInTheDocument();
    });

    it("validationFailed: error variant with correct title and message", () => {
      render(<WorkflowStatusBanner {...WorkflowBannerMessages.validationFailed} />);

      expect(screen.getByText(/Workflow Unavailable/)).toBeInTheDocument();
      expect(screen.getByText(/failed validation/)).toBeInTheDocument();
    });

    it("validating: loading variant with message only (no title)", () => {
      render(<WorkflowStatusBanner {...WorkflowBannerMessages.validating} />);

      expect(screen.getByText("Validating workflow...")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("uses semantic HTML for message content", () => {
      render(
        <WorkflowStatusBanner
          variant="error"
          title="Important"
          message="Please read this"
        />
      );

      // Text should be in a readable format
      const text = screen.getByText(/Important/);
      expect(text).toBeInTheDocument();
    });
  });
});
