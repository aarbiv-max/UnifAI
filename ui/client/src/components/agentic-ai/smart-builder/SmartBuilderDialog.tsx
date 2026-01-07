import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Sparkles,
  Search,
  Layers,
  CheckCircle2,
  Circle,
  Loader2,
  AlertCircle,
  Bot,
  ArrowRight,
  Workflow,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import {
  createBuilderSession,
  executeBuilderRequest,
  checkBuilderAgentExists,
  BuilderSession,
  BuilderExecuteResponse,
} from "@/api/agentic";
import { Settings, ExternalLink } from "lucide-react";

interface SmartBuilderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onWorkflowCreated?: (blueprintId: string) => void;
}

interface Phase {
  id: string;
  name: string;
  icon: React.ReactNode;
  description: string;
  status: "pending" | "in_progress" | "complete" | "error";
}

interface Message {
  id: string;
  content: string;
  sender: "user" | "ai";
  isPhaseUpdate?: boolean;
}

const initialPhases: Phase[] = [
  {
    id: "analyze",
    name: "Analyze",
    icon: <Sparkles className="h-4 w-4" />,
    description: "Understanding your requirements",
    status: "pending",
  },
  {
    id: "search",
    name: "Search",
    icon: <Search className="h-4 w-4" />,
    description: "Finding available resources",
    status: "pending",
  },
  {
    id: "design",
    name: "Design",
    icon: <Layers className="h-4 w-4" />,
    description: "Creating workflow structure",
    status: "pending",
  },
  {
    id: "validate",
    name: "Validate",
    icon: <CheckCircle2 className="h-4 w-4" />,
    description: "Verifying and saving",
    status: "pending",
  },
];

