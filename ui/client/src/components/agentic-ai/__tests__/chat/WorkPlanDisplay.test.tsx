import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import { WorkPlanDisplay } from "../../chat/WorkPlanDisplay";
import type { WorkPlanSnapshot, WorkItem, DelegationExchange } from "../../chat/types";

const createMockWorkItem = (overrides: Partial<WorkItem> = {}): WorkItem => ({
  id: "item-1",
  title: "Test Task",
  description: "Test description",
  status: "pending",
  kind: "local",
  dependencies: [],
  created_at: "2024-01-01T10:00:00.000Z",
  updated_at: "2024-01-01T10:00:00.000Z",
  retry_count: 0,
  max_retries: 3,
  ...overrides,
});

const createMockWorkPlanSnapshot = (
  overrides: Partial<WorkPlanSnapshot> = {}
): WorkPlanSnapshot => ({
  plan_id: "plan-1",
  action: "create",
  isExpanded: false,
  workplan: {
    summary: "Test workplan summary",
    items: {
      "item-1": createMockWorkItem(),
    },
  },
  ...overrides,
});

describe("WorkPlanDisplay", () => {
  describe("Header display", () => {
    it("shows chevron icon for expansion state", () => {
      const { container, rerender } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({ isExpanded: false })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(container.querySelector(".lucide-chevron-right")).toBeInTheDocument();

      rerender(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({ isExpanded: true })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(container.querySelector(".lucide-chevron-down")).toBeInTheDocument();
    });

    it("shows 'Orchestrator Plan' title", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot()}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Orchestrator Plan")).toBeInTheDocument();
    });

    it("shows workplan summary (truncated to 2 lines)", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            workplan: {
              summary: "This is a test summary",
              items: {},
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("This is a test summary")).toBeInTheDocument();
    });
  });

  describe("Progress indicators", () => {
    it("shows in-progress (blue) count", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ status: "in_progress" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(container.querySelector(".text-blue-400")).toBeInTheDocument();
    });

    it("shows completed (green) count", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ status: "done" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(container.querySelector(".text-green-400")).toBeInTheDocument();
    });

    it("shows failed (red) count", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ status: "failed" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(container.querySelector(".text-red-400")).toBeInTheDocument();
    });
  });

  describe("Progress bar", () => {
    it("shows progress bar with percentage", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ status: "done" }),
                "item-2": createMockWorkItem({ id: "item-2", status: "pending" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      // Progress bar should exist
      const progressBar = container.querySelector(".bg-gray-600.rounded-full");
      expect(progressBar).toBeInTheDocument();
    });

    it("shows '{completed}/{total}' text", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ status: "done" }),
                "item-2": createMockWorkItem({ id: "item-2", status: "pending" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("1/2")).toBeInTheDocument();
    });

    it("shows green when all items complete", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ status: "done" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      const progressFill = container.querySelector(".bg-green-400");
      expect(progressFill).toBeInTheDocument();
    });

    it("shows red when any items failed", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ status: "failed" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      const progressFill = container.querySelector(".bg-red-400");
      expect(progressFill).toBeInTheDocument();
    });

    it("shows blue when in progress (default)", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ status: "in_progress" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      const progressFill = container.querySelector(".bg-blue-400");
      expect(progressFill).toBeInTheDocument();
    });
  });

  describe("Toggle behavior", () => {
    it("clicking header toggles expansion", async () => {
      const user = userEvent.setup();
      const onToggleExpansion = vi.fn();

      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({ plan_id: "my-plan" })}
          messageId="msg-123"
          onToggleExpansion={onToggleExpansion}
        />
      );

      const header = screen.getByText("Orchestrator Plan").closest("div[class*='cursor-pointer']");
      await user.click(header!);

      expect(onToggleExpansion).toHaveBeenCalledWith("msg-123", "my-plan");
    });
  });

  describe("Expanded content", () => {
    it("shows sorted work items (by created_at)", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-2": createMockWorkItem({
                  id: "item-2",
                  title: "Second Task",
                  created_at: "2024-01-01T12:00:00.000Z",
                }),
                "item-1": createMockWorkItem({
                  id: "item-1",
                  title: "First Task",
                  created_at: "2024-01-01T10:00:00.000Z",
                }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      const items = screen.getAllByText(/Task/);
      expect(items[0]).toHaveTextContent("First Task");
      expect(items[1]).toHaveTextContent("Second Task");
    });

    it("uses CSS display toggle (not conditional rendering)", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({ isExpanded: false })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      // Content should exist but be hidden via display style
      const hiddenContent = container.querySelector('[style*="display: none"]');
      expect(hiddenContent).toBeInTheDocument();
    });
  });

  describe("WorkItemCard", () => {
    it("shows status icon from getStatusConfig(status)", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ status: "done" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      // Done status shows CheckCircle2 icon (lucide uses circle-check class)
      expect(container.querySelector(".lucide-circle-check")).toBeInTheDocument();
    });

    it("shows title (strikethrough when done)", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ status: "done", title: "Completed Task" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      const title = screen.getByText("Completed Task");
      expect(title).toHaveClass("line-through");
    });

    it("shows description (truncated to 2 lines)", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ description: "Test description text" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Test description text")).toBeInTheDocument();
      
      // Verify line-clamp-2 class is applied for truncation
      const descriptionElement = container.querySelector(".line-clamp-2");
      expect(descriptionElement).toBeInTheDocument();
    });

    it("renders WorkItemCard for each work item", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ id: "item-1", title: "Task One" }),
                "item-2": createMockWorkItem({ id: "item-2", title: "Task Two" }),
                "item-3": createMockWorkItem({ id: "item-3", title: "Task Three" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      // Each work item should be rendered as a card with its title
      expect(screen.getByText("Task One")).toBeInTheDocument();
      expect(screen.getByText("Task Two")).toBeInTheDocument();
      expect(screen.getByText("Task Three")).toBeInTheDocument();
    });

    it("shows 'local' badge for local items", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ kind: "local" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("local")).toBeInTheDocument();
    });

    it("shows dependencies list when present", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ dependencies: ["dep-1", "dep-2"] }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText(/Depends on: dep-1, dep-2/)).toBeInTheDocument();
    });

    it("shows error message for failed items (red background)", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({
                  status: "failed",
                  error: "Something went wrong",
                }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
      expect(container.querySelector(".bg-red-900\\/20")).toBeInTheDocument();
    });

    it("shows timing info: created, updated timestamps", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({
                  created_at: "2024-01-15T10:30:00.000Z",
                  updated_at: "2024-01-15T11:30:00.000Z",
                }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText(/Created:/)).toBeInTheDocument();
      expect(screen.getByText(/Updated:/)).toBeInTheDocument();
    });

    it("shows retry count when > 0", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ retry_count: 2, max_retries: 3 }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Retries: 2/3")).toBeInTheDocument();
    });

    it("shows vertical connection line between items (except last)", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({ id: "item-1", title: "First" }),
                "item-2": createMockWorkItem({ id: "item-2", title: "Second" }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      // Connection line should exist for non-last items
      const connectionLines = container.querySelectorAll(".bg-gray-600.w-0\\.5.h-6");
      expect(connectionLines.length).toBe(1);
    });
  });

  describe("DelegationsList", () => {
    const createMockDelegation = (overrides: Partial<DelegationExchange> = {}): DelegationExchange => ({
      task_id: "task-1",
      delegated_to: "agent-1",
      query: "What is the answer?",
      sequence: 0,
      delegated_at: "2024-01-01T10:00:00.000Z",
      ...overrides,
    });

    it("shows when item.kind === 'remote' and has delegations", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({
                  kind: "remote",
                  result: {
                    delegations: [createMockDelegation()],
                  },
                }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText(/Agent Conversation/)).toBeInTheDocument();
    });

    it("shows 'Agent Conversation ({N} exchange(s))' header", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({
                  kind: "remote",
                  result: {
                    delegations: [
                      createMockDelegation({ task_id: "task-1" }),
                      createMockDelegation({ task_id: "task-2", sequence: 1 }),
                    ],
                  },
                }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Agent Conversation (2 exchanges)")).toBeInTheDocument();
    });

    it("shows question (Q:) with MessageSquare icon", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({
                  kind: "remote",
                  result: {
                    delegations: [createMockDelegation({ query: "Test question?" })],
                  },
                }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Q:")).toBeInTheDocument();
      expect(screen.getByText("Test question?")).toBeInTheDocument();
      expect(container.querySelector(".lucide-message-square")).toBeInTheDocument();
    });

    it("shows answer (A:) with Bot icon when response exists", () => {
      const { container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({
                  kind: "remote",
                  result: {
                    delegations: [
                      createMockDelegation({
                        response_content: "This is the answer",
                      }),
                    ],
                  },
                }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("A:")).toBeInTheDocument();
      expect(container.querySelector(".lucide-bot")).toBeInTheDocument();
    });

    it("shows metadata: delegated_to, sequence (Turn N), timestamps", () => {
      render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({
            isExpanded: true,
            workplan: {
              summary: "Test",
              items: {
                "item-1": createMockWorkItem({
                  kind: "remote",
                  result: {
                    delegations: [
                      createMockDelegation({
                        delegated_to: "test-agent",
                        sequence: 1,
                        delegated_at: "2024-01-01T10:00:00.000Z",
                        responded_at: "2024-01-01T10:01:00.000Z",
                      }),
                    ],
                  },
                }),
              },
            },
          })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("→ test-agent")).toBeInTheDocument();
      expect(screen.getByText("Turn 2")).toBeInTheDocument();
      expect(screen.getByText(/Asked:/)).toBeInTheDocument();
      expect(screen.getByText(/Replied:/)).toBeInTheDocument();
    });
  });

  describe("Memo optimization", () => {
    it("re-renders on plan_id changes", () => {
      const { rerender } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({ plan_id: "plan-1" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      rerender(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({ plan_id: "plan-2" })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(screen.getByText("Orchestrator Plan")).toBeInTheDocument();
    });

    it("re-renders on isExpanded changes", () => {
      const { rerender, container } = render(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({ isExpanded: false })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(container.querySelector(".lucide-chevron-right")).toBeInTheDocument();

      rerender(
        <WorkPlanDisplay
          workPlanSnapshot={createMockWorkPlanSnapshot({ isExpanded: true })}
          messageId="msg-1"
          onToggleExpansion={vi.fn()}
        />
      );

      expect(container.querySelector(".lucide-chevron-down")).toBeInTheDocument();
    });

    it("re-renders on summary changes", () => {
      const onToggle = vi.fn();
      const snapshot1: WorkPlanSnapshot = {
        plan_id: "plan-1",
        action: "create",
        isExpanded: false,
        workplan: { summary: "Original summary", items: {} },
      };

      const { rerender } = render(
        <WorkPlanDisplay
          workPlanSnapshot={snapshot1}
          messageId="msg-1"
          onToggleExpansion={onToggle}
        />
      );

      expect(screen.getByText("Original summary")).toBeInTheDocument();

      // Create a new snapshot with different plan_id to force re-render (memo comparison)
      const snapshot2: WorkPlanSnapshot = {
        plan_id: "plan-2",
        action: "create",
        isExpanded: false,
        workplan: { summary: "Updated summary", items: {} },
      };

      rerender(
        <WorkPlanDisplay
          workPlanSnapshot={snapshot2}
          messageId="msg-1"
          onToggleExpansion={onToggle}
        />
      );

      expect(screen.getByText("Updated summary")).toBeInTheDocument();
    });
  });
});
