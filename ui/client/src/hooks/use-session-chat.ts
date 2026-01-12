/**
 * Generic hook for chat session management
 * Used by both ExecutionTab (full functionality) and PublicChat (public links)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import axios from '@/http/axiosAgentConfig';
import { ChatSession, ChatMessage, ChatSessionData } from '@/types/session';
import { checkSessionSharingStatus } from '@/hooks/use-sharing-status';
import { transformSessionData, sortSessionsByTimestamp } from '@/utils/sessionHelpers';
import { useSessionManagement } from '@/hooks/use-session-management';
import { getBlueprintInfo, validateBlueprint } from '@/api/blueprints';
import { EnhancedStreamReader } from '@/components/shared/stream/StreamJsonParser';

// ────────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────────

export interface SessionChatConfig {
  /** Filter sessions by a specific blueprint ID (for public chat) */
  blueprintId?: string | null;
  /** Execution scope - public for shared links, private for authenticated users */
  scope: 'public' | 'private';
  /** Auto-create a session if none exist (for public chat) */
  autoCreateSession?: boolean;
  /** Source metadata for created sessions */
  sessionSource?: string;
  /** Enable sharing status checks */
  enableSharingStatusChecks?: boolean;
  /** Callback for streaming chunk processing (for execution stream visualization) */
  onStreamChunk?: (chunkData: any) => void;
}

export interface UseSessionChatReturn {
  // Session state
  sessions: ChatSession[];
  selectedSession: ChatSession | null;
  currentMessages: ChatMessage[];
  
  // Loading states
  isLoading: boolean;
  isCreatingSession: boolean;
  isDeleting: boolean;
  isExecuting: boolean;
  
  // Blueprint info (for shared link sessions)
  blueprintName: string;
  blueprintOwner: string;
  isLoadingBlueprintInfo: boolean;
  isSharingDisabled: boolean;
  isBlueprintValid: boolean;
  isValidatingBlueprint: boolean;
  
  // Delete modal state
  showDeleteModal: boolean;
  setShowDeleteModal: (open: boolean) => void;
  chatToDelete: ChatSession | null;
  
  // Actions
  handleSessionSelect: (session: ChatSession) => Promise<void>;
  handleDeleteChat: (session: ChatSession, event: React.MouseEvent) => void;
  confirmDeleteChat: () => Promise<void>;
  cancelDeleteChat: () => void;
  createSession: (blueprintId: string, metadata?: Record<string, any>) => Promise<string | null>;
  triggerExecution: (sessionPayload: ExecutionPayload) => Promise<string>;
  refreshSessions: () => Promise<void>;
  
  // Setters for external state management
  setSessions: React.Dispatch<React.SetStateAction<ChatSession[]>>;
  setSelectedSession: React.Dispatch<React.SetStateAction<ChatSession | null>>;
}

export interface ExecutionPayload {
  sessionId: string;
  inputs: { user_prompt: string };
  stream: boolean;
  streamMode?: string[];
}

// ────────────────────────────────────────────────────────────────────────────────
// Hook Implementation
// ────────────────────────────────────────────────────────────────────────────────

