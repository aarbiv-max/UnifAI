import React, { useState, useEffect } from "react";
import * as Switch from '@radix-ui/react-switch';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, Users, Clock, ArrowUpRight, SplitSquareVertical, Trash2, Plus, X } from "lucide-react";
import ChatInterface from "./chat/ChatInterface";
import ExecutionStream from "./ExecutionStream";
import ReactFlowGraph from "./graphs/ReactFlowGraph";
import { GraphNode } from "../../pages/AgenticAI"
import axios from '../../http/axiosAgentConfig'
import { useStreamingData } from './StreamingDataContext'
import { EnhancedStreamReader } from '@/components/shared/stream/StreamJsonParser'
import { useAuth } from "@/contexts/AuthContext";
import AvailableFlows from "./AvailableFlows";
import { ReactFlowProvider } from "reactflow";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";
import { GraphFlow, FlowObject } from "./graphs/interfaces";

// Types for the API response
interface ChatMessage {
  content: string;
  role: 'user' | 'assistant';
}

interface ChatSessionData {
  metadata: Record<string, any>;
  blueprint_id: string;
  session_id: string;
  started_at: string;
  blueprint_exists: boolean;
  state: {
    final_output: string;
    messages: ChatMessage[];
  };
}

interface ChatSession {
  id: string;
  blueprintId: string;
  title: string;
  lastActive: string;
  timestamp: Date;
  preview: string;
  messages: ChatMessage[];
  blueprintExists: boolean;
}

export type SessionPayload = {
  sessionId: string;
  inputs: {"user_prompt": string},
  stream: boolean,
  scope: 'public' | 'private';
  loggedInUser: string;
};

type ExecutionTabProps = {
  runId: string | null;
};

// Custom Dialog components for full opacity overlay (only for Add Flow Modal)
const CustomDialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-black data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
  />
));
CustomDialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

const CustomDialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <DialogPrimitive.Portal>
    <CustomDialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg",
        className
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPrimitive.Portal>
));
CustomDialogContent.displayName = DialogPrimitive.Content.displayName;

type ChunkData = {
  node: string;
  display_name: string;
  type: 'llm_token' | 'complete' | 'tool_calling' | 'tool_result';
  chunk?: string;
  tool?: string;
  output?: string;
  call_id?: string;
  args?: Record<string, any>;
  state?: {
    user_prompt?: string;
  };
};

