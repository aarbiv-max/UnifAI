import React, { useState, useRef, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Sparkles,
  Loader2,
  Bot,
  Workflow,
  X,
  Settings,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import {
  createBuilderSession,
  executeBuilderRequest,
  checkBuilderAgentExists,
  BuilderSession,
  BuilderExecuteResponse,
} from "@/api/agentic";

interface SmartBuilderPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onWorkflowCreated?: (blueprintId: string) => void;
}

interface LogEntry {
  id: string;
  phase: string;
  message: string;
  icon: React.ReactNode;
  status: "running" | "complete" | "error";
  timestamp: Date;
}

interface WorkflowResult {
  workflowName?: string;
  blueprintId?: string;
  agentsCreated?: number;
  agentsReused?: number;
  usesOrchestrator?: boolean;
}


export default function SmartBuilderPanel({
  isOpen,
  onClose,
  onWorkflowCreated,
}: SmartBuilderPanelProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [workflowResult, setWorkflowResult] = useState<WorkflowResult | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [session, setSession] = useState<BuilderSession | null>(null);
  const [createdBlueprintId, setCreatedBlueprintId] = useState<string | null>(null);
  const [isCheckingSetup, setIsCheckingSetup] = useState(true);
  const [hasBuilderAgent, setHasBuilderAgent] = useState(false);
  const [builderAgentInfo, setBuilderAgentInfo] = useState<any>(null);
  const [availableLlms, setAvailableLlms] = useState<any[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();
  const { toast } = useToast();

  // Check if builder agent exists when panel opens
  useEffect(() => {
    if (isOpen) {
      setIsCheckingSetup(true);
      const userId = user?.username || "default";
      
      checkBuilderAgentExists(userId)
        .then((result) => {
          setHasBuilderAgent(result.exists);
          setBuilderAgentInfo(result.builderAgent);
          setAvailableLlms(result.llms || []);
          setIsCheckingSetup(false);
        })
        .catch((err) => {
          console.error("Error checking builder agent:", err);
          setIsCheckingSetup(false);
          setHasBuilderAgent(false);
        });
    }
  }, [isOpen, user]);

  // Reset state when closed
  useEffect(() => {
    if (!isOpen) {
      setLogs([]);
      setWorkflowResult(null);
      setInputValue("");
      setSession(null);
      setCreatedBlueprintId(null);
      setIsProcessing(false);
    }
  }, [isOpen]);

  // Scroll to bottom on new logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, workflowResult]);

  // Add a processing log entry (honest - no fake progress)
  const addProcessingLog = useCallback(() => {
    setLogs((prev) => [...prev, {
      id: `processing-${Date.now()}`,
      phase: "processing",
      message: "Building your workflow...",
      icon: <Loader2 className="h-3 w-3 animate-spin" />,
      status: "running",
      timestamp: new Date(),
    }]);
  }, []);

  // Update logs when phases complete (from actual response)
  const updateLogsFromResponse = useCallback((completedPhases: string[]) => {
    // Remove the processing log
    setLogs((prev) => prev.filter((log) => log.phase !== "processing"));
    
    // Add completed phase logs
    completedPhases.forEach((phase) => {
      const message = `${phase.charAt(0).toUpperCase() + phase.slice(1)} ✓`;
      setLogs((prev) => [...prev, {
        id: `${phase}-${Date.now()}`,
        phase,
        message,
        icon: <CheckCircle2 className="h-3 w-3 text-emerald-400" />,
        status: "complete",
        timestamp: new Date(),
      }]);
    });
  }, []);

  const handleSend = async () => {
    if (!inputValue.trim() || isProcessing) return;

    const userRequest = inputValue.trim();
    setInputValue("");
    setIsProcessing(true);
    setLogs([]);
    setWorkflowResult(null);
    setCreatedBlueprintId(null);

    // Add user message to logs
    setLogs([{
      id: `user-${Date.now()}`,
      phase: "request",
      message: userRequest,
      icon: <Bot className="h-3 w-3" />,
      status: "complete",
      timestamp: new Date(),
    }]);

    try {
      let currentSession = session;
      if (!currentSession) {
        if (!builderAgentInfo?.rid) {
          throw new Error("Builder agent not found. Create one in Inventory → Agents first.");
        }
        const userId = user?.username || "default";
        
        // Add connecting log
        setLogs((prev) => [...prev, {
          id: `connect-${Date.now()}`,
          phase: "connect",
          message: "Connecting to builder agent...",
          icon: <Loader2 className="h-3 w-3 animate-spin" />,
          status: "running",
          timestamp: new Date(),
        }]);

        currentSession = await createBuilderSession(userId, builderAgentInfo);
        setSession(currentSession);

        // Update connect log to complete
        setLogs((prev) => prev.map((log) => 
          log.phase === "connect" 
            ? { ...log, status: "complete" as const, message: "Connected", icon: <CheckCircle2 className="h-3 w-3 text-emerald-400" /> }
            : log
        ));
      }

      // Show honest processing state (no fake progress)
      addProcessingLog();

      // Execute the builder request
      const response: BuilderExecuteResponse = await executeBuilderRequest(
        currentSession.sessionId,
        userRequest
      );

      // Update with actual completed phases from response
      if (response.metadata?.phases_completed) {
        updateLogsFromResponse(response.metadata.phases_completed);
      } else {
        // Remove processing log if no phases info
        setLogs((prev) => prev.filter((log) => log.phase !== "processing"));
      }

      // Check for blueprint creation
      if (response.metadata?.blueprint_id) {
        setCreatedBlueprintId(response.metadata.blueprint_id);
        
        // Set workflow result for status display
        setWorkflowResult({
          workflowName: response.metadata?.workflow_name || 'Untitled Workflow',
          blueprintId: response.metadata.blueprint_id,
          agentsCreated: response.metadata?.agents_created || 0,
          agentsReused: response.metadata?.agents_reused || 0,
          usesOrchestrator: response.metadata?.uses_orchestrator || false,
        });
      }

      if (!response.success) {
        setLogs((prev) => [...prev, {
          id: `error-${Date.now()}`,
          phase: "error",
          message: response.error || "Failed to create workflow",
          icon: <AlertCircle className="h-3 w-3 text-red-400" />,
          status: "error",
          timestamp: new Date(),
        }]);
      }
    } catch (err: any) {
      console.error("Builder error:", err);
      const errorMsg = err.message || "Failed to communicate with builder agent";
      
      setLogs((prev) => [...prev, {
        id: `error-${Date.now()}`,
        phase: "error",
        message: errorMsg,
        icon: <AlertCircle className="h-3 w-3 text-red-400" />,
        status: "error",
        timestamp: new Date(),
      }]);

      toast({
        title: "Builder Error",
        description: errorMsg,
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleViewWorkflow = () => {
    if (createdBlueprintId && onWorkflowCreated) {
      onWorkflowCreated(createdBlueprintId);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3 }}
      className="mb-4"
    >
      <Card className="bg-background-card shadow-card border-gray-800 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-white">Smart Builder</span>
            <Sparkles className="h-3 w-3 text-primary/60" />
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-6 w-6 p-0 text-gray-400 hover:text-white"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Loading State */}
        {isCheckingSetup && (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="h-4 w-4 animate-spin text-primary mr-2" />
            <span className="text-xs text-gray-400">Checking setup...</span>
          </div>
        )}

        {/* Setup Required */}
        {!isCheckingSetup && !hasBuilderAgent && (
          <div className="p-4">
            <div className="flex items-start gap-3 p-3 bg-orange-900/20 border border-orange-500/30 rounded-lg">
              <Settings className="h-4 w-4 text-orange-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-xs font-medium text-orange-300 mb-1">Setup Required</p>
                <p className="text-xs text-gray-400 mb-2">
                  Create a Builder Agent in Inventory → Agents → Builder Node
                </p>
                <Button
                  size="sm"
                  onClick={() => window.location.href = "/inventory?category=nodes&type=builder_node"}
                  className="bg-primary hover:bg-primary/80 h-6 text-xs"
                >
                  <ExternalLink className="h-3 w-3 mr-1" />
                  Go to Inventory
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Main Interface */}
        {!isCheckingSetup && hasBuilderAgent && (
          <CardContent className="p-3">
            <div className="flex gap-3">
              {/* Left: Input Area */}
              <div className="flex-1 min-w-0">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Describe your workflow..."
                    className="flex-1 h-8 px-3 text-sm bg-background-dark border border-gray-700 rounded-md focus:border-primary focus:outline-none text-gray-100 placeholder-gray-500"
                    disabled={isProcessing}
                  />
                  <Button
                    onClick={handleSend}
                    disabled={!inputValue.trim() || isProcessing}
                    size="sm"
                    className="bg-primary hover:bg-primary/80 h-8 px-3"
                  >
                    {isProcessing ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                {logs.length === 0 && !isProcessing && (
                  <p className="text-xs text-gray-500 mt-1.5">
                    e.g., "Search Jira" • "Confluence lookup" • "Sales with CRM"
                  </p>
                )}
                
                {/* Workflow Result - Below input when complete */}
                {workflowResult && (
                  <motion.div 
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-3 p-2.5 rounded-lg bg-emerald-900/20 border border-emerald-600/40"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <Workflow className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                        <span className="text-xs font-medium text-emerald-400 truncate">
                          {workflowResult.workflowName}
                        </span>
                      </div>
                      <Button
                        size="sm"
                        onClick={handleViewWorkflow}
                        className="h-6 text-xs bg-emerald-600 hover:bg-emerald-700 flex-shrink-0"
                      >
                        View
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs text-gray-400 mt-1.5">
                      {(workflowResult.agentsCreated ?? 0) > 0 && (
                        <span><span className="text-emerald-400">+{workflowResult.agentsCreated}</span> created</span>
                      )}
                      {(workflowResult.agentsReused ?? 0) > 0 && (
                        <span><span className="text-blue-400">{workflowResult.agentsReused}</span> reused</span>
                      )}
                      {workflowResult.usesOrchestrator && (
                        <span className="text-purple-400">+orchestrator</span>
                      )}
                    </div>
                  </motion.div>
                )}
              </div>

              {/* Right: Progress Logs with scrollbar */}
              {logs.length > 0 && (
                <div className="w-48 flex-shrink-0 max-h-[120px] overflow-y-auto border-l border-gray-800 pl-3">
                  <div className="space-y-0.5">
                    {logs.map((log) => (
                      <motion.div
                        key={log.id}
                        initial={{ opacity: 0, x: 5 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="flex items-center gap-1.5"
                      >
                        <div className={`flex-shrink-0 ${
                          log.status === "running" ? "text-primary" :
                          log.status === "error" ? "text-red-400" : "text-emerald-400"
                        }`}>
                          {log.status === "running" ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : log.status === "error" ? (
                            <AlertCircle className="h-3 w-3" />
                          ) : (
                            <CheckCircle2 className="h-3 w-3" />
                          )}
                        </div>
                        <span className={`text-xs truncate ${
                          log.phase === "request" ? "text-white" :
                          log.status === "error" ? "text-red-300" :
                          log.status === "running" ? "text-gray-300" : "text-gray-500"
                        }`}>
                          {log.phase === "request" 
                            ? log.message.length > 20 ? log.message.substring(0, 20) + "..." : log.message
                            : log.message}
                        </span>
                      </motion.div>
                    ))}
                    <div ref={logsEndRef} />
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        )}
      </Card>
    </motion.div>
  );
}
