import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  Database,
  FileText,
  Zap,
  Filter,
  GitBranch,
  MessageSquare,
  BookOpen,
  Trash2,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { StreamingDataProvider } from "@/components/agentic-ai/StreamingDataContext";
import { GraphFlow, FlowObject } from "./graphs/interfaces";
import ReactFlowGraph from "../agentic-ai/graphs/ReactFlowGraph";
import axios from "../../http/axiosAgentConfig";

// Create a ReactFlow provider wrapper
import { ReactFlowProvider } from "reactflow";

// Helper function to convert GraphFlow to FlowObject
const convertGraphFlowToFlowObject = (
  graphFlow: GraphFlow,
  index: number,
  blueprintId?: string,
): FlowObject => {
  if (!graphFlow) return null;

  // Extract metadata
  const name = graphFlow.name || `Flow ${index + 1}`;
  const description = graphFlow.description || "No description available";

  // Generate a random icon for the flow
  const iconOptions: React.FC<{ className?: string }>[] = [
    Activity,
    Database,
    FileText,
    Zap,
    Filter,
    GitBranch,
    MessageSquare,
    BookOpen,
  ];
  const IconComponent = iconOptions[index % iconOptions.length];

  return {
    id: blueprintId || index.toString(), // Use blueprintId if available
    name,
    description,
    icon: <IconComponent className="h-4 w-4 mr-2" />,
    flow: {
      nodes: [],
      edges: [],
    },
  };
};

type AgentFlowGraphProps = {
  selectedFlow: FlowObject | null;
  setSelectedFlow: (flow: FlowObject | null) => void;
};

export default function AgentFlowGraph({
  selectedFlow,
  setSelectedFlow,
}: AgentFlowGraphProps): React.ReactElement {
  // State for available graph flows
  const [graphFlows, setGraphFlows] = useState<FlowObject[]>([]);
  const [activeFlowIds, setActiveFlowIds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false);
  const [flowToDelete, setFlowToDelete] = useState<FlowObject | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const { user } = useAuth();

  // Effect to load graph flows from API
  useEffect(() => {
    const fetchGraphFlows = async () => {
      try {
        const response = await axios.get(
          `/blueprints/available.blueprints.resolved.get?userId=${user?.username || "default"}`,
        );
        const blueprints: Array<{ blueprint_id: string; spec_dict: GraphFlow }> = response.data;

        // Convert the blueprints to the format expected by the component
        const processedFlows = blueprints.map((blueprint) =>
          convertGraphFlowToFlowObject(blueprint.spec_dict, 0, blueprint.blueprint_id),
        );
        setGraphFlows(processedFlows);

        // Select the first flow by default
        if (processedFlows.length > 0) {
          setSelectedFlow(processedFlows[0]);
        }
      } catch (error) {
        console.error("Error fetching available plans:", error);
      } finally {
        setIsLoading(false);
      }
    };

    const fetchActiveFlows = async () => {
      try {
        const response = await axios.get(
          `/sessions/session.user.blueprints.get?userId=${user?.username || "default"}`
        );
        setActiveFlowIds(response.data || []);
      } catch (error) {
        console.error("Error fetching active flows:", error);
        setActiveFlowIds([]);
      }
    };

    fetchGraphFlows();
    fetchActiveFlows();
  }, [setSelectedFlow, user]);

  const handleFlowSelect = (flow: FlowObject): void => {
    setSelectedFlow(flow);
  };

  const isFlowActive = (flowId: string): boolean => {
    return activeFlowIds.includes(flowId);
  };

  const handleDeleteClick = (flow: FlowObject, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent flow selection when clicking delete
    setFlowToDelete(flow);
    setShowDeleteModal(true);
  };

  const handleDeleteConfirm = async () => {
    if (!flowToDelete) return;

    setIsDeleting(true);
    try {
      await axios.delete(`/blueprints/remove.blueprint?blueprintId=${flowToDelete.id}`);
      
      // Remove the deleted flow from the list
      setGraphFlows(prevFlows => prevFlows.filter(flow => flow.id !== flowToDelete.id));
      
      // If the deleted flow was selected, clear the selection
      if (selectedFlow?.id === flowToDelete.id) {
        setSelectedFlow(null);
      }
      
      setShowDeleteModal(false);
      setFlowToDelete(null);
    } catch (error) {
      console.error('Error deleting blueprint:', error);
      // Handle error (we can consider show a toast notification here)
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setShowDeleteModal(false);
    setFlowToDelete(null);
  };

  if (isLoading) {
    return (
      <Card className="bg-background-card shadow-card border-gray-800">
        <CardHeader className="py-4 px-6">
          <CardTitle className="text-lg font-heading">
            Agent Flow Visualization
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0" style={{ height: "80vh" }}>
          <div className="flex items-center justify-center h-full">
            <div className="text-gray-400">Loading flows...</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-background-card shadow-card border-gray-800">
      <CardHeader className="py-4 px-6 flex flex-row justify-between items-center">
        <CardTitle className="text-lg font-heading">
          Agent Flow Visualization
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0" style={{ height: "80vh" }}>
        <div className="flex h-full">
          {/* Sidebar for graph selection */}
          <div className="w-1/5 border-r border-gray-800 bg-background-dark overflow-y-auto">
            <div className="py-3 px-4 border-b border-gray-800 bg-background-surface">
              <h3 className="text-sm font-medium">Available Flows</h3>
            </div>
            <div className="py-2">
              {graphFlows.map((flow) => (
                <motion.div
                  key={flow.id}
                  className={`px-4 py-2 border-l-2 cursor-pointer ${
                    selectedFlow?.id === flow.id
                      ? "border-[#003f5c] bg-[#003f5c] bg-opacity-10"
                      : "border-transparent hover:bg-background-surface"
                  }`}
                  onClick={() => handleFlowSelect(flow)}
                  whileHover={{ x: 2 }}
                  transition={{ duration: 0.1 }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      {flow.icon}
                      <span className="text-sm font-medium">{flow.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {isFlowActive(flow.id) && (
                        <span className="text-xs bg-primary text-white px-2 py-1 rounded-full">
                          Active
                        </span>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 hover:bg-red-500/20 hover:text-red-400"
                        onClick={(e) => handleDeleteClick(flow, e)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">
                    {flow.description}
                  </p>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Graph visualization */}
          <div className="flex-grow">
            <StreamingDataProvider>
              <ReactFlowProvider>
                <ReactFlowGraph
                  blueprintId={selectedFlow?.id} // Pass the id (which is blueprintId)
                  height="100%"
                  showControls={true}
                  showMiniMap={true}
                  showBackground={true}
                  interactive={true}
                />
              </ReactFlowProvider>
            </StreamingDataProvider>
          </div>
        </div>
      </CardContent>

      {/* Delete Confirmation Modal */}
      <Dialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Flow</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {flowToDelete?.name}?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={handleDeleteCancel}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
            >
              {isDeleting ? "Deleting..." : "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}