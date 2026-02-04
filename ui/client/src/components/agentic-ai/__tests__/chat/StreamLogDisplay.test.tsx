import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { render } from "@/test-utils/render";
import { StreamLogDisplay } from "../../chat/StreamLogDisplay";
import type { Message, StreamLogEntry, WorkPlanSnapshot } from "../../chat/types";

// Mock StreamLogItem
vi.mock("../../chat/StreamLogItem", () => ({
  StreamLogItem: ({ log, messageId, onToggleExpansion }: any) => (
    <div data-testid={`stream-log-item-${log.nodeId}`}>
      <span>Node: {log.nodeName}</span>
      <span>Status: {log.status}</span>
      <button onClick={() => onToggleExpansion(messageId, log.nodeId)}>
        Toggle
      </button>
    </div>
  ),
}));

// Mock WorkPlanDisplay
vi.mock("../../chat/WorkPlanDisplay", () => ({
  WorkPlanDisplay: ({ workPlanSnapshot, messageId, onToggleExpansion }: any) => (
    <div data-testid={`work-plan-display-${workPlanSnapshot.plan_id}`}>
      <span>Plan: {workPlanSnapshot.plan_id}</span>
      <button onClick={() => onToggleExpansion(messageId, workPlanSnapshot.plan_id)}>
        Toggle Plan
      </button>
    </div>
  ),
}));

const createMockMessage = (overrides: Partial<Message> = {}): Message => ({
  id: "msg-1",
  content: "Test message",
  sender: "ai",
  ...overrides,
});

const createMockStreamLog = (overrides: Partial<StreamLogEntry> = {}): StreamLogEntry => ({
  nodeId: "node-1",
  nodeName: "Test Node",
  message: "Processing...",
  tools: [],
  status: "processing",
  isExpanded: false,
  ...overrides,
});

const createMockWorkPlan = (overrides: Partial<WorkPlanSnapshot> = {}): WorkPlanSnapshot => ({
  plan_id: "plan-1",
  action: "create",
  isExpanded: false,
  workplan: {
    summary: "Test workplan",
    items: {},
  },
  ...overrides,
});

