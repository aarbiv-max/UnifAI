/**
 * Public Chat Component
 * Provides a standalone chat interface for shared workflow links
 */

import React, { useState, useEffect, useCallback } from "react";
import { useRoute } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import ChatInterface from "@/components/agentic-ai/chat/ChatInterface";
import { StreamingDataProvider } from "@/components/agentic-ai/StreamingDataContext";
import { Loader2, MessageSquare, LogOut } from "lucide-react";
import WorkflowStatusBanner, { WorkflowBannerMessages } from "@/components/shared/WorkflowStatusBanner";
import { motion } from "framer-motion";
import SimpleTooltip from "@/components/shared/SimpleTooltip";
import { useTheme } from "@/contexts/ThemeContext";
import { ChatHistorySidebar } from "@/components/shared/ChatHistorySidebar";
import { DeleteChatModal } from "@/components/shared/DeleteChatModal";
import { useSessionChat } from "@/hooks/use-session-chat";
import { getBlueprintInfo } from "@/api/blueprints";
import { UmamiEvents } from "@/config/umamiEvents";

// ────────────────────────────────────────────────────────────────────────────────
// Component
// ────────────────────────────────────────────────────────────────────────────────

export default function PublicChat() {
  const [, params] = useRoute("/chat/:token");
  const token = params?.token;
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth();
  const { toast } = useToast();
  const { primaryHex } = useTheme();

  const [blueprintId, setBlueprintId] = useState<string | null>(null);
  const [blueprintName, setBlueprintName] = useState<string>("");
  const [blueprintOwner, setBlueprintOwner] = useState<string>("");
  const [isValidating, setIsValidating] = useState(true);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Use the generic session chat hook with public scope
  const {
    sessions: chatSessions,
    selectedSession,
    currentMessages: chatHistory,
    isLoading: isLoadingSessions,
    isCreatingSession,
    isDeleting,
    isSharingDisabled,
    isBlueprintValid,
    isValidatingBlueprint,
    showDeleteModal,
    setShowDeleteModal,
    chatToDelete,
    handleSessionSelect,
    handleDeleteChat,
    confirmDeleteChat,
    cancelDeleteChat,
    createSession,
    triggerExecution,
  } = useSessionChat({
    blueprintId,
    scope: 'public',
    autoCreateSession: true,
    sessionSource: 'public_link',
    enableSharingStatusChecks: true,
  });

  // Validate token and get blueprint info
  useEffect(() => {
    if (!token) {
      setIsValidating(false);
      return;
    }

    const validateToken = async () => {
      try {
        // Get blueprint info (includes usageScope in metadata)
        const blueprintInfo = await getBlueprintInfo(token);
        setBlueprintId(token);
        setBlueprintName(blueprintInfo.spec_dict?.name || "Unnamed Workflow");
        setBlueprintOwner(blueprintInfo.user_id || "");

        // Check sharing status from the same blueprintInfo response
        const isPublic = blueprintInfo.metadata?.usageScope === "public";
        if (!isPublic) {
          setValidationError("Sorry, this workflow is not available for chats");
        }
      } catch (error: any) {
        if (error.response?.status === 404) {
          const errorMsg = error.response?.data?.error || "This workflow doesn't exist";
          setValidationError(errorMsg);
        } else {
          setValidationError("Failed to validate chat link");
        }
      } finally {
        setIsValidating(false);
      }
    };

    validateToken();
  }, [token]);

  // Handle new chat creation
  const handleNewChat = useCallback(async () => {
    if (!blueprintId) return;
    await createSession(blueprintId);
  }, [blueprintId, createSession]);

  // Get current run ID (selected session ID)
  const runId = selectedSession?.id || null;

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

  // Show invalid link
  if (!blueprintId || validationError) {
    return (
      <div className="flex items-center justify-center h-screen bg-background-dark">
        <div className="text-center">
          <p className="text-white mb-2">Invalid Chat Link</p>
          <p className="text-gray-400 text-sm">
            {validationError || "This chat link is no longer valid or has been disabled"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background-dark">
      {/* Header with Unifai branding and user info */}
      <div className="bg-background-card border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-md bg-gradient-to-r from-primary to-gray-500 flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 12H7M17 12H21M12 3V7M12 17V21M5 19L8 16M16 8L19 5M19 19L16 16M5 5L8 8" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h1 className="text-xl font-bold text-white">UnifAI</h1>
          </div>
          <div className="h-6 w-px bg-gray-700" />
          <div className="flex items-center">
            <p className="text-sm text-gray-400">{blueprintName}</p>
            {blueprintOwner && (
              <span className="text-xs text-gray-500 ml-2">(workflow shared by {blueprintOwner})</span>
            )}
          </div>
        </div>

        {/* User Profile with Logout */}
        <div className="px-4 py-3 border-l border-gray-800">
          <div className="flex items-center space-x-3">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
              style={{ background: `linear-gradient(90deg, #6B7280, ${primaryHex || '#8A2BE2'})` }}
            >
              <span className="text-sm font-medium text-white">
                {user?.name
                  ?.split(' ')
                  .filter(Boolean)
                  .map(part => part[0].toUpperCase())
                  .join('') || user?.username?.[0].toUpperCase() || 'U'}
              </span>
            </div>

            <motion.div
              initial={false}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2 }}
              className="flex-grow"
            >
              <h4 className="text-sm font-medium text-white">{user?.name || user?.username || "User"}</h4>
            </motion.div>

            <motion.div
              initial={false}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2 }}
            >
              <SimpleTooltip content={<p>Sign out</p>}>
                <button
                  onClick={logout}
                  className="mt-2 text-gray-400 hover:text-white transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </SimpleTooltip>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Main Content Area with Sidebar */}
      <div className="flex-1 overflow-hidden flex">
        {/* Chat History Sidebar */}
        <ChatHistorySidebar
          sessions={chatSessions}
          selectedSession={selectedSession}
          isLoading={isLoadingSessions}
          isCreatingSession={isCreatingSession}
          onSessionSelect={handleSessionSelect}
          onDeleteChat={handleDeleteChat}
          onNewChat={handleNewChat}
          title="Chat History"
          newChatUmamiEvent={UmamiEvents.PUBLIC_CHAT_NEW_SESSION}
          emptyMessage="No chat sessions yet. Click + to start a new chat."
          className="w-80 border-r border-gray-800 flex-shrink-0"
        />

        {/* Chat Interface */}
        <div className="flex-1 overflow-hidden">
          {!runId ? (
            isLoadingSessions ? (
              <div className="flex items-center justify-center h-full bg-background-dark">
                <div className="text-center">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                  <p className="text-gray-400">Loading chat sessions...</p>
                </div>
              </div>
            ) : !isBlueprintValid ? (
              <div className="flex items-center justify-center h-full bg-background-dark">
                <div className="max-w-md">
                  <WorkflowStatusBanner
                    variant={WorkflowBannerMessages.validationFailed.variant}
                    title={WorkflowBannerMessages.validationFailed.title}
                    message={WorkflowBannerMessages.validationFailed.message}
                  />
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full bg-background-dark">
                <div className="text-center">
                  <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-gray-400">Select a chat session or start a new one</p>
                </div>
              </div>
            )
          ) : (
            <StreamingDataProvider>
              <ChatInterface
                runId={runId}
                triggerExecution={triggerExecution}
                initialMessages={chatHistory}
                blueprintExists={true}
                isSharingDisabled={isSharingDisabled}
                blueprintValid={isBlueprintValid}
                isValidatingBlueprint={isValidatingBlueprint}
                isBlueprintGraphHidden={true}
                isChatOnlyMode={true}
              />
            </StreamingDataProvider>
          )}
        </div>
      </div>

      {/* Delete Chat Confirmation Modal */}
      <DeleteChatModal
        open={showDeleteModal}
        onOpenChange={setShowDeleteModal}
        chatToDelete={chatToDelete}
        isDeleting={isDeleting}
        onConfirm={confirmDeleteChat}
        onCancel={cancelDeleteChat}
      />
    </div>
  );
}