export const useSessionChat = (config: SessionChatConfig): UseSessionChatReturn => {
  const {
    blueprintId: filterBlueprintId,
    scope,
    autoCreateSession = false,
    sessionSource = 'chat',
    enableSharingStatusChecks = false,
    onStreamChunk,
  } = config;

  const { user, isAuthenticated } = useAuth();
  const { toast } = useToast();

  // Session state
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<ChatSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

  // Delete modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [chatToDelete, setChatToDelete] = useState<ChatSession | null>(null);

  // Blueprint info state (for shared link sessions)
  const [blueprintName, setBlueprintName] = useState<string>('');
  const [blueprintOwner, setBlueprintOwner] = useState<string>('');
  const [isLoadingBlueprintInfo, setIsLoadingBlueprintInfo] = useState(false);
  const [isSharingDisabled, setIsSharingDisabled] = useState(false);
  const [isBlueprintValid, setIsBlueprintValid] = useState(true);
  const [isValidatingBlueprint, setIsValidatingBlueprint] = useState(false);

  // Ref to track if auto-create has been attempted
  const autoCreateAttempted = useRef(false);

  const { currentMessages, loadSessionMessages, clearMessages, setCurrentMessages } =
    useSessionManagement();

  // ────────────────────────────────────────────────────────────────────────────────
  // Transform API data to ChatSession format
  // ────────────────────────────────────────────────────────────────────────────────

  const transformApiDataToSessions = useCallback(
    async (apiData: ChatSessionData[]): Promise<ChatSession[]> => {
      const transformedSessions = await Promise.all(
        apiData.map(async (sessionData, index) => {
          const baseSession = transformSessionData(sessionData, index);

          // Fetch fresh public_usage_scope status for shared link sessions
          const sessionSharingDisabled = enableSharingStatusChecks
            ? await checkSessionSharingStatus(
                baseSession.blueprintId,
                baseSession.fromSharedLink ?? false,
                baseSession.blueprintExists,
                sessionData.metadata?.public_usage_scope
              )
            : false;

          return {
            ...baseSession,
            isSharingDisabled: sessionSharingDisabled,
          };
        })
      );

      return transformedSessions;
    },
    [enableSharingStatusChecks]
  );

  // ────────────────────────────────────────────────────────────────────────────────
  // Fetch sessions
  // ────────────────────────────────────────────────────────────────────────────────

  const fetchSessions = useCallback(async () => {
    if (!isAuthenticated || !user) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.get(`/sessions/session.user.chat.get?userId=${user.username}`);
      const allSessions: ChatSessionData[] = response.data;

      // Filter by blueprint ID if specified
      let filteredSessions = allSessions;
      if (filterBlueprintId) {
        filteredSessions = allSessions.filter(
          (session) => session.blueprint_id === filterBlueprintId && session.blueprint_exists
        );
      }

      const transformedSessions = await transformApiDataToSessions(filteredSessions);
      const sortedSessions = sortSessionsByTimestamp(transformedSessions);

      setSessions(sortedSessions);

      return sortedSessions;
    } catch (error: any) {
      console.error('Error fetching chat sessions:', error);
      toast({
        title: 'Error',
        description: 'Failed to load chat sessions',
        variant: 'destructive',
      });
      return [];
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, user, filterBlueprintId, transformApiDataToSessions, toast]);

  // ────────────────────────────────────────────────────────────────────────────────
  // Create session
  // ────────────────────────────────────────────────────────────────────────────────

  const createSession = useCallback(
    async (blueprintId: string, metadata?: Record<string, any>): Promise<string | null> => {
      if (!user) return null;

      setIsCreatingSession(true);
      try {
        const response = await axios.post('/sessions/user.session.create', {
          blueprintId,
          userId: user.username,
          metadata: { source: sessionSource, ...metadata },
        });

        const newSessionId = response.data;

        if (!newSessionId || typeof newSessionId !== 'string') {
          throw new Error('Invalid session ID received from server');
        }

        // Create a temporary session object
        const tempSession: ChatSession = {
          id: newSessionId,
          blueprintId,
          title: 'New Chat',
          lastActive: 'Just now',
          timestamp: new Date(),
          preview: 'New conversation',
          messages: [],
          blueprintExists: true,
          fromSharedLink: sessionSource === 'public_link',
        };

        // Add to sessions list
        setSessions((prev) => [tempSession, ...prev]);
        setSelectedSession(tempSession);
        setCurrentMessages([]);

        // Refresh sessions in background to get proper data
        fetchSessions();

        return newSessionId;
      } catch (error: any) {
        console.error('Error creating session:', error);
        toast({
          title: 'Error',
          description: error.response?.data?.error || 'Failed to create new chat',
          variant: 'destructive',
        });
        return null;
      } finally {
        setIsCreatingSession(false);
      }
    },
    [user, sessionSource, fetchSessions, toast, setCurrentMessages]
  );

  // ────────────────────────────────────────────────────────────────────────────────
  // Session selection
  // ────────────────────────────────────────────────────────────────────────────────

  const handleSessionSelect = useCallback(
    async (session: ChatSession) => {
      setSelectedSession(session);

      // Reset blueprint info when switching sessions
      setBlueprintName('');
      setBlueprintOwner('');
      setIsLoadingBlueprintInfo(false);

      // Fetch blueprint info if needed
      if (session.blueprintId && session.blueprintExists) {
        setIsLoadingBlueprintInfo(true);
        try {
          const blueprintInfo = await getBlueprintInfo(session.blueprintId);

          // Extract blueprint name
          if (blueprintInfo.spec_dict?.name) {
            setBlueprintName(blueprintInfo.spec_dict.name);
          }
          setBlueprintOwner(blueprintInfo.user_id || '');

          // Check sharing status for shared link sessions
          if (session.fromSharedLink && enableSharingStatusChecks) {
            const isPublic = blueprintInfo.metadata?.usageScope === 'public';
            const disabled = !isPublic;
            setIsSharingDisabled(disabled);

            // Update the session in the list
            setSessions((prev) =>
              prev.map((s) => (s.id === session.id ? { ...s, isSharingDisabled: disabled } : s))
            );
          } else {
            setIsSharingDisabled(false);
          }
        } catch (error: any) {
          console.error('Error fetching blueprint info:', error);
          if (session.fromSharedLink) {
            setIsSharingDisabled(true);
            setBlueprintName('Unknown');
          }
        } finally {
          setIsLoadingBlueprintInfo(false);
        }
      } else if (!session.blueprintExists) {
        setIsSharingDisabled(false);
      }

      // Load session messages
      const updatedSession = await loadSessionMessages(session);
      if (updatedSession) {
        setSelectedSession(updatedSession);
        setSessions((prev) => prev.map((s) => (s.id === session.id ? updatedSession : s)));
      }
    },
    [loadSessionMessages, enableSharingStatusChecks]
  );

  // ────────────────────────────────────────────────────────────────────────────────
  // Delete session
  // ────────────────────────────────────────────────────────────────────────────────

  const handleDeleteChat = useCallback((session: ChatSession, event: React.MouseEvent) => {
    event.stopPropagation();
    setChatToDelete(session);
    setShowDeleteModal(true);
  }, []);

  const confirmDeleteChat = useCallback(async () => {
    if (!chatToDelete) return;

    setIsDeleting(true);
    try {
      await axios.delete(`/sessions/session.delete?sessionId=${chatToDelete.id}`);

      setSessions((prev) => prev.filter((s) => s.id !== chatToDelete.id));

      if (selectedSession?.id === chatToDelete.id) {
        setSelectedSession(null);
        clearMessages();
      }

      setShowDeleteModal(false);
      setChatToDelete(null);

      toast({
        title: 'Success',
        description: 'Chat session deleted successfully',
      });
    } catch (error: any) {
      console.error('Error deleting chat session:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.error || 'Failed to delete chat session',
        variant: 'destructive',
      });
    } finally {
      setIsDeleting(false);
    }
  }, [chatToDelete, selectedSession, clearMessages, toast]);

  const cancelDeleteChat = useCallback(() => {
    setShowDeleteModal(false);
    setChatToDelete(null);
  }, []);

  // ────────────────────────────────────────────────────────────────────────────────
  // Blueprint validation
  // ────────────────────────────────────────────────────────────────────────────────

  const checkBlueprintValidity = useCallback(async (blueprintId: string, showLoading = true) => {
    if (showLoading) {
      setIsValidatingBlueprint(true);
    }
    try {
      const result = await validateBlueprint({ blueprintId });
      setIsBlueprintValid(result.is_valid);
    } catch (error: any) {
      console.error('Error validating blueprint:', error);
      setIsBlueprintValid(true); // Don't block on validation errors
    } finally {
      if (showLoading) {
        setIsValidatingBlueprint(false);
      }
    }
  }, []);

  // ────────────────────────────────────────────────────────────────────────────────
  // Execution
  // ────────────────────────────────────────────────────────────────────────────────

  const triggerExecution = useCallback(
    async (sessionPayload: ExecutionPayload): Promise<string> => {
      const sessionId = sessionPayload.sessionId;

      if (!sessionId) {
        throw new Error('No session available');
      }

      // Check sharing status before execution (for public scope)
      if (scope === 'public' && selectedSession?.blueprintId) {
        try {
          const blueprintInfo = await getBlueprintInfo(selectedSession.blueprintId);
          const isPublic = blueprintInfo.metadata?.usageScope === 'public';
          if (!isPublic) {
            throw new Error(
              "This workflow's chat sharing has been disabled and can no longer be continued."
            );
          }
        } catch (error: any) {
          if (error.message?.includes('disabled')) {
            throw error;
          }
          throw new Error(
            "This workflow's chat sharing has been disabled and can no longer be continued."
          );
        }
      }

      setIsExecuting(true);

      try {
        const response = await fetch(`/api2/sessions/user.session.execute`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            sessionId,
            inputs: sessionPayload.inputs || {},
            stream: true,
            streamMode: sessionPayload.streamMode || ['custom'],
            scope,
            loggedInUser: user?.username || '',
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Process stream if callback provided
        if (response.body && onStreamChunk) {
          const streamReader = new EnhancedStreamReader((chunkData: any) => {
            onStreamChunk(chunkData);
          });
          await streamReader.readStream(response);
        } else if (response.body) {
          // Read stream to completion without processing
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

        // Fetch final output from session state
        const sessionResponse = await axios.get(`/sessions/session.state.get?sessionId=${sessionId}`);
        const output = sessionResponse.data.output;

        return output && output.trim() !== '' ? output : 'Execution completed, but no output was generated.';
      } catch (error: any) {
        console.error('Error in triggerExecution:', error);
        throw new Error(error.response?.data?.error || error.message || 'Failed to execute session');
      } finally {
        setIsExecuting(false);
      }
    },
    [scope, selectedSession?.blueprintId, user, onStreamChunk]
  );

  // ────────────────────────────────────────────────────────────────────────────────
  // Refresh sessions
  // ────────────────────────────────────────────────────────────────────────────────

  const refreshSessions = useCallback(async () => {
    const sortedSessions = await fetchSessions();
    if (sortedSessions && sortedSessions.length > 0 && selectedSession) {
      const updatedSelected = sortedSessions.find((s) => s.id === selectedSession.id);
      if (updatedSelected) {
        setSelectedSession(updatedSelected);
      }
    }
  }, [fetchSessions, selectedSession]);

  // ────────────────────────────────────────────────────────────────────────────────
  // Effects
  // ────────────────────────────────────────────────────────────────────────────────

  // Fetch sessions on mount
  useEffect(() => {
    const initializeSessions = async () => {
      if (!isAuthenticated || !user) return;

      const sortedSessions = await fetchSessions();

      // Auto-create session if enabled and no sessions exist
      if (
        autoCreateSession &&
        filterBlueprintId &&
        sortedSessions &&
        sortedSessions.length === 0 &&
        !autoCreateAttempted.current
      ) {
        autoCreateAttempted.current = true;
        await createSession(filterBlueprintId);
      } else if (sortedSessions && sortedSessions.length > 0 && !selectedSession) {
        // Auto-select first session
        await handleSessionSelect(sortedSessions[0]);
      }
    };

    initializeSessions();
  }, [isAuthenticated, user, filterBlueprintId]);

  // Periodic sharing status and validity checks for public scope
  useEffect(() => {
    if (scope !== 'public' || !isAuthenticated || !user || !filterBlueprintId) return;

    // Initial check
    checkBlueprintValidity(filterBlueprintId, false);

    // Polling every 30 seconds
    const interval = setInterval(() => {
      if (selectedSession?.blueprintId) {
        getBlueprintInfo(selectedSession.blueprintId)
          .then((info) => {
            const isPublic = info.metadata?.usageScope === 'public';
            setIsSharingDisabled(!isPublic);
          })
          .catch(() => {
            setIsSharingDisabled(true);
          });
      }
      checkBlueprintValidity(filterBlueprintId, false);
    }, 30000);

    return () => clearInterval(interval);
  }, [scope, isAuthenticated, user, filterBlueprintId, selectedSession?.blueprintId, checkBlueprintValidity]);

  return {
    sessions,
    selectedSession,
    currentMessages,
    isLoading,
    isCreatingSession,
    isDeleting,
    isExecuting,
    blueprintName,
    blueprintOwner,
    isLoadingBlueprintInfo,
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
    refreshSessions,
    setSessions,
    setSelectedSession,
  };
};