export default function ExecutionTab({
  runId
}: ExecutionTabProps): React.ReactElement {
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<ChatSession | null>(null);
  const [currentSessionMessages, setCurrentSessionMessages] = useState<ChatMessage[]>([]);
  const [showExecutionStream, setShowExecutionStream] = useState(false);
  const [isActiveChatSession, setIsActiveChatSession] = useState(true);
  const [isLiveRequest, setIsLiveRequest] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [globalScope, setGlobalScope] = useState<'public' | 'private'>('public');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [chatToDelete, setChatToDelete] = useState<ChatSession | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showAddFlowModal, setShowAddFlowModal] = useState(false);
  const [selectedFlowForModal, setSelectedFlowForModal] = useState<FlowObject | null>(null);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [isLoadingFlowsForModal, setIsLoadingFlowsForModal] = useState(false);

  const { nodeListRef, forceUpdate } = useStreamingData();
  const { user } = useAuth();

  // Utility functions
  const generateRandomId = (): string => {
    return `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  };

  const generateRandomTitle = (index: number): string => {
    return `Chat ${index + 1}`;
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInMs = now.getTime() - date.getTime();
    const diffInMinutes = Math.floor(diffInMs / (1000 * 60));
    const diffInHours = Math.floor(diffInMinutes / 60);
    const diffInDays = Math.floor(diffInHours / 24);

    if (diffInMinutes < 60) {
      return `${diffInMinutes} min ago`;
    } else if (diffInHours < 24) {
      return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
    } else if (diffInDays < 7) {
      return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const handleGlobalScopeToggle = () => {
    setGlobalScope(prevScope => prevScope === 'public' ? 'private' : 'public');
  };

  const getPreviewText = (messages: ChatMessage[]): string => {
    const userMessage = messages.find(msg => msg.role === 'user');
    if (userMessage && userMessage.content) {
      return userMessage.content.length > 50
        ? `${userMessage.content.substring(0, 50)}...`
        : userMessage.content;
    }
    return 'No message content available';
  };

  const transformApiDataToSessions = (apiData: ChatSessionData[]): ChatSession[] => {
    return apiData.map((sessionData, index) => {
      const title = sessionData.metadata?.title || generateRandomTitle(index);
      const id = sessionData.session_id || generateRandomId();
      const blueprintId = sessionData.blueprint_id;
      const blueprintExists = sessionData.blueprint_exists;
      const timestamp = new Date(sessionData.started_at);
      const lastActive = formatTimestamp(sessionData.started_at);
      const preview = getPreviewText(sessionData.state.messages);
      
      return {
        id,
        blueprintId,
        title,
        lastActive,
        timestamp,
        preview,
        messages: sessionData.state.messages,
        blueprintExists,  
      };
    });
  };

  // Fetch chat sessions from API
  const fetchChatSessions = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const userId = user?.username || "default";
      const response = await axios.get(`/sessions/session.user.chat.get?userId=${userId}`);
      const transformedSessions = transformApiDataToSessions(response.data);

      // sort chat sessions based on the latest date
      setChatSessions(transformedSessions.sort((firstSession, secondSession) => secondSession.timestamp.getTime() - firstSession.timestamp.getTime()));

      // Auto-select the first session if available
      if (transformedSessions.length > 0 && !selectedSession) {
        const firstSession = transformedSessions[0];
        setSelectedSession(firstSession);
        setCurrentSessionMessages(firstSession.messages);
      }
    } catch (err) {
      console.error('Error fetching chat sessions:', err);
      setError('Failed to load chat sessions');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle session selection
  const handleSessionSelect = (session: ChatSession) => {
    setSelectedSession(session);
    setCurrentSessionMessages(session.messages);

    // Refresh chat sessions when a session is selected
    fetchChatSessions();
  };

  // Handle delete chat
  const handleDeleteChat = (session: ChatSession, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent session selection when clicking delete
    setChatToDelete(session);
    setShowDeleteModal(true);
  };

  const confirmDeleteChat = async () => {
    if (!chatToDelete) return;

    setIsDeleting(true);
    try {
      const userId = user?.username || "default";
      await axios.delete(`/sessions/session.delete?sessionId=${chatToDelete.id}`);

      // Remove the deleted session from the list
      setChatSessions(prevSessions => prevSessions.filter(session => session.id !== chatToDelete.id));

      // If the deleted session was selected, clear the selection
      if (selectedSession?.id === chatToDelete.id) {
        setSelectedSession(null);
        setCurrentSessionMessages([]);
      }

      setShowDeleteModal(false);
      setChatToDelete(null);
    } catch (error) {
      console.error('Error deleting chat session:', error);
      // Handle error (you might want to show a toast notification here)
    } finally {
      setIsDeleting(false);
    }
  };

  const cancelDeleteChat = () => {
    setShowDeleteModal(false);
    setChatToDelete(null);
  };

  // Handle add flow modal
  const handleAddFlowClick = () => {
    setShowAddFlowModal(true);
  };

  const handleFlowSelect = (flow: FlowObject | null): void => {
    setSelectedFlowForModal(flow);
  };

  const handleAddFlow = async () => {
    if (!selectedFlowForModal) return;

    setIsCreatingSession(true);
    try {
      const graphId = selectedFlowForModal.id || `graph-${Date.now()}`;

      const selectedBlueprint = {
        blueprintId: graphId,
        userId: user?.username || "default",
      };

      const response = await axios.post(
        "/sessions/user.session.create",
        selectedBlueprint,
      );

      await fetchChatSessions();

      // Auto-select the newly created session
      // Wait a bit for state to update, then find the newest session with matching blueprintId
      setTimeout(() => {
        setChatSessions(prevSessions => {
          const newestSession = prevSessions.find(session => session.blueprintId === graphId);
          if (newestSession) {
            setSelectedSession(newestSession);
            setCurrentSessionMessages(newestSession.messages);
          }
          return prevSessions; // Return unchanged sessions
        });
      }, 100);

      setShowAddFlowModal(false);
      setSelectedFlowForModal(null);
    } catch (error) {
      console.error("Error creating new graph session:", error);
    } finally {
      setIsCreatingSession(false);
    }
  };

  const handleCancelAddFlow = () => {
    setShowAddFlowModal(false);
    setSelectedFlowForModal(null);
    // Force a small delay to ensure proper cleanup of ReactFlow state
    setTimeout(() => {
      // This timeout helps ensure the modal ReactFlow instance is properly unmounted
      // before potentially affecting other ReactFlow instances
    }, 100);
  };

  // Initialize component with API call
  useEffect(() => {
    fetchChatSessions();
  }, []);

  // Cleanup effect when modal closes to prevent ReactFlow state interference
  useEffect(() => {
    if (!showAddFlowModal && selectedFlowForModal) {
      // Reset selected flow when modal closes to ensure clean state
      setSelectedFlowForModal(null);
    }
  }, [showAddFlowModal]);

  // Tracks each node's streaming state.
  // Aggregates chunks per node.
  // Marks a node as DONE when a type: "complete" event is received for it.
  // Cleanly handles streaming via ReadableStream.
  // This follows clean architecture, maintains readability, and ensures correctness even in noisy or unpredictable stream outputs.
  // Extracts multiple well-formed ["custom", {...}] chunks from the stream text.
  const parseStreamChunk = (chunk: string): any[] => {
    const parsedChunks: any[] = [];
    const pattern = /\["custom",\s*(\{.*?\})\]/g;
    let match: RegExpExecArray | null;

    while ((match = pattern.exec(chunk)) !== null) {
      try {
        const json = JSON.parse(match[1]);
        parsedChunks.push(json);
      } catch (e) {
        console.warn("Failed to parse stream JSON chunk:", match[1]);
      }
    }

    return parsedChunks;
  };

  // Maintains and updates a list of nodes and their stream state (PROGRESS or DONE) while aggregating text.
  const updateNodeList = (chunkData: ChunkData) => {
    const { node, display_name, type, chunk, state, tool, output, call_id, args } = chunkData;
    const currentText = chunk ?? state?.user_prompt ?? '';
    const map = nodeListRef.current;

    let existing = map.get(node);

    // Initialize the node entry if it doesn't exist
    if (!existing) {
      existing = {
        node_name: display_name,
        node_uid: node,
        stream: type === 'complete' ? 'DONE' : 'PROGRESS',
        text: '',
        tools: [],
      };
      map.set(node, existing);
    }

    switch (type) {
      case 'llm_token':
        if (chunk) {
          existing.text += chunk;
        }
        break;

      // case 'complete':
      //   existing.stream = 'DONE';
      //   if (state?.user_prompt && existing.text.trim() === '') {
      //     existing.text = state.user_prompt;
      //   }
      //   break;

      case 'tool_calling':
        if (call_id && tool) {
          const existingTool = existing.tools?.find(t => t.id === call_id);
          if (!existingTool) {
            existing.tools?.push({ id: call_id, name: tool, args });
          }
        }
        break;

      case 'tool_result':
        if (call_id && tool && output) {
          const toolEntry = existing.tools?.find(t => t.id === call_id);
          if (toolEntry) {
            toolEntry.output = output;
          } else {
            existing.tools?.push({ id: call_id, name: tool, output });
          }
        }
        break;

      default:
        break;
    }

    // forceUpdate(); // Uncomment if needed to trigger a re-render
  };

  // Reads the stream, decodes it, parses chunks, and updates state cleanly.
  const triggerExecution = async (sessionPayload: SessionPayload) => {
    let streamReader: EnhancedStreamReader | null = null;

    try {
      setIsLiveRequest(true);
      const payloadWithScope = {
        ...sessionPayload,
        scope: globalScope,
        loggedInUser: user?.username || "default",
      };

      const response = await fetch(`/api2/sessions/user.session.execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payloadWithScope),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      if (!response.body) throw new Error('ReadableStream not supported!');

      // Create stream reader with chunk processing callback
      streamReader = new EnhancedStreamReader((chunkData: any) => {
        updateNodeList(chunkData);
        // console.log(JSON.stringify(Array.from(nodeListRef.current.entries()), null, 2));
      });

      // Read the entire stream
      await streamReader.readStream(response);

      console.log('Streaming completed.');
      console.log('Final Node List:', nodeListRef.current);
    } catch (error) {
      console.error('Error communicating with chat API', error);

      // Cancel stream reading if there was an error
      if (streamReader) {
        await streamReader.cancel();
      }
    } finally {
      setIsLiveRequest(false);

      try {
        const session_response = await axios.get(
          `/sessions/session.state.get?sessionId=${sessionPayload.sessionId}`
        );
        return session_response.data.output;
      } catch (error) {
        console.error('Error fetching session state:', error);
        throw error;
      }
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-center items-center h-64">
          <div className="text-gray-400">Loading chat sessions...</div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex justify-center items-center h-64">
          <div className="text-red-400">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-heading font-semibold">AI Assistant</h2>
          <p className="text-sm text-gray-400 mt-1">
            Interact with your AI assistant and monitor execution details
          </p>
        </div>
        <Button
          className={`flex items-center gap-2 ${isActiveChatSession ? "bg-[#03DAC6] hover:bg-opacity-80" : "bg-gray-700 text-gray-300 cursor-not-allowed"}`}
          onClick={() => setShowExecutionStream(!showExecutionStream)}
          disabled={!isActiveChatSession}
        >
          <SplitSquareVertical className="h-4 w-4" />
          {showExecutionStream ? "Hide" : "Open"} Execution Stream
        </Button>
      </div>

      <div className="flex gap-6" style={{ height: "calc(100vh - 230px)" }}>
        {/* Main Content Area - 70% width */}
        <div className="flex-grow" style={{ width: "70%" }}>
          <div className="grid grid-cols-12 gap-6 h-full">
            {/* Chat sessions sidebar */}
            <div className="col-span-12 md:col-span-4 lg:col-span-3">
              <Card className="bg-background-card shadow-card border-gray-800 h-full flex flex-col">
                <CardHeader className="py-3 px-4 border-b border-gray-800 overflow-hidden">
                  <div className="flex justify-between items-center min-w-0 w-full max-w-full">
                    <CardTitle className="text-sm font-medium truncate flex-1 min-w-0 mr-2">
                      Available Chats ({chatSessions.length})
                    </CardTitle>
                    <div className="flex items-center gap-1 flex-shrink-0 max-w-fit">
                      {/* Global Scope Toggle */}
                      <Switch.Root
                        className="relative w-20 h-5 rounded-full bg-gray-600 data-[state=checked]:bg-[#03DAC6] transition-colors cursor-pointer flex-shrink-0"
                        checked={globalScope === 'public'}
                        onCheckedChange={handleGlobalScopeToggle}
                        id="scope-switch"
                        title={`Current scope: ${globalScope}`}
                      >
                        {/* Background label */}
                        <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-white pointer-events-none select-none">
                          {globalScope === 'public' ? 'Public' : 'Private'}
                        </span>

                        {/* Switch thumb */}
                        <Switch.Thumb
                          className="absolute top-[1px] left-[1px] h-4 w-4 rounded-full bg-white transition-transform duration-300 z-10 transform data-[state=checked]:translate-x-[60px]"
                        />
                      </Switch.Root>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0 flex-shrink-0">
                        <Users className="h-3 w-3" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-6 w-6 p-0 text-[#03DAC6] hover:bg-[#03DAC6] hover:bg-opacity-20 flex-shrink-0" 
                        onClick={handleAddFlowClick}
                        title="Add new chat from flow"
                      >
                        <Plus className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-0 flex-grow">
                  {chatSessions.length === 0 ? (
                    <div className="p-4 text-center text-gray-400 text-sm">
                      No chat sessions available
                    </div>
                  ) : (
                    <div className="h-full max-h-[75vh] overflow-y-auto py-2">
                      {chatSessions.map((session) => (
                        <motion.div
                          key={session.id}
                          className={`group px-4 py-3 border-l-2 cursor-pointer ${
                            selectedSession?.id === session.id
                              ? "border-[#8A2BE2] bg-[#8A2BE2] bg-opacity-10"
                              : "border-transparent hover:bg-background-surface"
                          } ${
                            !session.blueprintExists 
                              ? "opacity-50 bg-gray-800/30" 
                              : ""
                          }`}
                          onClick={() => handleSessionSelect(session)}
                          whileHover={{ x: 2 }}
                          transition={{ duration: 0.1 }}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center min-w-0 flex-1">
                              <MessageSquare className="h-4 w-4 mr-2 text-gray-400 flex-shrink-0" />
                              <span className="text-sm font-medium truncate">
                                {session.title}
                              </span>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-gray-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                              onClick={(e) => handleDeleteChat(session, e)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                          <div className="mt-1 flex items-center text-xs text-gray-400">
                            <Clock className="h-3 w-3 mr-1" />
                            <span>{session.lastActive}</span>
                          </div>
                          <p className="mt-1 text-xs text-gray-500 truncate">
                            {session.preview}
                          </p>
                        </motion.div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* ChatInterface with conditional className */}
            <div className={`col-span-12 ${showExecutionStream ? 'md:col-span-4 lg:col-span-4' : 'md:col-span-8 lg:col-span-9'} h-full`}>
              <ChatInterface
                runId={selectedSession?.id || ''}
                triggerExecution={triggerExecution}
                initialMessages={currentSessionMessages}
                blueprintExists={selectedSession?.blueprintExists ?? true}
              />
            </div>

            {/* ExecutionStream only renders when showExecutionStream is true */}
            {selectedSession && showExecutionStream && (
              <div className="col-span-12 md:col-span-4 lg:col-span-5 h-full">
                <ExecutionStream
                  blueprintId={selectedSession.blueprintId}
                  isLiveRequest={isLiveRequest}
                />
              </div>
            )}
          </div>
        </div>

        {/* Blueprint Graph Visualization - 30% width */}
        <div className="flex-shrink-0" style={{ width: "30%" }}>
          <Card className="bg-background-card shadow-card border-gray-800 h-full flex flex-col">
            <CardHeader className="py-3 px-4 border-b border-gray-800">
              {selectedSession && (
                  <div className="mb-4 px-4 py-3 bg-[#8A2BE2] bg-opacity-10 border border-[#8A2BE2] rounded-md">
                    <p className="text-sm">
                      {/* TODO: Add below general component that gets 'blueprintId' and showing his title and uid - can be called from multiple places */}
                      <span className="font-medium">Active Graph:</span> {''} <span className="text-xs text-gray-400 ml-2">(ID: {selectedSession.blueprintId || 'N/A'})</span>
                    </p>
                  </div>
                )}
              {/* {selectedSession && (
                <p className="text-xs text-gray-400 mt-1">
                  Blueprint ID: {selectedSession.blueprintId || 'N/A'}
                </p>
              )} */}
            </CardHeader>
            <CardContent className="p-0 flex-grow">
              {selectedSession?.blueprintId ? (
                <ReactFlowProvider key={`main-graph-${selectedSession.blueprintId}`}>
                  <ReactFlowGraph
                    blueprintId={selectedSession.blueprintId}
                    height="100%"
                    showControls={true}
                    showMiniMap={false}
                    showBackground={true}
                    interactive={true}
                    isLiveRequest={isLiveRequest}
                  />
                </ReactFlowProvider>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                  {selectedSession ? 'No blueprint available for this session' : 'Select a chat session to view blueprint'}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Add Flow Modal */}
      <Dialog open={showAddFlowModal} onOpenChange={setShowAddFlowModal}>
        <CustomDialogContent 
          className="bg-background-card border-gray-800 max-w-[95vw] w-[95vw] h-[85vh] max-h-[85vh] flex flex-col overflow-hidden"
        >
          <DialogHeader className="flex-shrink-0 pb-4">
            <DialogTitle className="text-lg">Add New Chat from Flow</DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0 overflow-hidden">
            <ReactFlowProvider key={`new-chat-graph-${showAddFlowModal}`}>
              <AvailableFlows
                selectedFlow={selectedFlowForModal}
                onFlowSelect={handleFlowSelect}
                showActiveStatus={false}
                showDeleteButton={false}
                height="100%"
                graphProps={{
                  showControls: true,
                  showMiniMap: true,
                  showBackground: true,
                  interactive: true,
                  isLiveRequest: false,
                }}
              />
            </ReactFlowProvider>
          </div>
          <DialogFooter className="flex-shrink-0 pt-4 border-t border-gray-800">
            <Button
              variant="outline"
              onClick={handleCancelAddFlow}
              disabled={isCreatingSession}
              className="bg-background-dark border-gray-700 hover:bg-background-surface"
            >
              Cancel
            </Button>
            <Button
              onClick={handleAddFlow}
              disabled={!selectedFlowForModal || isCreatingSession}
              className="bg-[#03DAC6] hover:bg-opacity-80 text-black"
            >
              {isCreatingSession ? "Creating..." : "Add"}
            </Button>
          </DialogFooter>
        </CustomDialogContent>
      </Dialog>

      {/* Delete Chat Confirmation Modal */}
      <AlertDialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <AlertDialogContent className="bg-background-card border-gray-800">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Chat</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{chatToDelete?.title}"?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel 
              onClick={cancelDeleteChat}
              className="bg-background-dark border-gray-700 hover:bg-background-surface"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDeleteChat}
              disabled={isDeleting}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}