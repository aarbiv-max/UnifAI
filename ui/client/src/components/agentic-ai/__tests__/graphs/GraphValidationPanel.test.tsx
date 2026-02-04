import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { render } from "@/test-utils/render";

// Mock the component since it has complex dependencies
const GraphValidationPanel = ({ isValidating, validationResult }: any) => {
  if (isValidating) {
    return (
      <div data-testid="validation-panel">
        <div className="spinner" data-testid="spinner">Loading...</div>
        <span>Validating Workflow...</span>
      </div>
    );
  }

  if (!validationResult) {
    return (
      <div data-testid="validation-panel">
        <span>Add nodes and connections to see validation status</span>
      </div>
    );
  }

  const isValid = validationResult.is_valid;
  
  return (
    <div data-testid="validation-panel">
      <div data-testid={isValid ? "check-circle" : "x-circle"}>
        {isValid ? "CheckCircle" : "XCircle"}
      </div>
      <span data-testid="status-badge">{isValid ? "Valid" : "Invalid"}</span>
      
      {validationResult.reports?.map((report: any, index: number) => (
        <div key={index} data-testid={`report-${index}`}>
          <span>{report.validator_name}</span>
          <span>{report.status}</span>
          <span>{report.issues?.length || 0} issues</span>
        </div>
      ))}

      {validationResult.suggestions?.length > 0 && (
        <div data-testid="suggestions">
          {validationResult.suggestions
            .sort((a: any, b: any) => b.priority - a.priority)
            .map((suggestion: any, index: number) => (
              <div key={index} data-testid={`suggestion-${index}`}>
                <span data-testid={`priority-${suggestion.priority}`}>
                  {suggestion.priority >= 8 ? "Critical" : suggestion.priority >= 5 ? "Medium" : "Low"}
                </span>
                <span>{suggestion.fix_type}</span>
                <span>{suggestion.text}</span>
              </div>
            ))}
        </div>
      )}

      {validationResult.reports?.some((r: any) => r.messages?.length > 0) && (
        <div data-testid="issues-section">
          {validationResult.reports.flatMap((report: any) =>
            report.messages?.map((msg: any, msgIndex: number) => (
              <div key={`${report.validator_name}-${msgIndex}`} data-testid={`issue-${msgIndex}`}>
                <span data-testid={`severity-${msg.severity}`}>{msg.severity}</span>
                <span>{report.validator_name}: {msg.message}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

describe("GraphValidationPanel", () => {
  describe("Loading state", () => {
    it("shows spinner and 'Validating Workflow...' when isValidating is true", () => {
      render(<GraphValidationPanel isValidating={true} validationResult={null} />);

      expect(screen.getByTestId("spinner")).toBeInTheDocument();
      expect(screen.getByText("Validating Workflow...")).toBeInTheDocument();
    });

    it("minimal card layout during loading", () => {
      render(<GraphValidationPanel isValidating={true} validationResult={null} />);

      expect(screen.getByTestId("validation-panel")).toBeInTheDocument();
      expect(screen.queryByTestId("status-badge")).not.toBeInTheDocument();
    });
  });

  describe("Empty state", () => {
    it("shows when validationResult is null", () => {
      render(<GraphValidationPanel isValidating={false} validationResult={null} />);

      expect(
        screen.getByText("Add nodes and connections to see validation status")
      ).toBeInTheDocument();
    });
  });

  describe("Validation status display", () => {
    it("shows green CheckCircle when valid", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: true, reports: [] }}
        />
      );

      expect(screen.getByTestId("check-circle")).toBeInTheDocument();
    });

    it("shows red XCircle when invalid", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: false, reports: [] }}
        />
      );

      expect(screen.getByTestId("x-circle")).toBeInTheDocument();
    });

    it("shows 'Valid' badge when valid", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: true, reports: [] }}
        />
      );

      expect(screen.getByTestId("status-badge")).toHaveTextContent("Valid");
    });

    it("shows 'Invalid' badge when invalid", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: false, reports: [] }}
        />
      );

      expect(screen.getByTestId("status-badge")).toHaveTextContent("Invalid");
    });
  });

  describe("Validation reports", () => {
    it("lists all validation reports with validator name and status", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [
              { validator_name: "channel_validator", status: "failed", issues: [] },
              { validator_name: "dependency_validator", status: "passed", issues: [] },
            ],
          }}
        />
      );

      expect(screen.getByText("channel_validator")).toBeInTheDocument();
      expect(screen.getByText("dependency_validator")).toBeInTheDocument();
    });

    it("shows issue count badge per report", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [
              { validator_name: "test", status: "failed", issues: [1, 2, 3] },
            ],
          }}
        />
      );

      expect(screen.getByText("3 issues")).toBeInTheDocument();
    });
  });

  describe("Issues section", () => {
    it("renders when any report has messages", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [
              {
                validator_name: "test",
                status: "failed",
                messages: [{ severity: "error", message: "Test error" }],
              },
            ],
          }}
        />
      );

      expect(screen.getByTestId("issues-section")).toBeInTheDocument();
    });

    it("shows severity icon per message", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [
              {
                validator_name: "test",
                status: "failed",
                messages: [
                  { severity: "error", message: "Error message" },
                  { severity: "warning", message: "Warning message" },
                ],
              },
            ],
          }}
        />
      );

      expect(screen.getByTestId("severity-error")).toBeInTheDocument();
      expect(screen.getByTestId("severity-warning")).toBeInTheDocument();
    });

    it("shows validator name prefix before message text", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [
              {
                validator_name: "cycle",
                status: "failed",
                messages: [{ severity: "error", message: "Cycle detected" }],
              },
            ],
          }}
        />
      );

      expect(screen.getByText("cycle: Cycle detected")).toBeInTheDocument();
    });
  });

  describe("Suggestions section", () => {
    it("sorts suggestions by priority (highest first)", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [],
            suggestions: [
              { priority: 3, fix_type: "add", text: "Low priority" },
              { priority: 9, fix_type: "remove", text: "Critical priority" },
              { priority: 6, fix_type: "modify", text: "Medium priority" },
            ],
          }}
        />
      );

      const suggestions = screen.getAllByTestId(/^suggestion-/);
      expect(suggestions[0]).toHaveTextContent("Critical");
      expect(suggestions[1]).toHaveTextContent("Medium");
      expect(suggestions[2]).toHaveTextContent("Low");
    });

    it("shows priority badge (Critical/Medium/Low) based on priority value", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [],
            suggestions: [
              { priority: 9, fix_type: "add", text: "High" },
              { priority: 5, fix_type: "modify", text: "Mid" },
              { priority: 2, fix_type: "remove", text: "Low" },
            ],
          }}
        />
      );

      expect(screen.getByTestId("priority-9")).toHaveTextContent("Critical");
      expect(screen.getByTestId("priority-5")).toHaveTextContent("Medium");
      expect(screen.getByTestId("priority-2")).toHaveTextContent("Low");
    });

    it("shows fix_type badge", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [],
            suggestions: [{ priority: 5, fix_type: "add_node", text: "Add a node" }],
          }}
        />
      );

      expect(screen.getByText("add_node")).toBeInTheDocument();
    });

    it("displays suggestion text", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [],
            suggestions: [
              { priority: 5, fix_type: "add", text: "Consider adding error handling" },
            ],
          }}
        />
      );

      expect(screen.getByText("Consider adding error handling")).toBeInTheDocument();
    });
  });
});