describe("StreamLogDisplay", () => {
  describe("Empty state handling", () => {
    it("returns null when both workPlans and streamLogs are empty", () => {
      const message = createMockMessage({ streamLogs: [], workPlans: [] });
      const { container } = render(
        <StreamLogDisplay
          message={message}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      expect(container.firstChild).toBeNull();
    });

    it("returns null when message has no streamLogs or workPlans", () => {
      const message = createMockMessage();
      const { container } = render(
        <StreamLogDisplay
          message={message}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe("Rendering sections", () => {
    it("renders only workPlans section when only workPlans exist", () => {
      const message = createMockMessage({
        workPlans: [createMockWorkPlan()],
        streamLogs: [],
      });

      render(
        <StreamLogDisplay
          message={message}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      expect(screen.getByTestId("work-plan-display-plan-1")).toBeInTheDocument();
      expect(screen.queryByTestId(/stream-log-item/)).not.toBeInTheDocument();
    });

    it("renders only streamLogs section when only streamLogs exist", () => {
      const message = createMockMessage({
        streamLogs: [createMockStreamLog()],
        workPlans: [],
      });

      render(
        <StreamLogDisplay
          message={message}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      expect(screen.getByTestId("stream-log-item-node-1")).toBeInTheDocument();
      expect(screen.queryByTestId(/work-plan-display/)).not.toBeInTheDocument();
    });

    it("renders both sections when both exist", () => {
      const message = createMockMessage({
        streamLogs: [createMockStreamLog()],
        workPlans: [createMockWorkPlan()],
      });

      render(
        <StreamLogDisplay
          message={message}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      expect(screen.getByTestId("stream-log-item-node-1")).toBeInTheDocument();
      expect(screen.getByTestId("work-plan-display-plan-1")).toBeInTheDocument();
    });
  });

  describe("WorkPlans section", () => {
    it("shows 'Execution Timeline' header with Cpu icon", () => {
      const message = createMockMessage({
        workPlans: [createMockWorkPlan()],
      });

      render(
        <StreamLogDisplay
          message={message}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Execution Timeline")).toBeInTheDocument();
    });

    it("renders WorkPlanDisplay for each workplan snapshot", () => {
      const message = createMockMessage({
        workPlans: [
          createMockWorkPlan({ plan_id: "plan-1" }),
          createMockWorkPlan({ plan_id: "plan-2" }),
        ],
      });

      render(
        <StreamLogDisplay
          message={message}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      expect(screen.getByTestId("work-plan-display-plan-1")).toBeInTheDocument();
      expect(screen.getByTestId("work-plan-display-plan-2")).toBeInTheDocument();
    });

    it("passes onToggleExpansion callback correctly", async () => {
      const onToggleWorkPlanExpansion = vi.fn();
      const message = createMockMessage({
        workPlans: [createMockWorkPlan()],
      });

      render(
        <StreamLogDisplay
          message={message}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={onToggleWorkPlanExpansion}
        />
      );

      const toggleButton = screen.getByRole("button", { name: "Toggle Plan" });
      toggleButton.click();

      expect(onToggleWorkPlanExpansion).toHaveBeenCalledWith("msg-1", "plan-1");
    });
  });

  describe("StreamLogs section", () => {
    it("renders StreamLogItem for each stream log entry", () => {
      const message = createMockMessage({
        streamLogs: [
          createMockStreamLog({ nodeId: "node-1", nodeName: "Node One" }),
          createMockStreamLog({ nodeId: "node-2", nodeName: "Node Two" }),
        ],
      });

      render(
        <StreamLogDisplay
          message={message}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      expect(screen.getByTestId("stream-log-item-node-1")).toBeInTheDocument();
      expect(screen.getByTestId("stream-log-item-node-2")).toBeInTheDocument();
    });

    it("passes onToggleExpansion callback correctly", () => {
      const onToggleExpansion = vi.fn();
      const message = createMockMessage({
        streamLogs: [createMockStreamLog()],
      });

      render(
        <StreamLogDisplay
          message={message}
          onToggleExpansion={onToggleExpansion}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      const toggleButton = screen.getByRole("button", { name: "Toggle" });
      toggleButton.click();

      expect(onToggleExpansion).toHaveBeenCalledWith("msg-1", "node-1");
    });
  });

  describe("Re-render optimization (memo)", () => {
    it("re-renders on message ID change", () => {
      const onToggle = vi.fn();
      const message1 = createMockMessage({
        id: "msg-1",
        streamLogs: [createMockStreamLog()],
      });

      const { rerender } = render(
        <StreamLogDisplay
          message={message1}
          onToggleExpansion={onToggle}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      const message2 = createMockMessage({
        id: "msg-2",
        streamLogs: [createMockStreamLog()],
      });

      rerender(
        <StreamLogDisplay
          message={message2}
          onToggleExpansion={onToggle}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      // Component should have re-rendered with new message
      expect(screen.getByTestId("stream-log-item-node-1")).toBeInTheDocument();
    });

    it("re-renders on structural changes in streamLogs (length, nodeId, status, isExpanded)", () => {
      const message1 = createMockMessage({
        streamLogs: [createMockStreamLog({ status: "processing" })],
      });

      const { rerender } = render(
        <StreamLogDisplay
          message={message1}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Status: processing")).toBeInTheDocument();

      const message2 = createMockMessage({
        streamLogs: [createMockStreamLog({ status: "complete" })],
      });

      rerender(
        <StreamLogDisplay
          message={message2}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Status: complete")).toBeInTheDocument();
    });

    it("re-renders on structural changes in workPlans", () => {
      const message1 = createMockMessage({
        workPlans: [createMockWorkPlan({ action: "create" })],
      });

      const { rerender } = render(
        <StreamLogDisplay
          message={message1}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      expect(screen.getByTestId("work-plan-display-plan-1")).toBeInTheDocument();

      const message2 = createMockMessage({
        workPlans: [
          createMockWorkPlan({ plan_id: "plan-1" }),
          createMockWorkPlan({ plan_id: "plan-2" }),
        ],
      });

      rerender(
        <StreamLogDisplay
          message={message2}
          onToggleExpansion={vi.fn()}
          onToggleWorkPlanExpansion={vi.fn()}
        />
      );

      expect(screen.getByTestId("work-plan-display-plan-1")).toBeInTheDocument();
      expect(screen.getByTestId("work-plan-display-plan-2")).toBeInTheDocument();
    });
  });
});
