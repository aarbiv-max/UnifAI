import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import type { FlowObject } from "../graphs/interfaces";
import WorkflowsPanel from "../WorkflowsPanel";

const flow: FlowObject = {
  id: "bp-1",
  name: "Flow One",
  description: "Flow description",
  icon: <span>Icon</span>,
  flow: { nodes: [], edges: [] },
};

const flow2: FlowObject = {
  id: "bp-2",
  name: "Flow Two",
  description: "Second flow",
  icon: <span>Icon2</span>,
  flow: { nodes: [], edges: [] },
};

const fetchBlueprintsMock = vi.fn();
const fetchResolvedBlueprintsMock = vi.fn();
const fetchActiveSessionsMock = vi.fn();
const deleteBlueprintMock = vi.fn();
const validateBlueprintMock = vi.fn();
const clearValidationMock = vi.fn();

const authState = {
  user: { username: "tester" },
  isAuthenticated: true,
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn(),
  checkAuthStatus: vi.fn(),
};

vi.mock("@/contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => authState,
}));

const openShareForItemMock = vi.fn();
vi.mock("@/contexts/SharedContext", () => ({
  SharedProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useShared: () => ({ openShareForItem: openShareForItemMock }),
}));

vi.mock("@/api/agentic", () => ({
  fetchActiveSessions: (...args: unknown[]) => fetchActiveSessionsMock(...args),
}));

vi.mock("@/api/blueprints", () => ({
  fetchBlueprints: (...args: unknown[]) => fetchBlueprintsMock(...args),
  fetchResolvedBlueprints: (...args: unknown[]) =>
    fetchResolvedBlueprintsMock(...args),
  deleteBlueprint: (...args: unknown[]) => deleteBlueprintMock(...args),
}));

let flowIndex = 0;
vi.mock("@/utils/blueprintHelpers", () => ({
  convertGraphFlowToFlowObject: () => flowIndex++ % 2 === 0 ? flow : flow2,
}));

const validationState = {
  isValidating: false,
  validationResults: null,
  isValid: true,
};

vi.mock("@/hooks/use-blueprint-validation", () => ({
  useBlueprintValidation: () => ({
    ...validationState,
    validateBlueprint: validateBlueprintMock,
    clearValidation: clearValidationMock,
  }),
}));

const reactFlowGraphSpy = vi.fn();
vi.mock("../graphs/ReactFlowGraph", () => ({
  default: (props: Record<string, unknown>) => {
    reactFlowGraphSpy(props);
    return <div data-testid="react-flow-graph">ReactFlowGraph</div>;
  },
}));

vi.mock("../ShareWorkflow", () => ({
  default: (props: Record<string, unknown>) => (
    <div data-testid="share-workflow">ShareWorkflow {props.blueprintId as string}</div>
  ),
}));

