import React, { useState, useEffect } from "react";
import * as Switch from '@radix-ui/react-switch';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, Users, Clock, ArrowUpRight, SplitSquareVertical } from "lucide-react";
import ChatInterface from "./chat/ChatInterface";
import ExecutionStream from "./ExecutionStream";
import ReactFlowGraph from "./graphs/ReactFlowGraph";
import { GraphNode } from "../../pages/AgenticAI"
import axios, { AXIOS_AGENTS_IP } from '../../http/axiosAgentConfig'
import { useStreamingData } from './StreamingDataContext'
import { EnhancedStreamReader } from '@/components/shared/stream/StreamJsonParser'
import { useAuth } from "@/contexts/AuthContext";

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

type ChunkData = {
  node: string;
  type: 'llm_token' | 'complete' | 'tool_calling' | 'tool_result';
  chunk?: string;
  tool?: string;
  output?: string;
  call_id?: string;
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
      const blueprintId = sessionData.blueprint_id
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
    
    // TODO: For now, using a placeholder - replace with your actual user ID logic
    const userId = user; // Replace with actual userId
    fetchChatSessions(userId);
  };

  // Initialize component with API call
  useEffect(() => {
    // TODO: For now, using a placeholder - replace with your actual user ID logic
    const userId = user?.username || "default"; // Replace with actual userId
    fetchChatSessions(userId);
  }, []);

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
    const { node, type, chunk, state, tool, output, call_id } = chunkData;
    const currentText = chunk ?? state?.user_prompt ?? '';
    const map = nodeListRef.current;
  
    let existing = map.get(node);
  
    // Initialize the node entry if it doesn't exist
    if (!existing) {
      existing = {
        node_name: node,
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
            existing.tools?.push({ id: call_id, name: tool });
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
                <CardHeader className="py-3 px-4 border-b border-gray-800">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-sm font-medium">
                      Available Chats ({chatSessions.length})
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      {/* Global Scope Toggle */}
                      <Switch.Root
                        className="relative w-24 h-6 rounded-full bg-gray-600 data-[state=checked]:bg-[#03DAC6] transition-colors cursor-pointer"
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
                          className="absolute top-[2px] left-[2px] h-5 w-5 rounded-full bg-white transition-transform duration-300 z-10 transform data-[state=checked]:translate-x-[72px]"
                        />
                      </Switch.Root>
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                        <Users className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-0 flex-grow overflow-y-auto">
                  {chatSessions.length === 0 ? (
                    <div className="p-4 text-center text-gray-400 text-sm">
                      No chat sessions available
                    </div>
                  ) : (
                    <div className="py-2">
                      {chatSessions.map((session) => (
                        <motion.div
                          key={session.id}
                          className={`px-4 py-3 border-l-2 cursor-pointer ${
                            selectedSession?.id === session.id
                              ? "border-[#8A2BE2] bg-[#8A2BE2] bg-opacity-10"
                              : "border-transparent hover:bg-background-surface"
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
                <ReactFlowGraph 
                  blueprintId={selectedSession.blueprintId}
                  height="100%"
                  showControls={true}
                  showMiniMap={false}
                  showBackground={true}
                  interactive={true}
                  isLiveRequest={isLiveRequest}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                  {selectedSession ? 'No blueprint available for this session' : 'Select a chat session to view blueprint'}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}