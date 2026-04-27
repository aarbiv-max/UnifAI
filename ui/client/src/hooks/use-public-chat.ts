import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import axios from "@/http/axiosAgentConfig";
import { ChatSession, ChatMessage, ChatSessionData } from "@/types/session";
import { checkSessionSharingStatus } from "@/hooks/use-sharing-status";
import { transformSessionData, sortSessionsByTimestamp } from "@/utils/sessionHelpers";
import { useSessionManagement } from "@/hooks/use-session-management";
import { getBlueprintInfo } from "@/api/blueprints";
import {
  useChatSessionsPagination,
  CHAT_SESSIONS_PAGE_SIZE,
} from "@/hooks/use-chat-sessions-pagination";

interface UsePublicChatReturn {
  sessions: ChatSession[];
  sessionsTotal: number;
  sessionsPage: number;
  sessionsMaxPage: number;
  goSessionsPrevPage: () => void;
  goSessionsNextPage: () => void;
  selectedSession: ChatSession | null;
  isLoading: boolean;
  isCreatingSession: boolean;
  isDeleting: boolean;
  chatHistory: ChatMessage[];
  runId: string | null;
  handleNewChat: () => Promise<void>;
  handleSessionSelect: (session: ChatSession) => Promise<void>;
  handleDeleteChat: (session: ChatSession, event: React.MouseEvent) => void;
  confirmDeleteChat: () => Promise<void>;
  cancelDeleteChat: () => void;
  triggerExecution: (sessionPayload: any) => Promise<string>;
  showDeleteModal: boolean;
  setShowDeleteModal: (open: boolean) => void;
  chatToDelete: ChatSession | null;
}