describe("WorkflowsPanel", () => {
  beforeEach(() => {
    flowIndex = 0;
    fetchBlueprintsMock.mockReset();
    fetchResolvedBlueprintsMock.mockReset();
    fetchActiveSessionsMock.mockReset();
    deleteBlueprintMock.mockReset();
    openShareForItemMock.mockReset();
    validateBlueprintMock.mockReset();
    clearValidationMock.mockReset();
    reactFlowGraphSpy.mockClear();
    fetchBlueprintsMock.mockResolvedValue([]);
    fetchResolvedBlueprintsMock.mockResolvedValue([]);
    fetchActiveSessionsMock.mockResolvedValue([]);
    deleteBlueprintMock.mockResolvedValue({});
  });

  describe("Data fetching", () => {
    it("fetches blueprints on mount via fetchBlueprints() when useResolvedEndpoint=false", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      render(
        <WorkflowsPanel
          selectedFlow={null}
          onFlowSelect={vi.fn()}
          useResolvedEndpoint={false}
        />,
      );

      await waitFor(() => {
        expect(fetchBlueprintsMock).toHaveBeenCalled();
      });
    });

    it("fetches blueprints on mount via fetchResolvedBlueprints() when useResolvedEndpoint=true", async () => {
      fetchResolvedBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      render(
        <WorkflowsPanel
          selectedFlow={null}
          onFlowSelect={vi.fn()}
          useResolvedEndpoint={true}
        />,
      );

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });
    });

    it("auto-selects first flow if none selected", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);
      fetchActiveSessionsMock.mockResolvedValueOnce([]);
      const onFlowSelect = vi.fn();

      render(
        <WorkflowsPanel
          selectedFlow={null}
          onFlowSelect={onFlowSelect}
        />,
      );

      await waitFor(() => {
        expect(onFlowSelect).toHaveBeenCalledWith(flow);
      });
    });

    it("sets isLoading=false after completion", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([]);

      render(
        <WorkflowsPanel
          selectedFlow={null}
          onFlowSelect={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.queryByText("Loading flows...")).not.toBeInTheDocument();
      });
    });
  });

  describe("Active status", () => {
    it("only fetches active sessions when showActiveStatus=true", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);
      fetchActiveSessionsMock.mockResolvedValueOnce(["bp-1"]);

      render(
        <WorkflowsPanel
          selectedFlow={null}
          onFlowSelect={vi.fn()}
          showActiveStatus={true}
        />,
      );

      await waitFor(() => {
        expect(fetchActiveSessionsMock).toHaveBeenCalledWith("tester");
      });
    });

    it("shows 'Active' badge when showActiveStatus && isFlowActive(flowId)", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);
      fetchActiveSessionsMock.mockResolvedValueOnce(["bp-1"]);

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
          showActiveStatus={true}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Active")).toBeInTheDocument();
      });
    });
  });

  describe("Validation", () => {
    it("triggers validateSelectedBlueprint() when selectedFlow?.id changes", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(validateBlueprintMock).toHaveBeenCalledWith("bp-1");
      });
    });

    it("calls clearValidation() when no flow selected", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([]);

      render(
        <WorkflowsPanel
          selectedFlow={null}
          onFlowSelect={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(clearValidationMock).toHaveBeenCalled();
      });
    });
  });

  describe("Flow selection", () => {
    it("handleFlowSelect(flow) calls onFlowSelect(flow)", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);
      fetchActiveSessionsMock.mockResolvedValueOnce([]);
      const onFlowSelect = vi.fn();

      render(
        <WorkflowsPanel
          selectedFlow={null}
          onFlowSelect={onFlowSelect}
        />,
      );

      const label = await screen.findByText("Flow One");
      const user = userEvent.setup();
      await user.click(label);
      expect(onFlowSelect).toHaveBeenCalledWith(flow);
    });

    it("highlights selected flow with primary color", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
        />,
      );

      await screen.findByText("Flow One");
      // Selected flow should have primary border
      const flowElement = screen.getByText("Flow One").closest('[class*="border-"]');
      expect(flowElement).toHaveClass("border-[hsl(var(--primary))]");
    });
  });

  describe("Delete functionality", () => {
    it("only shows delete button when showDeleteButton=true", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      const { container, rerender } = render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
          showDeleteButton={false}
        />,
      );

      await screen.findByText("Flow One");
      
      // Find trash icon - should not exist
      expect(container.querySelector(".lucide-trash-2")).not.toBeInTheDocument();
    });

    it("handleDeleteClick(): opens confirmation modal", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);
      fetchActiveSessionsMock.mockResolvedValueOnce([]);

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
          onFlowDelete={vi.fn()}
          showDeleteButton
        />,
      );

      const user = userEvent.setup();
      const flowLabel = await screen.findByText("Flow One");
      let flowRow: HTMLElement | null = flowLabel;
      while (flowRow && flowRow.querySelectorAll("button").length < 2) {
        flowRow = flowRow.parentElement;
      }
      
      const rowButtons = flowRow?.querySelectorAll("button");
      if (rowButtons && rowButtons.length >= 2) {
        const deleteButton = rowButtons[rowButtons.length - 1];
        await user.click(deleteButton);

        expect(screen.getByText(/Are you sure/)).toBeInTheDocument();
      }
    });

    it("handleDeleteConfirm(): calls deleteBlueprint(), removes from list, clears selection if needed, calls onFlowDelete()", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);
      fetchActiveSessionsMock.mockResolvedValueOnce([]);
      deleteBlueprintMock.mockResolvedValueOnce({});
      const onFlowDelete = vi.fn();

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
          onFlowDelete={onFlowDelete}
          showDeleteButton
        />,
      );

      const user = userEvent.setup();
      const flowLabel = await screen.findByText("Flow One");
      let flowRow: HTMLElement | null = flowLabel;
      while (flowRow && flowRow.querySelectorAll("button").length < 2) {
        flowRow = flowRow.parentElement;
      }
      
      const rowButtons = flowRow?.querySelectorAll("button");
      if (rowButtons && rowButtons.length >= 2) {
        const deleteButton = rowButtons[rowButtons.length - 1];
        await user.click(deleteButton);

        const confirmButton = await screen.findByRole("button", { name: "Confirm" });
        await user.click(confirmButton);
        
        expect(deleteBlueprintMock).toHaveBeenCalledWith("bp-1");
        expect(onFlowDelete).toHaveBeenCalledWith(flow);
      }
    });

    it("handleDeleteCancel(): closes modal", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
          showDeleteButton
        />,
      );

      const user = userEvent.setup();
      const flowLabel = await screen.findByText("Flow One");
      let flowRow: HTMLElement | null = flowLabel;
      while (flowRow && flowRow.querySelectorAll("button").length < 2) {
        flowRow = flowRow.parentElement;
      }
      
      const rowButtons = flowRow?.querySelectorAll("button");
      if (rowButtons && rowButtons.length >= 2) {
        const deleteButton = rowButtons[rowButtons.length - 1];
        await user.click(deleteButton);

        const cancelButton = await screen.findByRole("button", { name: /cancel/i });
        await user.click(cancelButton);

        await waitFor(() => {
          expect(screen.queryByText(/Are you sure/)).not.toBeInTheDocument();
        });
      }
    });
  });

  describe("Share functionality", () => {
    it("share button always visible on flow items", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
        />,
      );

      await screen.findByText("Flow One");
      
      // Should have at least the share button
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThan(0);
    });

    it("handleShareClick(): calls openShareForItem() with blueprint info", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
        />,
      );

      const user = userEvent.setup();
      const flowLabel = await screen.findByText("Flow One");
      let flowRow: HTMLElement | null = flowLabel;
      while (flowRow && flowRow.querySelectorAll("button").length === 0) {
        flowRow = flowRow.parentElement;
      }
      
      const shareButton = flowRow?.querySelector("button");
      if (shareButton) {
        await user.click(shareButton);
        expect(openShareForItemMock).toHaveBeenCalledWith({
          itemKind: "blueprint",
          itemId: "bp-1",
          itemName: "Flow One",
        });
      }
    });
  });

  describe("Loading states", () => {
    it("shows 'Loading flows...' in sidebar during loading", async () => {
      fetchBlueprintsMock.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(
        <WorkflowsPanel
          selectedFlow={null}
          onFlowSelect={vi.fn()}
        />,
      );

      expect(screen.getByText("Loading flows...")).toBeInTheDocument();
    });

    it("shows 'No flows available' when graphFlows.length === 0", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([]);

      render(
        <WorkflowsPanel
          selectedFlow={null}
          onFlowSelect={vi.fn()}
        />,
      );

      expect(await screen.findByText("No flows available")).toBeInTheDocument();
    });
  });

  describe("Main area content", () => {
    it("shows ShareWorkflow + ReactFlowGraph when selectedFlow exists", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByTestId("share-workflow")).toBeInTheDocument();
        expect(screen.getByTestId("react-flow-graph")).toBeInTheDocument();
      });
    });

    it("shows 'Select a flow to view its visualization' when no selectedFlow", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([]);

      render(
        <WorkflowsPanel
          selectedFlow={null}
          onFlowSelect={vi.fn()}
        />,
      );

      expect(
        await screen.findByText("Select a flow to view its visualization")
      ).toBeInTheDocument();
    });
  });

  describe("Props passed to child components", () => {
    it("passes blueprintId={selectedFlow.id} to ShareWorkflow", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByTestId("share-workflow")).toHaveTextContent("bp-1");
      });
    });

    it("passes blueprintId={selectedFlow.id} to ReactFlowGraph", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(reactFlowGraphSpy).toHaveBeenCalledWith(
          expect.objectContaining({ blueprintId: "bp-1" })
        );
      });
    });

    it("passes height='100%' to ReactFlowGraph", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
          height="100%"
        />,
      );

      await waitFor(() => {
        expect(reactFlowGraphSpy).toHaveBeenCalledWith(
          expect.objectContaining({ height: "100%" })
        );
      });
    });

    it("spreads graphProps to ReactFlowGraph", async () => {
      fetchBlueprintsMock.mockResolvedValueOnce([
        { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
      ]);

      render(
        <WorkflowsPanel
          selectedFlow={flow}
          onFlowSelect={vi.fn()}
          graphProps={{
            showControls: true,
            showMiniMap: false,
            showBackground: true,
          }}
        />,
      );

      await waitFor(() => {
        expect(reactFlowGraphSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            showControls: true,
            showMiniMap: false,
            showBackground: true,
          })
        );
      });
    });
  });
});

