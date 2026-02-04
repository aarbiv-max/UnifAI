import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { render } from "@/test-utils/render";
import { StatusIndicator } from "../../chat/StatusIndicator";

describe("StatusIndicator", () => {
  describe("Status visuals", () => {
    it("shows rotating AlertCircle icon (yellow #FFB300) for 'processing' status", () => {
      const { container } = render(<StatusIndicator status="processing" />);

      // Should have the AlertCircle icon with yellow color
      const icon = container.querySelector("svg");
      expect(icon).toBeInTheDocument();
      expect(icon).toHaveClass("text-[#FFB300]");
    });

    it("shows green circle (#00E676) for 'complete' status", () => {
      const { container } = render(<StatusIndicator status="complete" />);

      const circle = container.querySelector("div");
      expect(circle).toHaveClass("bg-[#00E676]");
      expect(circle).toHaveClass("rounded-full");
    });

    it("shows red circle (#FF1744) for 'error' status", () => {
      const { container } = render(<StatusIndicator status="error" />);

      const circle = container.querySelector("div");
      expect(circle).toHaveClass("bg-[#FF1744]");
      expect(circle).toHaveClass("rounded-full");
    });

    it("shows gray circle for default/unknown status", () => {
      const { container } = render(<StatusIndicator status="unknown" />);

      const circle = container.querySelector("div");
      expect(circle).toHaveClass("bg-gray-400");
      expect(circle).toHaveClass("rounded-full");
    });
  });

  describe("Animation", () => {
    it("processing status has rotate animation via framer-motion", () => {
      const { container } = render(<StatusIndicator status="processing" />);

      // The motion.div wrapper should exist for processing status
      const motionWrapper = container.querySelector("div.inline-block");
      expect(motionWrapper).toBeInTheDocument();
    });
  });

  describe("Size consistency", () => {
    it("all status indicators have consistent sizing (w-3 h-3)", () => {
      // Complete status
      const { container: completeContainer } = render(<StatusIndicator status="complete" />);
      const completeCircle = completeContainer.querySelector("div");
      expect(completeCircle).toHaveClass("w-3", "h-3");

      // Error status
      const { container: errorContainer } = render(<StatusIndicator status="error" />);
      const errorCircle = errorContainer.querySelector("div");
      expect(errorCircle).toHaveClass("w-3", "h-3");

      // Default status
      const { container: defaultContainer } = render(<StatusIndicator status="default" />);
      const defaultCircle = defaultContainer.querySelector("div");
      expect(defaultCircle).toHaveClass("w-3", "h-3");
    });

    it("processing icon has h-3 w-3 sizing", () => {
      const { container } = render(<StatusIndicator status="processing" />);
      const icon = container.querySelector("svg");
      expect(icon).toHaveClass("h-3", "w-3");
    });
  });
});
