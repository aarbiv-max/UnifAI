import { describe, it, expect } from "vitest";
import { getStatusConfig, formatTimestamp } from "../../chat/WorkPlanDisplayHelpers";
import { CheckCircle2, Circle, Clock, AlertCircle } from "lucide-react";

describe("WorkPlanDisplayHelpers", () => {
  describe("getStatusConfig", () => {
    it("returns correct config for 'done' status", () => {
      const config = getStatusConfig("done");

      expect(config.icon).toBe(CheckCircle2);
      expect(config.color).toBe("text-green-400");
      expect(config.bgColor).toBe("bg-green-400/10");
      expect(config.borderColor).toBe("border-green-400/30");
    });

    it("returns correct config for 'in_progress' status", () => {
      const config = getStatusConfig("in_progress");

      expect(config.icon).toBe(Clock);
      expect(config.color).toBe("text-blue-400");
      expect(config.bgColor).toBe("bg-blue-400/10");
      expect(config.borderColor).toBe("border-blue-400/30");
    });

    it("returns correct config for 'failed' status", () => {
      const config = getStatusConfig("failed");

      expect(config.icon).toBe(AlertCircle);
      expect(config.color).toBe("text-red-400");
      expect(config.bgColor).toBe("bg-red-400/10");
      expect(config.borderColor).toBe("border-red-400/30");
    });

    it("returns correct config for default/pending status", () => {
      const config = getStatusConfig("pending");

      expect(config.icon).toBe(Circle);
      expect(config.color).toBe("text-gray-400");
      expect(config.bgColor).toBe("bg-gray-400/10");
      expect(config.borderColor).toBe("border-gray-400/30");
    });

    it("returns default config for unknown status", () => {
      const config = getStatusConfig("unknown_status");

      expect(config.icon).toBe(Circle);
      expect(config.color).toBe("text-gray-400");
      expect(config.bgColor).toBe("bg-gray-400/10");
      expect(config.borderColor).toBe("border-gray-400/30");
    });

    it("returns default config for empty string", () => {
      const config = getStatusConfig("");

      expect(config.icon).toBe(Circle);
      expect(config.color).toBe("text-gray-400");
    });
  });

  describe("formatTimestamp", () => {
    it("formats ISO timestamp to time format", () => {
      // Create a specific date/time
      const timestamp = "2024-01-15T14:30:45.000Z";
      const result = formatTimestamp(timestamp);

      // The result should contain HH:MM:SS pattern (may include AM/PM based on locale)
      expect(result).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });

    it("uses toLocaleTimeString with hour, minute, second", () => {
      const timestamp = "2024-06-20T09:05:03.000Z";
      const result = formatTimestamp(timestamp);

      // Should be formatted with hours, minutes, and seconds
      expect(result).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });

    it("handles different timestamp formats", () => {
      // ISO format with milliseconds
      const timestamp1 = "2024-03-10T12:00:00.123Z";
      expect(formatTimestamp(timestamp1)).toMatch(/\d{1,2}:\d{2}:\d{2}/);

      // ISO format without milliseconds
      const timestamp2 = "2024-03-10T12:00:00Z";
      expect(formatTimestamp(timestamp2)).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });

    it("handles timestamps at midnight", () => {
      const timestamp = "2024-01-01T00:00:00.000Z";
      const result = formatTimestamp(timestamp);

      // Should still produce valid time format
      expect(result).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });

    it("handles timestamps at noon", () => {
      const timestamp = "2024-01-01T12:00:00.000Z";
      const result = formatTimestamp(timestamp);

      expect(result).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });
  });

  describe("Status config table validation", () => {
    const statusTable = [
      { status: "done", expectedIcon: CheckCircle2, expectedColor: "text-green-400" },
      { status: "in_progress", expectedIcon: Clock, expectedColor: "text-blue-400" },
      { status: "failed", expectedIcon: AlertCircle, expectedColor: "text-red-400" },
      { status: "pending", expectedIcon: Circle, expectedColor: "text-gray-400" },
    ];

    statusTable.forEach(({ status, expectedIcon, expectedColor }) => {
      it(`status '${status}' has correct icon and color`, () => {
        const config = getStatusConfig(status);
        expect(config.icon).toBe(expectedIcon);
        expect(config.color).toBe(expectedColor);
      });
    });
  });
});
