import React, { useState, useEffect } from "react";
import { useRoute } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import axios from "../http/axiosAgentConfig";
import ChatInterface from "@/components/agentic-ai/chat/ChatInterface";
import { SessionPayload } from "@/components/agentic-ai/ExecutionTab";
import { StreamingDataProvider } from "@/components/agentic-ai/StreamingDataContext";
import { Loader2 } from "lucide-react";

export default function ChatOnlyPage() {
  const [, params] = useRoute("/chat/:token");
  const token = params?.token;
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const { toast } = useToast();
  
  const [blueprintId, setBlueprintId] = useState<string | null>(null);
  const [blueprintName, setBlueprintName] = useState<string>("");
  const [runId, setRunId] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(true);
  const [isCreatingSession, setIsCreatingSession] = useState(false);

  // Validate token and get blueprint info
  useEffect(() => {
    if (!token) {
      setIsValidating(false);
      return;
    }

    const validateToken = async () => {
      try {
        const response = await axios.get(
          `/shares/public-chat.validate?blueprintId=${token}`
        );
        
        if (response.data.valid) {
          setBlueprintId(token);
          setBlueprintName(response.data.blueprint_name || "Unnamed Workflow");
        } else {
          toast({
            title: "Invalid Link",
            description: "This chat link is no longer valid or has been disabled",
            variant: "destructive",
          });
        }
      } catch (error: any) {
        toast({
          title: "Error",
          description: error.response?.data?.error || "Failed to validate chat link",
          variant: "destructive",
        });
      } finally {
        setIsValidating(false);
      }
    };

    validateToken();
  }, [token, toast]);

  // Create or get session when authenticated and blueprint is valid
  useEffect(() => {
    if (!isAuthenticated || !user || !blueprintId || runId || isCreatingSession) {
      return;
    }

    const createSession = async () => {
      setIsCreatingSession(true);
      try {
        const response = await axios.post("/sessions/user.session.create", {
          blueprintId: blueprintId,
          userId: user.username,
          metadata: {},
          fromSharedLink: true, // Mark as shared link session
        });
        setRunId(response.data);
      } catch (error: any) {
        toast({
          title: "Error",
          description: error.response?.data?.error || "Failed to create chat session",
          variant: "destructive",
        });
      } finally {
        setIsCreatingSession(false);
      }
    };

    createSession();
  }, [isAuthenticated, user, blueprintId, runId, isCreatingSession, toast]);

  const triggerExecution = async (sessionPayload: SessionPayload): Promise<string> => {
    if (!runId) {
      throw new Error("No session available");
    }

    try {
      const response = await axios.post("/sessions/user.session.execute", {
        sessionId: runId,
        inputs: sessionPayload.inputs || {},
        stream: true,
        streamMode: ["custom"],
        scope: "public",
        loggedInUser: user?.username || "",
      });

      // Return a placeholder - actual streaming is handled by ChatInterface
      return runId;
    } catch (error: any) {
      throw new Error(error.response?.data?.error || "Failed to execute session");
    }
  };

  // Show loading state
  if (authLoading || isValidating) {
    return (
      <div className="flex items-center justify-center h-screen bg-background-dark">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Show authentication required
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-screen bg-background-dark">
        <div className="text-center">
          <p className="text-white mb-4">Authentication required to access this chat</p>
          <p className="text-gray-400 text-sm">Please log in to continue</p>
        </div>
      </div>
    );
  }

  // Show invalid link
  if (!blueprintId) {
    return (
      <div className="flex items-center justify-center h-screen bg-background-dark">
        <div className="text-center">
          <p className="text-white mb-2">Invalid Chat Link</p>
          <p className="text-gray-400 text-sm">
            This chat link is no longer valid or has been disabled
          </p>
        </div>
      </div>
    );
  }

  // Show session creation loading
  if (isCreatingSession || !runId) {
    return (
      <div className="flex items-center justify-center h-screen bg-background-dark">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-gray-400">Setting up chat session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background-dark">
      {/* Header with Unifai branding and user info */}
      <div className="bg-background-card border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-bold text-white">UnifAI</h1>
          <div className="h-6 w-px bg-gray-700" />
          <p className="text-sm text-gray-400">{blueprintName}</p>
        </div>
        <div className="flex items-center space-x-3">
          <span className="text-sm text-gray-400">
            {user?.name || user?.username || "User"}
          </span>
        </div>
      </div>

      {/* Chat Interface */}
      <div className="flex-1 overflow-hidden">
        <StreamingDataProvider>
          <ChatInterface
            runId={runId}
            triggerExecution={triggerExecution}
            initialMessages={[]}
            blueprintExists={true}
            isBlueprintGraphHidden={true}
            isChatOnlyMode={true}
          />
        </StreamingDataProvider>
      </div>
    </div>
  );
}

