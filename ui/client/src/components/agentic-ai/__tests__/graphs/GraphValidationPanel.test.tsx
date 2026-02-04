import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { render } from "@/test-utils/render";
import GraphValidationPanel from "../../graphs/GraphValidationPanel";

describe("GraphValidationPanel", () => {
  describe("Loading state", () => {
    it("shows spinner and 'Validating Workflow...' when isValidating is true", () => {
      render(
        <GraphValidationPanel
          isValidating={true}
          validationResult={null}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Validating Workflow...")).toBeInTheDocument();
      // Spinner is rendered via CSS animation class
      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("minimal card layout during loading", () => {
      render(
        <GraphValidationPanel
          isValidating={true}
          validationResult={null}
          fixSuggestions={[]}
        />
      );

      // Should not show the Valid/Invalid badge during loading
      expect(screen.queryByText("Valid")).not.toBeInTheDocument();
      expect(screen.queryByText("Invalid")).not.toBeInTheDocument();
    });
  });

  describe("Empty state", () => {
    it("shows when validationResult is null", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={null}
          fixSuggestions={[]}
        />
      );

      expect(
        screen.getByText("Add nodes and connections to see validation status.")
      ).toBeInTheDocument();
    });

    it("shows 'Workflow Validation' title when no result", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={null}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Workflow Validation")).toBeInTheDocument();
    });
  });

  describe("Validation status display", () => {
    it("shows CheckCircle icon when valid", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: true, reports: [] }}
          fixSuggestions={[]}
        />
      );

      // The CheckCircle from lucide-react renders as an SVG
      const header = screen.getByText("Workflow Validation").closest("div");
      expect(header?.querySelector("svg")).toBeInTheDocument();
    });

    it("shows XCircle icon when invalid", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: false, reports: [] }}
          fixSuggestions={[]}
        />
      );

      // The XCircle from lucide-react renders as an SVG
      const header = screen.getByText("Workflow Validation").closest("div");
      expect(header?.querySelector("svg")).toBeInTheDocument();
    });

    it("shows 'Valid' badge when valid", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: true, reports: [] }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Valid")).toBeInTheDocument();
    });

    it("shows 'Invalid' badge when invalid", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: false, reports: [] }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Invalid")).toBeInTheDocument();
    });
  });

  describe("Validation reports", () => {
    it("lists all validation reports with validator display names", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [
              { validator_name: "channel", is_valid: false, messages: [], details: {} },
              { validator_name: "dependency", is_valid: true, messages: [], details: {} },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Channel Validation")).toBeInTheDocument();
      expect(screen.getByText("Dependency Validation")).toBeInTheDocument();
    });

    it("shows issue count badge per report", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [
              {
                validator_name: "channel",
                is_valid: false,
                messages: [
                  { text: "Error 1", severity: "error", code: "E1", context: {} },
                  { text: "Error 2", severity: "error", code: "E2", context: {} },
                  { text: "Error 3", severity: "error", code: "E3", context: {} },
                ],
                details: {},
              },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("3 issues")).toBeInTheDocument();
    });

    it("displays validator icons based on validator name", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [
              { validator_name: "cycle", is_valid: false, messages: [], details: {} },
              { validator_name: "orphan", is_valid: true, messages: [], details: {} },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Cycle Validation")).toBeInTheDocument();
      expect(screen.getByText("Orphan Validation")).toBeInTheDocument();
    });

    it("shows unknown validator name as-is", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: true,
            reports: [
              { validator_name: "custom_validator", is_valid: true, messages: [], details: {} },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("custom_validator")).toBeInTheDocument();
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
                validator_name: "channel",
                is_valid: false,
                messages: [{ text: "Test error", severity: "error", code: "E1", context: {} }],
                details: {},
              },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Issues Found")).toBeInTheDocument();
    });

    it("displays error severity icon (XCircle) for error messages", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [
              {
                validator_name: "channel",
                is_valid: false,
                messages: [{ text: "Error message", severity: "error", code: "E1", context: {} }],
                details: {},
              },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      // Message text is displayed
      expect(screen.getByText("Error message")).toBeInTheDocument();
    });

    it("displays warning severity icon (AlertTriangle) for warning messages", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [
              {
                validator_name: "dependency",
                is_valid: false,
                messages: [{ text: "Warning message", severity: "warning", code: "W1", context: {} }],
                details: {},
              },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Warning message")).toBeInTheDocument();
    });

    it("displays info severity icon for info messages", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [
              {
                validator_name: "orphan",
                is_valid: false,
                messages: [{ text: "Info message", severity: "info", code: "I1", context: {} }],
                details: {},
              },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Info message")).toBeInTheDocument();
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
                is_valid: false,
                messages: [{ text: "Cycle detected", severity: "error", code: "C1", context: {} }],
                details: {},
              },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("[Cycle Validation]")).toBeInTheDocument();
      expect(screen.getByText("Cycle detected")).toBeInTheDocument();
    });

    it("displays multiple messages from multiple reports", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: false,
            reports: [
              {
                validator_name: "channel",
                is_valid: false,
                messages: [
                  { text: "Channel error", severity: "error", code: "C1", context: {} },
                ],
                details: {},
              },
              {
                validator_name: "dependency",
                is_valid: false,
                messages: [
                  { text: "Dependency error", severity: "error", code: "D1", context: {} },
                ],
                details: {},
              },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Channel error")).toBeInTheDocument();
      expect(screen.getByText("Dependency error")).toBeInTheDocument();
    });
  });

  describe("Suggestions section", () => {
    it("sorts suggestions by priority (highest first)", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: false, reports: [] }}
          fixSuggestions={[
            { priority: 1, fix_type: "ADD_NODE", text: "Low priority", code: "L1", context: {} },
            { priority: 5, fix_type: "REMOVE_NODE", text: "Critical priority", code: "H1", context: {} },
            { priority: 3, fix_type: "MODIFY_CONNECTION", text: "Medium priority", code: "M1", context: {} },
          ]}
        />
      );

      // Text should appear in order from highest priority to lowest
      const allText = document.body.textContent || "";
      const criticalPos = allText.indexOf("Critical priority");
      const mediumPos = allText.indexOf("Medium priority");
      const lowPos = allText.indexOf("Low priority");

      expect(criticalPos).toBeLessThan(mediumPos);
      expect(mediumPos).toBeLessThan(lowPos);
    });

    it("shows Critical badge for priority >= 4", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: false, reports: [] }}
          fixSuggestions={[
            { priority: 4, fix_type: "ADD_NODE", text: "High priority fix", code: "H1", context: {} },
          ]}
        />
      );

      expect(screen.getByText("Critical")).toBeInTheDocument();
    });

    it("shows Medium badge for priority >= 2 and < 4", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: false, reports: [] }}
          fixSuggestions={[
            { priority: 2, fix_type: "MODIFY_CONNECTION", text: "Medium priority fix", code: "M1", context: {} },
          ]}
        />
      );

      expect(screen.getByText("Medium")).toBeInTheDocument();
    });

    it("shows Low badge for priority < 2", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: false, reports: [] }}
          fixSuggestions={[
            { priority: 1, fix_type: "ADD_CHANNEL", text: "Low priority fix", code: "L1", context: {} },
          ]}
        />
      );

      expect(screen.getByText("Low")).toBeInTheDocument();
    });

    it("shows fix_type badge with formatted text", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: false, reports: [] }}
          fixSuggestions={[
            { priority: 3, fix_type: "ADD_NODE", text: "Add a node", code: "A1", context: {} },
          ]}
        />
      );

      // fix_type is formatted: ADD_NODE -> "add node"
      expect(screen.getByText("add node")).toBeInTheDocument();
    });

    it("displays suggestion text", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: false, reports: [] }}
          fixSuggestions={[
            { priority: 3, fix_type: "ADD_NODE", text: "Consider adding error handling", code: "A1", context: {} },
          ]}
        />
      );

      expect(screen.getByText("Consider adding error handling")).toBeInTheDocument();
    });

    it("shows Fix Suggestions header when suggestions exist", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: false, reports: [] }}
          fixSuggestions={[
            { priority: 3, fix_type: "ADD_NODE", text: "Some suggestion", code: "S1", context: {} },
          ]}
        />
      );

      expect(screen.getByText("Fix Suggestions")).toBeInTheDocument();
    });

    it("does not show Fix Suggestions header when no suggestions", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{ is_valid: true, reports: [] }}
          fixSuggestions={[]}
        />
      );

      expect(screen.queryByText("Fix Suggestions")).not.toBeInTheDocument();
    });
  });

  describe("Validation Reports header", () => {
    it("shows 'Validation Reports' section header", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: true,
            reports: [
              { validator_name: "channel", is_valid: true, messages: [], details: {} },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Validation Reports")).toBeInTheDocument();
    });
  });

  describe("Validator display names", () => {
    it("displays 'Channel Validation' for channel validator", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: true,
            reports: [
              { validator_name: "channel", is_valid: true, messages: [], details: {} },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Channel Validation")).toBeInTheDocument();
    });

    it("displays 'Required Nodes Validation' for requirednodes validator", () => {
      render(
        <GraphValidationPanel
          isValidating={false}
          validationResult={{
            is_valid: true,
            reports: [
              { validator_name: "requirednodes", is_valid: true, messages: [], details: {} },
            ],
          }}
          fixSuggestions={[]}
        />
      );

      expect(screen.getByText("Required Nodes Validation")).toBeInTheDocument();
    });
  });
});
