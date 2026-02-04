import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StreamingDataProvider, useStreamingData } from "../StreamingDataContext";
import { render } from "@/test-utils/render";
import type { NodeEntry } from "../StreamingDataContext";

const TestConsumer = () => {
  const { nodeListRef, forceUpdate, clearStream } = useStreamingData();

  return (
    <div>
      <span data-testid="count">{nodeListRef.current.size}</span>
      <button
        type="button"
        onClick={() => {
          nodeListRef.current.set("node-1", { id: "node-1" } as unknown as NodeEntry);
          forceUpdate();
        }}
      >
        Add
      </button>
      <button type="button" onClick={clearStream}>
        Clear
      </button>
      <button
        type="button"
        onClick={() => {
          nodeListRef.current.set("node-2", { id: "node-2" } as unknown as NodeEntry);
          nodeListRef.current.set("node-3", { id: "node-3" } as unknown as NodeEntry);
          forceUpdate();
        }}
      >
        Add Multiple
      </button>
    </div>
  );
};

describe("StreamingDataContext", () => {
  describe("Provider initialization", () => {
    it("creates nodeListRef as useRef<Map<string, NodeEntry>>(new Map())", () => {
      render(
        <StreamingDataProvider>
          <TestConsumer />
        </StreamingDataProvider>,
      );

      expect(screen.getByTestId("count")).toHaveTextContent("0");
    });

    it("creates tick state for force updates", async () => {
      const user = userEvent.setup();

      render(
        <StreamingDataProvider>
          <TestConsumer />
        </StreamingDataProvider>,
      );

      // Add a node and verify the re-render happens via forceUpdate
      await user.click(screen.getByRole("button", { name: "Add" }));
      expect(screen.getByTestId("count")).toHaveTextContent("1");
    });
  });

  describe("Context values", () => {
    it("provides nodeListRef: ref to Map of node entries", () => {
      render(
        <StreamingDataProvider>
          <TestConsumer />
        </StreamingDataProvider>,
      );

      // Initially empty map
      expect(screen.getByTestId("count")).toHaveTextContent("0");
    });

    it("provides forceUpdate: increments tick to trigger re-render", async () => {
      const user = userEvent.setup();

      render(
        <StreamingDataProvider>
          <TestConsumer />
        </StreamingDataProvider>,
      );

      expect(screen.getByTestId("count")).toHaveTextContent("0");

      await user.click(screen.getByRole("button", { name: "Add" }));
      expect(screen.getByTestId("count")).toHaveTextContent("1");
    });

    it("provides clearStream: clears map and forces update", async () => {
      const user = userEvent.setup();

      render(
        <StreamingDataProvider>
          <TestConsumer />
        </StreamingDataProvider>,
      );

      // Add some nodes
      await user.click(screen.getByRole("button", { name: "Add Multiple" }));
      expect(screen.getByTestId("count")).toHaveTextContent("2");

      // Clear the stream
      await user.click(screen.getByRole("button", { name: "Clear" }));
      expect(screen.getByTestId("count")).toHaveTextContent("0");
    });
  });

  describe("useStreamingData hook", () => {
    it("throws error if used outside provider", () => {
      const ConsumerOutside = () => {
        useStreamingData();
        return <div>Outside</div>;
      };

      expect(() => render(<ConsumerOutside />)).toThrow(
        "useStreamingData must be used within a StreamingDataProvider",
      );
    });

    it("returns context with all three values", () => {
      let contextValues: ReturnType<typeof useStreamingData> | null = null;

      const InspectConsumer = () => {
        contextValues = useStreamingData();
        return <div>Inspecting</div>;
      };

      render(
        <StreamingDataProvider>
          <InspectConsumer />
        </StreamingDataProvider>,
      );

      expect(contextValues).not.toBeNull();
      expect(contextValues).toHaveProperty("nodeListRef");
      expect(contextValues).toHaveProperty("forceUpdate");
      expect(contextValues).toHaveProperty("clearStream");
      expect(typeof contextValues!.forceUpdate).toBe("function");
      expect(typeof contextValues!.clearStream).toBe("function");
    });
  });

  describe("State updates", () => {
    it("initializes with defaults and updates on changes", async () => {
      const user = userEvent.setup();

      render(
        <StreamingDataProvider>
          <TestConsumer />
        </StreamingDataProvider>,
      );

      expect(screen.getByTestId("count")).toHaveTextContent("0");

      await user.click(screen.getByRole("button", { name: "Add" }));
      expect(screen.getByTestId("count")).toHaveTextContent("1");

      await user.click(screen.getByRole("button", { name: "Clear" }));
      expect(screen.getByTestId("count")).toHaveTextContent("0");
    });

    it("handles multiple nodes correctly", async () => {
      const user = userEvent.setup();

      render(
        <StreamingDataProvider>
          <TestConsumer />
        </StreamingDataProvider>,
      );

      await user.click(screen.getByRole("button", { name: "Add Multiple" }));
      expect(screen.getByTestId("count")).toHaveTextContent("2");
    });
  });

  describe("NodeEntry imported from ./chat/types", () => {
    it("nodeListRef stores NodeEntry objects correctly", async () => {
      const user = userEvent.setup();
      let capturedRef: React.MutableRefObject<Map<string, NodeEntry>> | null = null;

      const CaptureConsumer = () => {
        const { nodeListRef, forceUpdate } = useStreamingData();
        capturedRef = nodeListRef;
        
        return (
          <button
            type="button"
            onClick={() => {
              nodeListRef.current.set("test-node", {
                node_uid: "test-uid",
                node_name: "Test Node",
                stream: "PROGRESS",
                text: "Processing...",
                tools: [],
                workplans: [],
              } as NodeEntry);
              forceUpdate();
            }}
          >
            Add Node Entry
          </button>
        );
      };

      render(
        <StreamingDataProvider>
          <CaptureConsumer />
        </StreamingDataProvider>,
      );

      await user.click(screen.getByRole("button", { name: "Add Node Entry" }));
      
      expect(capturedRef).not.toBeNull();
      expect(capturedRef!.current.has("test-node")).toBe(true);
      
      const entry = capturedRef!.current.get("test-node");
      expect(entry?.node_uid).toBe("test-uid");
      expect(entry?.node_name).toBe("Test Node");
      expect(entry?.stream).toBe("PROGRESS");
    });
  });
});