export const usePublicChat = (blueprintId: string | null): UsePublicChatReturn => {
  const { user, isAuthenticated } = useAuth();
  const { toast } = useToast();

  const [selectedSession, setSelectedSession] = useState<ChatSession | null>(null);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [chatToDelete, setChatToDelete] = useState<ChatSession | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [runId, setRunId] = useState<string | null>(null);

  const didInitialSessionPick = useRef(false);
  const didTryAutoCreate = useRef(false);

  const { loadSessionMessages } = useSessionManagement();

  const transformPage = useCallback(
    async (items: ChatSessionData[], pageIndex: number): Promise<ChatSession[]> => {
      const baseOffset = pageIndex * CHAT_SESSIONS_PAGE_SIZE;
      const transformedSessions = await Promise.all(
        items.map(async (sessionData, i) => {
          const baseSession = transformSessionData(sessionData, baseOffset + i);
          const isSharingDisabled = await checkSessionSharingStatus(
            baseSession.blueprintId,
            baseSession.fromSharedLink ?? false,
            baseSession.blueprintExists,
            sessionData.metadata?.public_usage_scope,
          );
          return {
            ...baseSession,
            isSharingDisabled,
          };
        }),
      );
      return transformedSessions;
    },
    [],
  );

  const listEnabled = Boolean(isAuthenticated && user && blueprintId);
  const {
    mergeSessionInCache,
    removeSessionFromCache,
    peekPage,
    refresh: refreshSessionPages,
    ...chatPagination
  } = useChatSessionsPagination({
    userId: user?.username,
    blueprintId: blueprintId ?? undefined,
    enabled: listEnabled,
    transformPage,
  });

  useEffect(() => {
    if (!chatPagination.listLoadError) return;
    toast({
      title: "Error",
      description: chatPagination.listLoadError,
      variant: "destructive",
    });
  }, [chatPagination.listLoadError, toast]);

  useEffect(() => {
    didInitialSessionPick.current = false;
    didTryAutoCreate.current = false;
  }, [blueprintId, user?.username]);

  const handleSessionSelect = useCallback(
    async (session: ChatSession) => {
      setSelectedSession(session);

      const updatedSession = await loadSessionMessages(session);
      if (updatedSession) {
        setSelectedSession(updatedSession);
        setChatHistory(updatedSession.messages);
        setRunId(session.id);
        mergeSessionInCache(updatedSession);
      } else {
        setChatHistory([]);
        setRunId(session.id);
      }
    },
    [loadSessionMessages, mergeSessionInCache],
  );

  useEffect(() => {
    if (!listEnabled) return;
    if (chatPagination.isLoading) return;
    if (didTryAutoCreate.current) return;
    if (chatPagination.total > 0) return;
    if (selectedSession || runId) return;
    if (!blueprintId || !user) return;

    didTryAutoCreate.current = true;
    void (async () => {
      try {
        const createResponse = await axios.post("/sessions/user.session.create", {
          blueprintId: blueprintId,
          userId: user.username,
          metadata: { source: "public_link" },
        });

        const newSessionId = createResponse.data;
        if (!newSessionId || typeof newSessionId !== "string") {
          throw new Error("Invalid session ID received from server");
        }

        setRunId(newSessionId);
        setChatHistory([]);

        const tempSession: ChatSession = {
          id: newSessionId,
          blueprintId: blueprintId,
          title: "New Chat",
          lastActive: "Just now",
          timestamp: new Date(),
          preview: "New conversation",
          messages: [],
          blueprintExists: true,
          fromSharedLink: true,
        };
        setSelectedSession(tempSession);

        await refreshSessionPages();
        const sortedPage0 = sortSessionsByTimestamp([...peekPage(0)]);
        const newSession = sortedPage0.find((s) => s.id === newSessionId);
        if (newSession) {
          setSelectedSession(newSession);
        }
      } catch (createError: unknown) {
        console.error("Error auto-creating new chat:", createError);
      }
    })();
  }, [
    listEnabled,
    chatPagination.isLoading,
    chatPagination.total,
    selectedSession,
    runId,
    blueprintId,
    user,
    refreshSessionPages,
    peekPage,
  ]);

  const firstSidebarSessionId = chatPagination.displayedSessions[0]?.id;

  useEffect(() => {
    if (!listEnabled) return;
    if (chatPagination.isLoading || didInitialSessionPick.current) return;
    if (chatPagination.total === 0) return;
    if (selectedSession || runId) return;
    if (!firstSidebarSessionId) return;
    const first =
      chatPagination.displayedSessions.find((s) => s.id === firstSidebarSessionId) ??
      peekPage(0)[0];
    if (!first) return;
    didInitialSessionPick.current = true;
    void handleSessionSelect(first);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listEnabled, chatPagination.isLoading, chatPagination.total, firstSidebarSessionId, selectedSession, runId]);

  const handleDeleteChat = useCallback((session: ChatSession, event: React.MouseEvent) => {
    event.stopPropagation();
    setChatToDelete(session);
    setShowDeleteModal(true);
  }, []);

  const confirmDeleteChat = useCallback(async () => {
    if (!chatToDelete) return;

    const onlyRowOnPage =
      chatPagination.displayedSessions.length === 1 &&
      chatPagination.displayedSessions[0]?.id === chatToDelete.id;
    const pageBefore = chatPagination.currentPage;

    setIsDeleting(true);
    try {
      await axios.delete(`/sessions/session.delete?sessionId=${chatToDelete.id}`);

      removeSessionFromCache(chatToDelete.id);
      if (onlyRowOnPage && pageBefore > 0) {
        chatPagination.setCurrentPage(pageBefore - 1);
      }

      if (selectedSession?.id === chatToDelete.id) {
        setSelectedSession(null);
        setChatHistory([]);
        setRunId(null);
      }

      setShowDeleteModal(false);
      setChatToDelete(null);

      toast({
        title: "Success",
        description: "Chat session deleted successfully",
      });
    } catch (error: unknown) {
      console.error("Error deleting chat session:", error);
      toast({
        title: "Error",
        description:
          (error as { response?: { data?: { error?: string } } })?.response?.data?.error ||
          "Failed to delete chat session",
        variant: "destructive",
      });
    } finally {
      setIsDeleting(false);
    }
  }, [chatToDelete, selectedSession, toast, chatPagination, removeSessionFromCache]);

  const cancelDeleteChat = useCallback(() => {
    setShowDeleteModal(false);
    setChatToDelete(null);
  }, []);

  const handleNewChat = useCallback(async () => {
    if (!blueprintId || !user) return;

    setIsCreatingSession(true);
    try {
      const response = await axios.post("/sessions/user.session.create", {
        blueprintId: blueprintId,
        userId: user.username,
        metadata: { source: "public_link" },
      });

      const newSessionId = response.data;

      const tempSession: ChatSession = {
        id: newSessionId,
        blueprintId: blueprintId,
        title: "New Chat",
        lastActive: "Just now",
        timestamp: new Date(),
        preview: "New conversation",
        messages: [],
        blueprintExists: true,
        fromSharedLink: true,
      };

      setSelectedSession(tempSession);
      setChatHistory([]);
      setRunId(newSessionId);

      await refreshSessionPages();
      const sortedPage0 = sortSessionsByTimestamp([...peekPage(0)]);
      const newSession = sortedPage0.find((s) => s.id === newSessionId);
      if (newSession) {
        setSelectedSession(newSession);
      }
    } catch (error: unknown) {
      toast({
        title: "Error",
        description:
          (error as { response?: { data?: { error?: string } } })?.response?.data?.error ||
          "Failed to create new chat",
        variant: "destructive",
      });
    } finally {
      setIsCreatingSession(false);
    }
  }, [blueprintId, user, toast, refreshSessionPages, peekPage]);

  const triggerExecution = useCallback(
    async (sessionPayload: any): Promise<string> => {
      if (!runId) {
        throw new Error("No session available");
      }

      if (blueprintId) {
        try {
          const blueprintInfo = await getBlueprintInfo(blueprintId);
          const isPublic = blueprintInfo.metadata?.usageScope === "public";
          if (!isPublic) {
            throw new Error(
              "This workflow's chat sharing has been disabled and can no longer be continued.",
            );
          }
        } catch (error: unknown) {
          const err = error as Error;
          if (err.message && err.message.includes("disabled")) {
            throw err;
          }
          throw new Error(
            "This workflow's chat sharing has been disabled and can no longer be continued.",
          );
        }
      }

      try {
        const response = await fetch(`/api2/sessions/user.session.execute`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            sessionId: runId,
            inputs: sessionPayload.inputs || {},
            stream: true,
            streamMode: ["custom"],
            scope: "public",
            loggedInUser: user?.username || "",
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        if (response.body) {
          const reader = response.body.getReader();
          const decoder = new TextDecoder();

          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              decoder.decode(value, { stream: true });
            }
          } finally {
            reader.releaseLock();
          }
        }

        const sessionResponse = await axios.get(`/sessions/session.chat.get?sessionId=${runId}`);
        const output = sessionResponse.data.output;
        return output && output.trim() !== ""
          ? output
          : "Execution completed, but no output was generated.";
      } catch (error: unknown) {
        console.error("Error in triggerExecution:", error);
        const err = error as { response?: { data?: { error?: string } }; message?: string };
        throw new Error(err.response?.data?.error || err.message || "Failed to execute session");
      }
    },
    [runId, blueprintId, user],
  );

  return {
    sessions: chatPagination.displayedSessions,
    sessionsTotal: chatPagination.total,
    sessionsPage: chatPagination.currentPage,
    sessionsMaxPage: chatPagination.maxPageIndex,
    goSessionsPrevPage: chatPagination.goToPrevPage,
    goSessionsNextPage: chatPagination.goToNextPage,
    selectedSession,
    isLoading: chatPagination.isLoading,
    isCreatingSession,
    isDeleting,
    chatHistory,
    runId,
    handleNewChat,
    handleSessionSelect,
    handleDeleteChat,
    confirmDeleteChat,
    cancelDeleteChat,
    triggerExecution,
    showDeleteModal,
    setShowDeleteModal,
    chatToDelete,
  };
};
