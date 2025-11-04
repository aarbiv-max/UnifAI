import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { InfoIcon } from "lucide-react";
import { ElementType, ElementSchema } from "../../../types/workspace";
import { FieldPopulation } from "./FieldPopulation";

interface GoogleMcpFormProps {
  isOpen: boolean;
  onClose: () => void;
  elementType: ElementType;
  elementSchema: ElementSchema;
  elementActions?: any[];
  onSave: (data: any) => Promise<void>;
}


export const GoogleMcpForm: React.FC<GoogleMcpFormProps> = ({
  isOpen,
  onClose,
  elementType,
  elementSchema,
  elementActions = [],
  onSave,
}) => {
  const [formData, setFormData] = useState({
    name: "",
    podUrl: "",
    sseEndpoint: "http://localhost:3000/sse", // Default localhost URL for mcp-inspector
    tool_names: [] as string[],
  });
  const [isSaving, setIsSaving] = useState(false);
  const [populateResults, setPopulateResults] = useState<{ [fieldName: string]: string[] }>({});

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (isOpen) {
      setFormData({
        name: "",
        podUrl: "",
        sseEndpoint: "http://localhost:3000/sse",
        tool_names: [],
      });
      setPopulateResults({});
    }
  }, [isOpen]);

  const handleInputChange = (field: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handlePopulateResult = (fieldName: string, results: string[], multiSelect: boolean) => {
    setPopulateResults(prev => ({
      ...prev,
      [fieldName]: results
    }));
    
    // Update form data with populated results
    if (multiSelect) {
      // For multi-select, set the array of selected values
      handleInputChange(fieldName, results);
    } else {
      // For single select, set the first (and only) selected value
      handleInputChange(fieldName, results.length > 0 ? results[0] : "");
    }
  };

  const isFormValid = () => {
    // pod_url is optional (just for reference), only sse_endpoint is required
    return (
      formData.name.trim() !== "" &&
      formData.sseEndpoint.trim() !== ""
    );
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);

      // Prepare save data
      // Note: pod_url is not part of McpProviderConfig schema, so we only save sse_endpoint
      // The pod_url is just for user reference - they'll configure mcp-inspector separately
      const saveData: any = {
        name: formData.name.trim(),
        cfg_dict: {
          sse_endpoint: formData.sseEndpoint.trim(),
          // pod_url removed - not part of McpProviderConfig schema
        },
      };
      
      // Add tool_names if any are selected
      if (formData.tool_names && formData.tool_names.length > 0) {
        saveData.cfg_dict.tool_names = formData.tool_names;
      }

      const result = await onSave(saveData);

      // Only close the dialog if save was successful
      if (result !== null && result !== false) {
        onClose();
      }
    } catch (error) {
      console.error("Error saving Google MCP server:", error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-background-card border-gray-800 text-foreground max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Add Google MCP Server
            <Badge variant="outline" className="bg-amber-900/30 text-amber-300 border-amber-600/50">
              Google MCP
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Configure a Google MCP server using mcp-inspector. This will create a local MCP server
            that connects to your Google pod URL via streamable HTTP.
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSave();
          }}
          className="space-y-6 mt-4"
        >
          <Alert className="bg-amber-900/20 border-amber-600/50">
            <InfoIcon className="h-4 w-4 text-amber-400" />
            <AlertDescription className="text-amber-200">
              <p className="font-semibold mb-2">How this works:</p>
              <ol className="list-decimal list-inside space-y-1 text-sm">
                <li>Enter the endpoint URL where mcp-inspector is serving (use localhost if on same machine, or VM IP if accessing remotely)</li>
                <li>Optionally note your Google MCP pod URL for reference (not saved - configure in mcp-inspector)</li>
                <li>After saving, the MCP server will be available for use</li>
              </ol>
              <p className="text-xs mt-2 font-semibold text-amber-300">
                Note: If the app is on a VM and mcp-inspector is on your local machine, use your machine's IP address instead of localhost.
              </p>
              <p className="text-xs mt-2 italic">
                Note: The local endpoint uses streamable HTTP transport, not traditional SSE.
              </p>
            </AlertDescription>
          </Alert>

          {/* Name Field */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Server Name <span className="text-red-400">*</span>
            </Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => handleInputChange("name", e.target.value)}
              className="bg-background-dark"
              placeholder="My Google MCP Server"
            />
            <p className="text-xs text-gray-400">
              A friendly name to identify this MCP server instance
            </p>
          </div>

          {/* Pod URL Field - Info only, not saved */}
          <div className="space-y-2">
            <Label htmlFor="podUrl">
              Google MCP Pod URL (Info Only)
            </Label>
            <Input
              id="podUrl"
              value={formData.podUrl}
              onChange={(e) => handleInputChange("podUrl", e.target.value)}
              className="bg-background-dark"
              placeholder="https://your-google-mcp-pod.example.com"
            />
            <p className="text-xs text-gray-400">
              The actual Google MCP server endpoint URL (for your reference - configure this in mcp-inspector separately)
            </p>
          </div>

          {/* SSE Endpoint Field (Localhost URL for Streamable HTTP) */}
          <div className="space-y-2">
            <Label htmlFor="sseEndpoint">
              Local Endpoint (Streamable HTTP) <span className="text-red-400">*</span>
            </Label>
            <Input
              id="sseEndpoint"
              value={formData.sseEndpoint}
              onChange={(e) => handleInputChange("sseEndpoint", e.target.value)}
              className="bg-background-dark"
              placeholder="http://localhost:3000/sse"
            />
            <p className="text-xs text-gray-400">
              The endpoint URL where mcp-inspector is serving. Use localhost if on the same machine, 
              or use your machine's IP address (e.g., http://192.168.1.100:3000/sse) if accessing from a VM.
              (default: http://localhost:3000/sse)
            </p>
          </div>

          {/* Tool Names Field */}
          <div className="space-y-2">
            <Label htmlFor="tool_names">
              Tool Names (Optional)
              <Badge variant="outline" className="ml-2 text-xs">
                populate
              </Badge>
              <Badge variant="outline" className="ml-1 text-xs">
                multi-select
              </Badge>
            </Label>
            <FieldPopulation
              fieldName="tool_names"
              populateHint={{
                action_uid: "mcp.get_tools_names",
                hint_type: "populate",
                field_mapping: "tool_names",
                multi_select: true,
                dependencies: { "sseEndpoint": "sse_endpoint" }
              }}
              elementActions={elementActions}
              selectedElementType={elementType}
              formData={{
                ...formData,
                sse_endpoint: formData.sseEndpoint, // Map camelCase to snake_case for the action
              }}
              onPopulateResult={handlePopulateResult}
            />
            <p className="text-xs text-gray-400">
              Select specific tools to use from the MCP server. Leave empty to use all available tools.
              Click the populate button to discover available tools from the server.
            </p>
          </div>

          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-primary hover:bg-opacity-80"
              disabled={isSaving || !isFormValid()}
            >
              {isSaving ? "Saving..." : "Save & Configure"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

