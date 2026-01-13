import React, { useState, useRef, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import {
  Send,
  Sparkles,
  Loader2,
  Bot,
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
  executeBuilderRequestStreaming,
  checkBuilderAgentExists,
  BuilderSession,
  BuilderPhaseEvent,
  BuilderStreamEvent,
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

// Phase status type
type PhaseStatus = 'pending' | 'running' | 'complete' | 'error';

export default function SmartBuilderPanel({
  isOpen,
  onClose,
  onWorkflowCreated,
}: SmartBuilderPanelProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [session, setSession] = useState<BuilderSession | null>(null);
  const [isCheckingSetup, setIsCheckingSetup] = useState(true);
  const [hasBuilderAgent, setHasBuilderAgent] = useState(false);
  const [builderAgentInfo, setBuilderAgentInfo] = useState<any>(null);
  const [phaseStatuses, setPhaseStatuses] = useState<Record<string, PhaseStatus>>({
    analyze: 'pending',
    search: 'pending',
    design: 'pending',
    validate: 'pending',
  });
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
      setInputValue("");
      setSession(null);
      setIsProcessing(false);
      setPhaseStatuses({
        analyze: 'pending',
        search: 'pending',
        design: 'pending',
        validate: 'pending',
      });
    }
  }, [isOpen]);

  // Scroll to bottom within the logs container only (not the whole page)
  const logsContainerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Add a log entry with timestamp
  const addLog = useCallback((phase: string, message: string, status: LogEntry["status"] = "running") => {
    const icon = status === "running" 
      ? <Loader2 className="h-3 w-3 animate-spin" />
      : status === "complete" 
        ? <CheckCircle2 className="h-3 w-3 text-emerald-400" />
        : <AlertCircle className="h-3 w-3 text-red-400" />;
    
    setLogs((prev) => [...prev, {
      id: `${phase}-${Date.now()}`,
      phase,
      message,
      icon,
      status,
      timestamp: new Date(),
    }]);
  }, []);

  const handleSend = async () => {
    if (!inputValue.trim() || isProcessing) return;

    const userRequest = inputValue.trim();
    setInputValue("");
    setIsProcessing(true);
    setLogs([]);
    // Reset phase statuses
    setPhaseStatuses({
      analyze: 'pending',
      search: 'pending',
      design: 'pending',
      validate: 'pending',
    });

    try {
      let currentSession = session;
      if (!currentSession) {
        if (!builderAgentInfo?.rid) {
          throw new Error("Builder agent not found. Create one in Inventory → Agents first.");
        }
        const userId = user?.username || "default";
        
        currentSession = await createBuilderSession(userId, builderAgentInfo);
        setSession(currentSession);
      }

      // Handle streaming phase events - update phase status indicators
      const handlePhaseEvent = (event: BuilderPhaseEvent) => {
        if (event.status === 'started') {
          setPhaseStatuses(prev => ({ ...prev, [event.phase]: 'running' }));
        } else if (event.status === 'complete') {
          setPhaseStatuses(prev => ({ ...prev, [event.phase]: 'complete' }));
        } else if (event.status === 'failed') {
          setPhaseStatuses(prev => ({ ...prev, [event.phase]: 'error' }));
          addLog('error', `Phase failed: ${event.message}`, 'error');
        }
      };

      // Handle completion
      const handleComplete = (response: { success: boolean; output: string }) => {
        if (response.success) {
          addLog("complete", "✓ Workflow created successfully!", "complete");
          
          // Notify parent to refresh workflows list
          if (onWorkflowCreated) {
            onWorkflowCreated("refresh");
          }
        } else {
          addLog("error", "Failed to create workflow", "error");
        }
        setIsProcessing(false);
      };

      // Handle error
      const handleError = (errorMsg: string) => {
        setLogs(prev => [...prev, {
          id: `error-${Date.now()}`,
          phase: "error",
          message: errorMsg,
          icon: <AlertCircle className="h-3 w-3 text-red-400" />,
          status: "error" as const,
          timestamp: new Date(),
        }]);
        
        toast({
          title: "Builder Error",
          description: errorMsg,
          variant: "destructive",
        });
        setIsProcessing(false);
      };

      // Handle detailed stream events with human-friendly messages
      const handleStreamEvent = (event: BuilderStreamEvent) => {
        if (event.type === 'tool_result' && event.output) {
          const output = event.output;
          const tool = (event as any).tool;
          
          // Generate human-friendly messages based on tool type
          let message = '';
          
          if (tool === 'analyze_request') {
            const intent = output.intent || 'workflow';
            const caps = output.required_capabilities?.join(', ') || 'general';
            message = `Understanding: ${intent.substring(0, 40)}... (needs: ${caps})`;
          } else if (tool === 'search_resources') {
            const llmCount = output.llms?.length || 0;
            const agentCount = output.existing_agents?.length || 0;
            const providerCount = output.matched_providers?.length || 0;
            message = `Found ${llmCount} LLM${llmCount !== 1 ? 's' : ''}, ${agentCount} agent${agentCount !== 1 ? 's' : ''}, ${providerCount} provider${providerCount !== 1 ? 's' : ''}`;
          } else if (tool === 'generate_blueprint') {
            const name = output.blueprint?.name || output.name || 'workflow';
            message = `Designed "${name}" workflow`;
          } else if (tool === 'validate_blueprint') {
            if (output.is_valid) {
              message = 'Validation passed ✓';
            } else {
              const errorCount = output.errors?.length || 0;
              message = `Validation: ${errorCount} issue${errorCount !== 1 ? 's' : ''} found`;
            }
          } else if (tool === 'save_blueprint') {
            const name = output.name || 'Workflow';
            message = `Saved "${name}" successfully`;
          } else if (tool === 'preview_workflow') {
            message = 'Preview ready';
          } else {
            // Fallback for unknown tools
            message = output.success ? 'Step completed' : 'Step finished';
          }
          
          if (message) {
            addLog('info', message, 'complete');
          }
        }
      };

      // Execute with streaming
      await executeBuilderRequestStreaming(
        currentSession.sessionId,
        userRequest,
        handlePhaseEvent,
        handleComplete,
        handleError,
        handleStreamEvent
      );

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
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
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
        {/* Header with Current Phase */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-white">Smart Builder</span>
            {isProcessing && (() => {
              // Find current running phase or last completed
              const phases = ['analyze', 'search', 'design', 'validate'] as const;
              const labels = { analyze: 'Analyzing', search: 'Searching', design: 'Designing', validate: 'Saving' };
              const runningPhase = phases.find(p => phaseStatuses[p] === 'running');
              const completedCount = phases.filter(p => phaseStatuses[p] === 'complete').length;
              
              if (runningPhase) {
                return (
                  <span className="text-xs text-primary animate-pulse ml-2 flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    {labels[runningPhase]}... ({completedCount}/4)
                  </span>
                );
              } else if (completedCount === 4) {
                return (
                  <span className="text-xs text-emerald-400 ml-2 flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Complete
                  </span>
                );
              } else if (completedCount > 0) {
                return (
                  <span className="text-xs text-gray-400 ml-2">
                    Step {completedCount}/4
                  </span>
                );
              }
              return (
                <span className="text-xs text-gray-500 ml-2 flex items-center gap-1">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Starting...
                </span>
              );
            })()}
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
            {/* Input Area - transforms to Log Display during processing */}
            {isProcessing ? (
              /* Log Display Mode - shows tool results and details */
              <div 
                ref={logsContainerRef}
                className="bg-[#0d0d1a] border border-gray-700 rounded-lg p-2 max-h-[80px] overflow-y-auto font-mono"
              >
                <div className="space-y-0.5">
                  {logs.length === 0 ? (
                    <div className="flex items-center gap-2 text-gray-500 text-xs">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      <span>Starting...</span>
                    </div>
                  ) : logs.map((log) => (
                    <motion.div
                      key={log.id}
                      initial={{ opacity: 0, x: -5 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="flex items-center gap-1.5"
                    >
                      <span className="text-gray-500 text-xs w-16 flex-shrink-0">
                        {log.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
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
                      <span className={`text-xs ${
                        log.message.includes('✓') || log.message.includes('🎉') ? 'text-emerald-400' :
                        log.status === "error" ? "text-red-300" :
                        log.status === "running" ? "text-gray-300" : "text-gray-400"
                      }`}>
                        {log.message}
                      </span>
                    </motion.div>
                  ))}
                </div>
              </div>
            ) : (
              /* Normal Input Mode */
              <div className="flex-1 min-w-0">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Describe your workflow..."
                    className="flex-1 h-8 px-3 text-sm bg-background-dark border border-gray-700 rounded-md focus:border-primary focus:outline-none text-gray-100 placeholder-gray-500"
                  />
                  <Button
                    onClick={handleSend}
                    disabled={!inputValue.trim()}
                    size="sm"
                    className="bg-primary hover:bg-primary/80 h-8 px-3"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-gray-500 mt-1.5">
                  e.g., "Search Jira" • "Confluence lookup" • "Sales with CRM"
                </p>
              </div>
            )}
          </CardContent>
        )}
      </Card>
    </motion.div>
  );
}
