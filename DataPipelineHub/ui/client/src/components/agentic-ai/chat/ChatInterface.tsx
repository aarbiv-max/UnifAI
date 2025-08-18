import React, {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
} from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Trash2, Settings } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import axios from "../../../http/axiosAgentConfig";
import { MarkdownComponents, preprocessText } from "./helpers/TextComponents";
import { SessionPayload } from "../ExecutionTab";
import { useStreamingData } from "../StreamingDataContext";
import { Message, StreamLogEntry } from "./types";
import { StreamLogDisplay } from "./StreamLogDisplay";

// Backend message format
interface BackendMessage {
  content: string;
  role: "user" | "assistant";
}

interface ChatInterfaceProps {
  runId?: string;
  triggerExecution: (sessionPayload: SessionPayload) => Promise<string>;
  initialMessages?: BackendMessage[];
}

export default function ChatInterface({
  runId,
  triggerExecution,
  initialMessages = [],
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [currentStreamingMessageId, setCurrentStreamingMessageId] = useState<
    string | null
  >(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const { nodeListRef, clearStream } = useStreamingData();

  // Transform backend messages to frontend format
  const transformBackendMessagesToFrontend = useCallback(
    (backendMessages: BackendMessage[]): Message[] => {
      return backendMessages.map((msg, index) => ({
        id: `${Date.now()}-${index}`,
        content: msg.content,
        sender: msg.role === "user" ? "user" : "ai",
        // For AI messages, we might want to add finalAnswer if it's the last assistant message
        ...(msg.role === "assistant" && {
          finalAnswer: msg.content,
          streamLogs: [],
        }),
      }));
    },
    [],
  );

  // Initialize messages from props or default
  useEffect(() => {
    if (initialMessages && initialMessages.length > 0) {
      const transformedMessages =
        transformBackendMessagesToFrontend(initialMessages);
      setMessages(transformedMessages);
    } else {
      // Default welcome message when no initial messages
      setMessages([
        {
          id: "welcome",
          content:
            "Hello! I'm your AI assistant. How can I help you process your data today?",
          sender: "ai",
        },
      ]);
    }
  }, [initialMessages, transformBackendMessagesToFrontend]);

  // useEffect(() => {
  //   scrollToBottom();
  // }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Map stream type to status
  const mapStreamToStatus = (
    stream: string,
  ): "processing" | "complete" | "error" => {
    switch (stream) {
      case "PROGRESS":
        return "processing";
      case "ERROR":
        return "error";
      case "COMPLETE":
        return "complete";
      default:
        return "processing";
    }
  };

  // Optimized streaming logic with reduced update frequency
  const startStreamingLogs = (messageId: string) => {
    if (streamingIntervalRef.current) {
      clearInterval(streamingIntervalRef.current);
    }

    let lastUpdateTime = 0;
    const UPDATE_THROTTLE = 300; // Reduced update frequency to 300ms

    streamingIntervalRef.current = setInterval(() => {
      const now = Date.now();
      if (now - lastUpdateTime < UPDATE_THROTTLE) {
        return;
      }

      const list = Array.from(nodeListRef.current.values());

      if (list.length > 0) {
        lastUpdateTime = now;

        setMessages((prevMessages) =>
          prevMessages.map((msg) => {
            if (msg.id === messageId && msg.sender === "ai") {
              const currentLogs = msg.streamLogs || [];
              const updatedStreamLogs: StreamLogEntry[] = [];

              // Process each entry from nodeListRef
              list.forEach((entry) => {
                const existingLog = currentLogs.find(
                  (log) => log.nodeId === entry.node_name,
                );

                // Only update if there's actually a change
                const newStatus = mapStreamToStatus(entry.stream);
                const newMessage = entry.text;

                if (
                  !existingLog ||
                  existingLog.status !== newStatus ||
                  existingLog.message !== newMessage
                ) {
                  if (newMessage) {
                    updatedStreamLogs.push({
                      nodeId: entry.node_name,
                      nodeName: entry.node_name
                        .replace(/_/g, " ")
                        .replace(/\b\w/g, (l) => l.toUpperCase()),
                      message: newMessage,
                      tools: entry?.tools || [],
                      status: newStatus,
                      isExpanded: existingLog?.isExpanded || false,
                    });
                  }
                } else {
                  // Keep existing log unchanged
                  updatedStreamLogs.push(existingLog);
                }
              });

              // Only update if there are actual changes
              const hasChanges =
                updatedStreamLogs.length !== currentLogs.length ||
                updatedStreamLogs.some((log, index) => {
                  const currentLog = currentLogs[index];
                  return (
                    !currentLog ||
                    log.status !== currentLog.status ||
                    log.message !== currentLog.message
                  );
                });

              if (hasChanges) {
                return {
                  ...msg,
                  streamLogs: updatedStreamLogs,
                };
              }
            }
            return msg;
          }),
        );
      }
    }, 100); // Check every 100ms but only update every 300ms
  };

  // Stop streaming logs and mark all as complete
  const stopStreamingLogs = (messageId?: string) => {
    if (streamingIntervalRef.current) {
      clearInterval(streamingIntervalRef.current);
      streamingIntervalRef.current = null;

      // Mark all processing nodes as complete when streaming stops
      const targetMessageId = messageId || currentStreamingMessageId;
      if (targetMessageId) {
        setMessages((prevMessages) =>
          prevMessages.map((msg) => {
            if (msg.id === targetMessageId && msg.sender === "ai") {
              return {
                ...msg,
                streamLogs: msg.streamLogs?.map((log) => ({
                  ...log,
                  status: log.status === "processing" ? "complete" : log.status,
                })),
              };
            }
            return msg;
          }),
        );
      }
    }
  };

  // Toggle expansion of a specific node log
  const toggleNodeExpansion = (messageId: string, nodeId: string) => {
    setMessages((prevMessages) =>
      prevMessages.map((msg) => {
        if (msg.id === messageId) {
          return {
            ...msg,
            streamLogs: msg.streamLogs?.map((log) =>
              log.nodeId === nodeId
                ? { ...log, isExpanded: !log.isExpanded }
                : log,
            ),
          };
        }
        return msg;
      }),
    );
  };

  const getSessionState = async (sid: string) => {
    try {
      // Make API call to get the session state
      const response = await axios.get(
        `/session.state.get?sessionId=${sid}`,
      );
      const data = response.data;

      if (data && data.response) {
        return data.response;
      }

      return "I'm sorry, I couldn't retrieve a response for your query.";
    } catch (error) {
      console.error("Failed to get session state:", error);
      return "I'm sorry, I couldn't retrieve a response for your query.";
    }
  };

  // User sends message → Creates an AI message with empty streamLogs
  // Streaming starts → Interval polls for node updates and updates the message
  // Live updates → Each node appears/updates as data becomes available
  // User interaction → Can expand/collapse individual node logs
  // Completion → Final answer appears and streaming stops
  // Cleanup → All intervals are properly cleared
  const handleSendMessage = async () => {
    if (inputMessage.trim() === "") return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage,
      sender: "user",
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setIsTyping(true);

    // Create initial AI message for streaming
    const streamingMessageId = (Date.now() + 1).toString();
    const initialAiMessage: Message = {
      id: streamingMessageId,
      content: "",
      sender: "ai",
      streamLogs: [],
    };

    setMessages((prev) => [...prev, initialAiMessage]);
    clearStream();
    setCurrentStreamingMessageId(streamingMessageId);

    // Start streaming logs
    startStreamingLogs(streamingMessageId);

    try {
      const sessionPayload: SessionPayload = {
        sessionId: runId || "",
        inputs: { user_prompt: inputMessage },
        stream: true,
        scope: "public",
        loggedInUser: "default",
      };

      const response = await triggerExecution(sessionPayload);

      // Update the message with final answer
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id === streamingMessageId) {
            return {
              ...msg,
              finalAnswer: response,
            };
          }
          return msg;
        }),
      );
    } catch (error) {
      console.error("Error in chat interaction:", error);

      // Update with error message
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id === streamingMessageId) {
            return {
              ...msg,
              finalAnswer:
                "I'm sorry, there was an error processing your request.",
            };
          }
          return msg;
        }),
      );
    } finally {
      setIsTyping(false);
      stopStreamingLogs(streamingMessageId);
      setCurrentStreamingMessageId(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSendMessage();
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: "cleared",
        content: "Chat cleared. How can I help you with your data pipeline?",
        sender: "ai",
      },
    ]);
    stopStreamingLogs();
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  // Clean up interval on unmount
  useEffect(() => {
    return () => {
      stopStreamingLogs();
    };
  }, []);

  // Memoized typing indicator
  const TypingIndicator = useMemo(
    () => (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex justify-start"
      >
        <div className="bg-background-dark border border-gray-800 rounded-2xl rounded-tl-none p-3 max-w-[80%]">
          <div className="flex space-x-1">
            <motion.div
              className="w-2 h-2 bg-gray-400 rounded-full"
              animate={{ y: [0, -5, 0] }}
              transition={{
                repeat: Infinity,
                duration: 0.5,
                ease: "easeInOut",
              }}
            />
            <motion.div
              className="w-2 h-2 bg-gray-400 rounded-full"
              animate={{ y: [0, -5, 0] }}
              transition={{
                repeat: Infinity,
                duration: 0.5,
                ease: "easeInOut",
                delay: 0.1,
              }}
            />
            <motion.div
              className="w-2 h-2 bg-gray-400 rounded-full"
              animate={{ y: [0, -5, 0] }}
              transition={{
                repeat: Infinity,
                duration: 0.5,
                ease: "easeInOut",
                delay: 0.2,
              }}
            />
          </div>
        </div>
      </motion.div>
    ),
    [],
  );

  // Component for rendering message content with markdown support
  const MessageContent = ({ message }: { message: Message }) => {
    if (message.sender === "user") {
      return (
        <div className="text-sm whitespace-pre-line">{message.content}</div>
      );
    }

    if (
      message.sender === "ai" &&
      (message.streamLogs || message.finalAnswer)
    ) {
      return (
        <div className="space-y-3 w-full">
          {/* Stream logs display */}
          <StreamLogDisplay
            message={message}
            onToggleExpansion={toggleNodeExpansion}
          />

          {/* Final answer with markdown rendering */}
          {message.finalAnswer && (
            <div
              className="mt-3 p-3 rounded-lg"
              style={{
                backgroundColor: `hsl(var(--primary) / 0.1)`,
                border: `1px solid hsl(var(--primary) / 0.3)`,
              }}
            >
              <div className="text-sm text-gray-100">
                <ReactMarkdown
                  components={MarkdownComponents}
                  remarkPlugins={[remarkGfm, remarkBreaks]}
                >
                  {preprocessText(message.finalAnswer)}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      );
    }

    // Default AI message without streaming
    return (
      <div className="text-sm">
        <ReactMarkdown
          components={MarkdownComponents}
          remarkPlugins={[remarkGfm, remarkBreaks]}
        >
          {preprocessText(message.content)}
        </ReactMarkdown>
      </div>
    );
  };

  return (
    <Card className="bg-background-card shadow-card border-gray-800 flex flex-col h-full max-h-[82.5vh]">
      <CardHeader className="py-4 px-6 flex flex-row justify-between items-center flex-shrink-0">
        <CardTitle className="text-lg font-heading">AI Assistant</CardTitle>
        <div className="flex space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={clearChat}
            className="text-gray-400 hover:text-gray-100"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-gray-400 hover:text-gray-100"
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-0 flex flex-col min-h-0">
        <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
          <AnimatePresence>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[90%] rounded-2xl p-3 ${
                    message.sender === "user"
                      ? "bg-primary text-white rounded-tr-none"
                      : "bg-background-dark border border-gray-800 rounded-tl-none"
                  }`}
                >
                  <MessageContent message={message} />
                </div>
              </motion.div>
            ))}
            {isTyping && TypingIndicator}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>
        <div className="p-4 border-t border-gray-800 flex-shrink-0">
          <div className="flex space-x-2 items-end">
            <Textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your data..."
              className="bg-background-dark min-h-[80px] resize-none"
              rows={3}
            />
            <Button
              onClick={handleSendMessage}
              disabled={inputMessage.trim() === "" || isTyping}
              className="bg-primary hover:bg-[#7525c9] mb-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}