export default function SmartBuilderDialog({
  open,
  onOpenChange,
  onWorkflowCreated,
}: SmartBuilderDialogProps) {
  const [phases, setPhases] = useState<Phase[]>(initialPhases);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [session, setSession] = useState<BuilderSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createdBlueprintId, setCreatedBlueprintId] = useState<string | null>(null);
  const [isCheckingSetup, setIsCheckingSetup] = useState(true);
  const [hasBuilderAgent, setHasBuilderAgent] = useState(false);
  const [builderAgentInfo, setBuilderAgentInfo] = useState<any>(null);
  const [availableLlms, setAvailableLlms] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { user } = useAuth();
  const { toast } = useToast();

  // Check if builder agent exists when dialog opens
  useEffect(() => {
    if (open) {
      setIsCheckingSetup(true);
      const userId = user?.username || "default";
      
      checkBuilderAgentExists(userId)
        .then((result) => {
          setHasBuilderAgent(result.exists);
          setBuilderAgentInfo(result.builderAgent);
          setAvailableLlms(result.llms || []);
          setIsCheckingSetup(false);
          
          // If builder exists, show welcome message
          if (result.exists) {
            setMessages([
              {
                id: "welcome",
                content:
                  "Hi! I'm the **Smart Builder Agent**. Tell me what kind of workflow you want to create, and I'll build it for you.\n\nFor example:\n- *\"Create a workflow to search Jira and summarize tickets\"*\n- *\"Build an agent that uses Confluence for documentation lookup\"*\n- *\"I need a sales assistant that can access customer data\"*",
                sender: "ai",
              },
            ]);
          }
        })
        .catch((err) => {
          console.error("Error checking builder agent:", err);
          setIsCheckingSetup(false);
          setHasBuilderAgent(false);
        });
      
      // Reset other state
      setPhases(initialPhases);
      setInputValue("");
      setSession(null);
      setError(null);
      setCreatedBlueprintId(null);
      setIsProcessing(false);
    }
  }, [open, user]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Update phases based on completed phases from response
  const updatePhasesFromResponse = useCallback((completedPhases: string[]) => {
    setPhases((prev) =>
      prev.map((phase) => {
        if (completedPhases.includes(phase.id)) {
          return { ...phase, status: "complete" };
        }
        // Find the next phase after completed ones
        const lastCompletedIndex = prev.findIndex(
          (p) => !completedPhases.includes(p.id) && p.status !== "complete"
        );
        if (phase.id === prev[lastCompletedIndex]?.id && completedPhases.length > 0) {
          return { ...phase, status: "in_progress" };
        }
        return phase;
      })
    );
  }, []);

  // Simulate phase progression for visual feedback
  const simulatePhaseProgression = useCallback(() => {
    const phaseOrder = ["analyze", "search", "design", "validate"];
    let currentIndex = 0;

    const interval = setInterval(() => {
      if (currentIndex < phaseOrder.length) {
        setPhases((prev) =>
          prev.map((phase, idx) => {
            if (idx < currentIndex) {
              return { ...phase, status: "complete" };
            }
            if (idx === currentIndex) {
              return { ...phase, status: "in_progress" };
            }
            return phase;
          })
        );
        currentIndex++;
      } else {
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const handleSend = async () => {
    if (!inputValue.trim() || isProcessing) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: "user",
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsProcessing(true);
    setError(null);

    // Reset phases for new request
    setPhases(initialPhases.map((p, i) => 
      i === 0 ? { ...p, status: "in_progress" } : p
    ));

    try {
      // Create session if not exists
      let currentSession = session;
      if (!currentSession) {
        if (!builderAgentInfo?.rid) {
          throw new Error("Builder agent not found. Please create one in your inventory first.");
        }
        const userId = user?.username || "default";
        currentSession = await createBuilderSession(userId, builderAgentInfo);
        setSession(currentSession);
      }

      // Start phase simulation for visual feedback
      const cleanup = simulatePhaseProgression();

      // Execute the builder request
      const response: BuilderExecuteResponse = await executeBuilderRequest(
        currentSession.sessionId,
        userMessage.content
      );

      // Stop simulation
      cleanup();

      // Update phases based on actual response
      if (response.metadata?.phases_completed) {
        updatePhasesFromResponse(response.metadata.phases_completed);
      } else {
        // Mark all as complete if we got a response
        setPhases((prev) => prev.map((p) => ({ ...p, status: "complete" })));
      }

      // Check for blueprint creation
      if (response.metadata?.blueprint_id) {
        setCreatedBlueprintId(response.metadata.blueprint_id);
      }

      // Add AI response
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.success
          ? response.output || "Workflow created successfully!"
          : response.error || "Failed to create workflow. Please try again.",
        sender: "ai",
      };
      setMessages((prev) => [...prev, aiMessage]);

      if (!response.success) {
        setError(response.error || "Unknown error occurred");
        setPhases((prev) =>
          prev.map((p) =>
            p.status === "in_progress" ? { ...p, status: "error" } : p
          )
        );
      }
    } catch (err: any) {
      console.error("Builder error:", err);
      const errorMsg = err.message || "Failed to communicate with builder agent";
      setError(errorMsg);
      setPhases((prev) =>
        prev.map((p) =>
          p.status === "in_progress" ? { ...p, status: "error" } : p
        )
      );

      // Special handling for missing LLM
      const isNoLlmError = errorMsg.includes("No LLM");
      const displayMessage = isNoLlmError
        ? "**Setup Required**: You need to add an LLM resource to your inventory before using the Smart Builder.\n\nGo to **Inventory → LLMs** and add at least one LLM (e.g., OpenAI GPT-4, Gemini, etc.)."
        : `Sorry, I encountered an error: ${errorMsg}. Please try again.`;

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: displayMessage,
        sender: "ai",
      };
      setMessages((prev) => [...prev, errorMessage]);

      toast({
        title: isNoLlmError ? "LLM Required" : "Builder Error",
        description: isNoLlmError ? "Add an LLM in your inventory first" : errorMsg,
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
      onOpenChange(false);
    }
  };

  const getPhaseStatusIcon = (status: Phase["status"]) => {
    switch (status) {
      case "complete":
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
      case "in_progress":
        return <Loader2 className="h-4 w-4 text-primary animate-spin" />;
      case "error":
        return <AlertCircle className="h-4 w-4 text-red-400" />;
      default:
        return <Circle className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl h-[80vh] flex flex-col p-0 gap-0 bg-[#1a1a2e] border-gray-700 shadow-2xl">
        <DialogHeader className="px-6 py-4 border-b border-gray-700 flex-shrink-0 bg-[#16162a]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-br from-primary/30 to-purple-600/30 border border-primary/40">
              <Bot className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle className="text-xl font-bold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
                Smart Builder Agent
              </DialogTitle>
              <DialogDescription className="text-gray-400 text-sm">
                Describe your workflow and I'll build it for you
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Loading State */}
        {isCheckingSetup && (
          <div className="flex-1 flex items-center justify-center bg-[#1a1a2e]">
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
              <p className="text-gray-400">Checking setup...</p>
            </div>
          </div>
        )}

        {/* Setup Required Screen */}
        {!isCheckingSetup && !hasBuilderAgent && (
          <div className="flex-1 flex items-center justify-center p-8 bg-[#1a1a2e]">
            <div className="max-w-md text-center">
              <div className="p-4 rounded-full bg-orange-900/30 border border-orange-500/50 w-fit mx-auto mb-6">
                <Settings className="h-10 w-10 text-orange-400" />
              </div>
              
              <h3 className="text-xl font-bold text-white mb-3">
                Setup Required
              </h3>
              
              <p className="text-gray-400 mb-6">
                To use the Smart Builder, you need to create a <strong className="text-white">Builder Agent</strong> in your inventory first.
              </p>
              
              <div className="bg-[#252542] border border-gray-600 rounded-lg p-4 mb-6 text-left">
                <h4 className="text-sm font-semibold text-white mb-3">How to set up:</h4>
                <ol className="text-sm text-gray-400 space-y-2">
                  <li className="flex gap-2">
                    <span className="text-primary font-bold">1.</span>
                    Go to <strong className="text-white">Inventory → Agents</strong>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-primary font-bold">2.</span>
                    Click <strong className="text-white">Add Resource</strong>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-primary font-bold">3.</span>
                    Select <strong className="text-white">Builder Node</strong> type
                  </li>
                  <li className="flex gap-2">
                    <span className="text-primary font-bold">4.</span>
                    Choose an <strong className="text-white">LLM</strong> for the builder
                  </li>
                  <li className="flex gap-2">
                    <span className="text-primary font-bold">5.</span>
                    Save and return here
                  </li>
                </ol>
              </div>
              
              {availableLlms.length === 0 && (
                <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-3 mb-6">
                  <p className="text-sm text-red-300">
                    ⚠️ You also need at least one <strong>LLM</strong> in your inventory.
                  </p>
                </div>
              )}
              
              <div className="flex gap-3 justify-center">
                <Button
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  className="border-gray-600"
                >
                  Close
                </Button>
                <Button
                  onClick={() => {
                    window.location.href = "/inventory?category=nodes&type=builder_node";
                  }}
                  className="bg-primary hover:bg-primary/80"
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Go to Inventory
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Main Chat Interface - Only shown when builder agent exists */}
        {!isCheckingSetup && hasBuilderAgent && (
          <>
            {/* Phase Progress Bar */}
            <div className="px-6 py-4 border-b border-gray-700 bg-[#1e1e38] flex-shrink-0">
              <div className="flex items-center justify-between">
                {phases.map((phase, index) => (
              <React.Fragment key={phase.id}>
                <div className="flex items-center gap-2">
                  <div
                    className={`
                      p-2 rounded-full transition-all duration-300
                      ${phase.status === "complete" ? "bg-emerald-900 border border-emerald-500" : ""}
                      ${phase.status === "in_progress" ? "bg-purple-900 border border-primary" : ""}
                      ${phase.status === "error" ? "bg-red-900 border border-red-500" : ""}
                      ${phase.status === "pending" ? "bg-gray-800 border border-gray-600" : ""}
                    `}
                  >
                    {getPhaseStatusIcon(phase.status)}
                  </div>
                  <div className="hidden sm:block">
                    <p
                      className={`text-sm font-medium ${
                        phase.status === "complete"
                          ? "text-emerald-400"
                          : phase.status === "in_progress"
                          ? "text-primary"
                          : phase.status === "error"
                          ? "text-red-400"
                          : "text-gray-500"
                      }`}
                    >
                      {phase.name}
                    </p>
                    <p className="text-xs text-gray-500">{phase.description}</p>
                  </div>
                </div>
                {index < phases.length - 1 && (
                  <ArrowRight
                    className={`h-4 w-4 mx-2 ${
                      phases[index + 1].status !== "pending"
                        ? "text-primary"
                        : "text-gray-600"
                    }`}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 min-h-0 bg-[#1a1a2e]">
          <AnimatePresence>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className={`flex ${
                  message.sender === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl p-4 ${
                    message.sender === "user"
                      ? "bg-primary text-white rounded-tr-none"
                      : "bg-[#252542] border border-gray-600 rounded-tl-none"
                  }`}
                >
                  {message.sender === "ai" ? (
                    <div className="prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {isProcessing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-[#252542] border border-gray-600 rounded-2xl rounded-tl-none p-4">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span className="text-sm text-gray-300">
                    Building your workflow...
                  </span>
                </div>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Created Workflow Banner */}
        {createdBlueprintId && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mx-6 mb-4 p-4 rounded-lg bg-emerald-950 border border-emerald-600"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Workflow className="h-5 w-5 text-emerald-400" />
                <div>
                  <p className="text-sm font-medium text-emerald-400">
                    Workflow Created Successfully!
                  </p>
                  <p className="text-xs text-gray-400">
                    Your workflow is ready to use
                  </p>
                </div>
              </div>
              <Button
                size="sm"
                onClick={handleViewWorkflow}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                View Workflow
              </Button>
            </div>
          </motion.div>
        )}

        {/* Input Area */}
        <div className="p-4 border-t border-gray-700 flex-shrink-0 bg-[#16162a]">
          <div className="flex gap-3">
            <Textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe the workflow you want to create..."
              className="flex-1 min-h-[60px] max-h-[120px] resize-none bg-[#252542] border-gray-600 focus:border-primary text-gray-100"
              disabled={isProcessing}
            />
            <Button
              onClick={handleSend}
              disabled={!inputValue.trim() || isProcessing}
              className="self-end bg-primary hover:bg-primary/80 px-6"
            >
              {isProcessing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

