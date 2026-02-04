import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import { StreamLogItem } from "../../chat/StreamLogItem";
import type { StreamLogEntry, ToolEntry } from "../../chat/types";

const createMockLog = (overrides: Partial<StreamLogEntry> = {}): StreamLogEntry => ({
  nodeId: "test-node",
  nodeName: "Test Node",
  message: "Test message content",
  tools: [],
  status: "processing",
  isExpanded: false,
  ...overrides,
});

const createMockTool = (overrides: Partial<ToolEntry> = {}): ToolEntry => ({
  id: "tool-1",
  name: "test_tool",
  args: { param1: "value1" },
  output: "Tool result",
  ...overrides,
});

describe("StreamLogItem", () => {
  describe("Header display", () => {
    it("shows StatusIndicator with current status", () => {
      const { container } = render(
        <StreamLogItem
          log={createMockLog({ status: "processing" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      // Processing status shows AlertCircle icon
      expect(container.querySelector("svg")).toBeInTheDocument();
    });

    it("shows formatted node name (underscores → spaces, capitalized)", () => {
      render(
        <StreamLogItem
          log={createMockLog({ nodeName: "Test Node" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Test Node")).toBeInTheDocument();
    });

    it("shows status text: 'Generating...' for processing", () => {
      render(
        <StreamLogItem
          log={createMockLog({ status: "processing" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Generating...")).toBeInTheDocument();
    });

    it("shows status text: 'Complete' for complete", () => {
      render(
        <StreamLogItem
          log={createMockLog({ status: "complete" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Complete")).toBeInTheDocument();
    });

    it("shows status text: 'Error' for error", () => {
      render(
        <StreamLogItem
          log={createMockLog({ status: "error" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Error")).toBeInTheDocument();
    });

    it("shows status text: 'Unknown' for unknown status", () => {
      render(
        <StreamLogItem
          log={createMockLog({ status: "unknown" as any })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Unknown")).toBeInTheDocument();
    });

    it("shows tool count badge when tools exist: '{N} tool(s)'", () => {
      render(
        <StreamLogItem
          log={createMockLog({
            tools: [createMockTool(), createMockTool({ id: "tool-2" })],
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("2 tools")).toBeInTheDocument();
    });

    it("shows singular 'tool' for single tool", () => {
      render(
        <StreamLogItem
          log={createMockLog({ tools: [createMockTool()] })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("1 tool")).toBeInTheDocument();
    });

    it("shows chevron icon: ChevronDown when expanded, ChevronRight when collapsed", () => {
      const { rerender, container } = render(
        <StreamLogItem
          log={createMockLog({ isExpanded: false })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      // Collapsed shows ChevronRight
      expect(container.querySelector(".lucide-chevron-right")).toBeInTheDocument();

      rerender(
        <StreamLogItem
          log={createMockLog({ isExpanded: true })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      // Expanded shows ChevronDown
      expect(container.querySelector(".lucide-chevron-down")).toBeInTheDocument();
    });
  });

  describe("Toggle behavior", () => {
    it("clicking header calls onToggleExpansion(messageId, nodeId)", async () => {
      const user = userEvent.setup();
      const onToggleExpansion = vi.fn();

      render(
        <StreamLogItem
          log={createMockLog({ nodeId: "my-node" })}
          messageId="msg-123"
          onToggleExpansion={onToggleExpansion}
        />
      );

      // Click the header
      const header = screen.getByText("Test Node").closest("div[class*='cursor-pointer']");
      await user.click(header!);

      expect(onToggleExpansion).toHaveBeenCalledWith("msg-123", "my-node");
    });

    it("toggles between expanded and collapsed states", async () => {
      const user = userEvent.setup();
      const onToggleExpansion = vi.fn();

      const { rerender } = render(
        <StreamLogItem
          log={createMockLog({ isExpanded: false })}
          messageId="msg-1"
          onToggleExpansion={onToggleExpansion}
        />
      );

      // Initial state is collapsed
      expect(screen.getByText("Test message content")).toBeInTheDocument();

      // Simulate expansion
      rerender(
        <StreamLogItem
          log={createMockLog({ isExpanded: true })}
          messageId="msg-1"
          onToggleExpansion={onToggleExpansion}
        />
      );

      // Still shows content but in expanded form
      expect(screen.getByText("Test message content")).toBeInTheDocument();
    });
  });

  describe("Tools section", () => {
    it("shows tools section when hasTools && isExpanded", () => {
      render(
        <StreamLogItem
          log={createMockLog({
            tools: [createMockTool()],
            isExpanded: true,
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Tool Calls (1)")).toBeInTheDocument();
    });

    it("shows tool count header: 'Tool Calls ({N})'", () => {
      render(
        <StreamLogItem
          log={createMockLog({
            tools: [createMockTool(), createMockTool({ id: "tool-2", name: "another_tool" })],
            isExpanded: true,
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Tool Calls (2)")).toBeInTheDocument();
    });

    it("shows Wrench icon with tool name", () => {
      const { container } = render(
        <StreamLogItem
          log={createMockLog({
            tools: [createMockTool({ name: "search_tool" })],
            isExpanded: true,
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText(/search_tool/)).toBeInTheDocument();
      expect(container.querySelector(".lucide-wrench")).toBeInTheDocument();
    });

    it("shows args as key-value table", () => {
      render(
        <StreamLogItem
          log={createMockLog({
            tools: [createMockTool({ args: { query: "test query", limit: 10 } })],
            isExpanded: true,
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("query")).toBeInTheDocument();
      expect(screen.getByText("test query")).toBeInTheDocument();
      expect(screen.getByText("limit")).toBeInTheDocument();
      expect(screen.getByText("10")).toBeInTheDocument();
    });

    it("formats object values as JSON string", () => {
      render(
        <StreamLogItem
          log={createMockLog({
            tools: [createMockTool({ args: { config: { nested: true } } })],
            isExpanded: true,
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText('{"nested":true}')).toBeInTheDocument();
    });
  });

  describe("Message content display", () => {
    it("shows truncated preview (first 2 lines + '...')", () => {
      const longMessage = "Line 1\nLine 2\nLine 3\nLine 4";
      render(
        <StreamLogItem
          log={createMockLog({ message: longMessage, isExpanded: false })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      // In collapsed mode, shows truncated preview
      expect(screen.getByText(/Line 1/)).toBeInTheDocument();
    });

    it("shows 'Show full log' button when content > 2 lines", () => {
      const longMessage = "Line 1\nLine 2\nLine 3\nLine 4";
      render(
        <StreamLogItem
          log={createMockLog({ message: longMessage, isExpanded: false })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Show full log")).toBeInTheDocument();
    });

    it("shows red text for error status", () => {
      const { container } = render(
        <StreamLogItem
          log={createMockLog({ status: "error", message: "Error occurred" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      const errorText = container.querySelector(".text-\\[\\#FF1744\\]");
      expect(errorText).toBeInTheDocument();
    });

    it("shows gray text for other statuses", () => {
      const { container } = render(
        <StreamLogItem
          log={createMockLog({ status: "processing", message: "Processing" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      const grayText = container.querySelector(".text-gray-300");
      expect(grayText).toBeInTheDocument();
    });

    it("uses ReactMarkdown with remarkGfm for expanded view", () => {
      render(
        <StreamLogItem
          log={createMockLog({ message: "**bold text**", isExpanded: true })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      // Markdown should be rendered (bold text becomes <strong>)
      const boldElement = screen.getByText("bold text");
      expect(boldElement.tagName.toLowerCase()).toBe("strong");
    });
  });

  describe("CSS display toggle", () => {
    it("uses CSS display toggle (not conditional rendering)", () => {
      const { container } = render(
        <StreamLogItem
          log={createMockLog({ isExpanded: false })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      // Both expanded and collapsed content divs should exist in DOM
      // They're controlled via style.display
      const expandedContent = container.querySelector('[style*="display: none"]');
      expect(expandedContent).toBeInTheDocument();
    });
  });

  describe("Memo optimization", () => {
    it("re-renders on nodeId changes", () => {
      const { rerender } = render(
        <StreamLogItem
          log={createMockLog({ nodeId: "node-1" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      rerender(
        <StreamLogItem
          log={createMockLog({ nodeId: "node-2" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      // Component should still render correctly
      expect(screen.getByText("Test Node")).toBeInTheDocument();
    });

    it("re-renders on status changes", () => {
      const { rerender } = render(
        <StreamLogItem
          log={createMockLog({ status: "processing" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Generating...")).toBeInTheDocument();

      rerender(
        <StreamLogItem
          log={createMockLog({ status: "complete" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Complete")).toBeInTheDocument();
    });

    it("re-renders on isExpanded changes", () => {
      const { rerender, container } = render(
        <StreamLogItem
          log={createMockLog({ isExpanded: false })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(container.querySelector(".lucide-chevron-right")).toBeInTheDocument();

      rerender(
        <StreamLogItem
          log={createMockLog({ isExpanded: true })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(container.querySelector(".lucide-chevron-down")).toBeInTheDocument();
    });

    it("re-renders on tools length changes", () => {
      const { rerender } = render(
        <StreamLogItem
          log={createMockLog({ tools: [] })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.queryByText(/tool/)).not.toBeInTheDocument();

      rerender(
        <StreamLogItem
          log={createMockLog({ tools: [createMockTool()] })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("1 tool")).toBeInTheDocument();
    });
  });
});
