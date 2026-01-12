import React, { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import ChatInterface from "./chat/ChatInterface";
import ExecutionStream from "./ExecutionStream";
import ReactFlowGraph from "./graphs/ReactFlowGraph";
import { useStreamingData } from './StreamingDataContext';
import { useAuth } from "@/contexts/AuthContext";
import { useAgenticAI } from "@/contexts/AgenticAIContext";
import WorkflowsPanel from "./WorkflowsPanel";
import { ReactFlowProvider } from "reactflow";
import {
  Dialog,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  CustomDialogContent,
} from "@/components/ui/dialog";
import { FlowObject } from "./graphs/interfaces";
import { UmamiTrack } from '@/components/ui/umamitrack';
import { UmamiEvents } from '@/config/umamiEvents';
import { useBlueprintValidation } from "@/hooks/use-blueprint-validation";
import { useSessionChat, ExecutionPayload } from "@/hooks/use-session-chat";
import { ChatHistorySidebar } from "@/components/shared/ChatHistorySidebar";
import { DeleteChatModal } from "@/components/shared/DeleteChatModal";
import axios from '@/http/axiosAgentConfig';

// ────────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────────

export type SessionPayload = {
  sessionId: string;
  inputs: { user_prompt: string };
  stream: boolean;
  scope: 'public' | 'private';
  loggedInUser: string;
};

type ExecutionTabProps = {
  runId: string | null;
};

type ChunkData = {
  node: string;
  display_name: string;
  type: 'llm_token' | 'complete' | 'tool_calling' | 'tool_result' | 'workplan_snapshot';
  chunk?: string;
  tool?: string;
  output?: string;
  call_id?: string;
  args?: Record<string, any>;
  state?: {
    user_prompt?: string;
  };
  action?: 'loaded' | 'saved' | 'deleted';
  plan_id?: string;
  thread_id?: string;
  owner_uid?: string;
  workplan?: any;
};

// ────────────────────────────────────────────────────────────────────────────────
// Component
// ────────────────────────────────────────────────────────────────────────────────

export default function ExecutionTab({
  runId
}: ExecutionTabProps): React.ReactElement {
  const [showExecutionStream, setShowExecutionStream] = useState(false);
  const [isLiveRequest, setIsLiveRequest] = useState(false);
  const [showAddFlowModal, setShowAddFlowModal] = useState(false);
  const [selectedFlowForModal, setSelectedFlowForModal] = useState<FlowObject | null>(null);

  // Three panel widths: Available Chats, ChatInterface, Blueprint Graph
  const [chatSidebarWidth, setChatSidebarWidth] = useState(20);
  const [chatInterfaceWidth, setChatInterfaceWidth] = useState(50);
  const [blueprintGraphWidth, setBlueprintGraphWidth] = useState(30);
  const [isResizing, setIsResizing] = useState(false);
  const [activeResizer, setActiveResizer] = useState<'left' | 'right' | null>(null);
  const [isBlueprintGraphHidden, setIsBlueprintGraphHidden] = useState(false);
  const [savedBlueprintGraphWidth, setSavedBlueprintGraphWidth] = useState(30);

  const { nodeListRef, forceUpdate } = useStreamingData();
  const { user } = useAuth();
  const { cacheBlueprintValidationResults } = useAgenticAI();

  // Stream chunk processing callback for execution visualization
  const handleStreamChunk = useCallback((chunkData: ChunkData) => {
    updateNodeList(chunkData);
  }, []);

  // Use the generic session chat hook
  const {
    sessions: chatSessions,
    selectedSession,
    currentMessages: currentSessionMessages,
    isLoading,
    isCreatingSession,
    isDeleting,
    isExecuting,
    blueprintName: sharedLinkBlueprintName,
    isLoadingBlueprintInfo: isLoadingBlueprintName,
    isSharingDisabled,
    showDeleteModal,
    setShowDeleteModal,
    chatToDelete,
    handleSessionSelect: baseHandleSessionSelect,
    handleDeleteChat,
    confirmDeleteChat,
    cancelDeleteChat,
    createSession,
    triggerExecution: baseExecute,
    refreshSessions,
    setSessions: setChatSessions,
    setSelectedSession,
  } = useSessionChat({
    scope: 'private',
    enableSharingStatusChecks: true,
    onStreamChunk: handleStreamChunk,
  });

  // Derived state: Chat-only mode is active for shared link sessions
  const isChatOnlyMode = selectedSession?.fromSharedLink ?? false;

  // Blueprint validation hook
  const {
    isValidating: isValidatingBlueprint,
    validationResults: blueprintValidationResults,
    isValid: isBlueprintValid,
    validateBlueprint: validateSelectedBlueprint,
  } = useBlueprintValidation({
    onCacheResults: cacheBlueprintValidationResults,
    showToastOnFailure: true,
  });

  // Custom session select handler with additional logic
  const handleSessionSelect = useCallback(async (session: any) => {
    // Trigger blueprint validation
    if (session.blueprintId) {
      validateSelectedBlueprint(session.blueprintId);
    }

    // For chat-only sessions (shared links), configure panel layout
    if (session.fromSharedLink) {
      setIsBlueprintGraphHidden(false);
      setBlueprintGraphWidth(30);
      const remainingWidth = 100 - chatSidebarWidth - 30;
      setChatInterfaceWidth(remainingWidth);
    }

    await baseHandleSessionSelect(session);
  }, [baseHandleSessionSelect, validateSelectedBlueprint, chatSidebarWidth]);

  // Toggle Blueprint Graph visibility
  const toggleBlueprintGraph = () => {
    if (isChatOnlyMode) {
      return;
    }

    if (isBlueprintGraphHidden) {
      const availableWidth = 100 - chatSidebarWidth;
      const restoredGraphWidth = savedBlueprintGraphWidth;
      const newChatInterfaceWidth = availableWidth - restoredGraphWidth;

      setChatInterfaceWidth(newChatInterfaceWidth);
      setBlueprintGraphWidth(restoredGraphWidth);
      setIsBlueprintGraphHidden(false);
    } else {
      setSavedBlueprintGraphWidth(blueprintGraphWidth);
      const availableWidth = 100 - chatSidebarWidth;

      setChatInterfaceWidth(availableWidth);
      setBlueprintGraphWidth(0);
      setIsBlueprintGraphHidden(true);
    }
  };

  // Resizable panel handlers
  const handleMouseDown = (resizer: 'left' | 'right') => (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    setActiveResizer(resizer);
  };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizing || !activeResizer) return;

    const containerRect = document.querySelector('.resizable-container')?.getBoundingClientRect();
    if (!containerRect) return;

    const mousePosition = ((e.clientX - containerRect.left) / containerRect.width) * 100;

    if (activeResizer === 'left') {
      const minChatSidebar = 15;
      const maxChatSidebar = 35;
      const newChatSidebarWidth = Math.min(Math.max(mousePosition, minChatSidebar), maxChatSidebar);
      const remainingWidth = 100 - newChatSidebarWidth;
      const newChatInterfaceWidth = (chatInterfaceWidth / (chatInterfaceWidth + blueprintGraphWidth)) * remainingWidth;
      const newBlueprintGraphWidth = remainingWidth - newChatInterfaceWidth;

      setChatSidebarWidth(newChatSidebarWidth);
      setChatInterfaceWidth(newChatInterfaceWidth);
      setBlueprintGraphWidth(newBlueprintGraphWidth);
    } else if (activeResizer === 'right') {
      const availableWidth = 100 - chatSidebarWidth;
      const relativePosition = ((mousePosition - chatSidebarWidth) / availableWidth) * 100;
      const minChatInterface = 25;
      const maxChatInterface = 100;
      const newChatInterfaceRatio = Math.min(Math.max(relativePosition, minChatInterface), maxChatInterface);

      const newChatInterfaceWidth = (availableWidth * newChatInterfaceRatio) / 100;
      const newBlueprintGraphWidth = availableWidth - newChatInterfaceWidth;

      setChatInterfaceWidth(newChatInterfaceWidth);
      setBlueprintGraphWidth(newBlueprintGraphWidth);
    }
  }, [isResizing, activeResizer, chatSidebarWidth, chatInterfaceWidth, blueprintGraphWidth]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
    setActiveResizer(null);
  }, []);

  // Add event listeners for mouse move and up
  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
    } else {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  // Node list update for streaming
  const updateNodeList = useCallback((chunkData: ChunkData) => {
    const { node, display_name, type, chunk, state, tool, output, call_id, args, action, plan_id, thread_id, owner_uid, workplan } = chunkData;
    const map = nodeListRef.current;

    let existing = map.get(node);

    if (!existing) {
      existing = {
        node_name: display_name,
        node_uid: node,
        stream: type === 'complete' ? 'DONE' : 'PROGRESS',
        text: '',
        tools: [],
        workplans: [],
      };
      map.set(node, existing);
    }

    switch (type) {
      case 'llm_token':
        if (chunk) {
          existing.text += chunk;
        }
        break;

      case 'tool_calling':
        if (call_id && tool) {
          const existingTool = existing.tools?.find((t: any) => t.id === call_id);
          if (!existingTool) {
            existing.tools?.push({ id: call_id, name: tool, args });
          }
        }
        break;

      case 'tool_result':
        if (call_id && tool && output) {
          const toolEntry = existing.tools?.find((t: any) => t.id === call_id);
          if (toolEntry) {
            toolEntry.output = output;
          } else {
            existing.tools?.push({ id: call_id, name: tool, output });
          }
        }
        break;

      case 'workplan_snapshot':
        if (plan_id && workplan && action) {
          if (!existing.workplans) {
            existing.workplans = [];
          }

          const workplanSnapshot = {
            type: 'workplan_snapshot' as const,
            action: action as 'loaded' | 'saved' | 'deleted',
            plan_id: plan_id,
            thread_id: thread_id || '',
            owner_uid: owner_uid || node,
            node: node,
            display_name: display_name,
            workplan: workplan
          };

          const existingPlanIndex = existing.workplans.findIndex(
            (wp: any) => wp.plan_id === plan_id
          );

          if (existingPlanIndex !== -1) {
            existing.workplans[existingPlanIndex] = workplanSnapshot;
          } else {
            existing.workplans.push(workplanSnapshot);
          }
        }
        break;

      default:
        break;
    }
  }, [nodeListRef]);

  // Custom trigger execution with live request state
  const triggerExecution = useCallback(async (sessionPayload: SessionPayload) => {
    setIsLiveRequest(true);
    try {
      const result = await baseExecute({
        sessionId: sessionPayload.sessionId,
        inputs: sessionPayload.inputs,
        stream: sessionPayload.stream,
        streamMode: ['custom'],
      });
      return result;
    } finally {
      setIsLiveRequest(false);
    }
  }, [baseExecute]);

  // Handle add flow modal
  const handleAddFlowClick = () => {
    setShowAddFlowModal(true);
  };

  const handleFlowSelect = (flow: FlowObject | null): void => {
    setSelectedFlowForModal(flow);
  };

  const handleAddFlow = async () => {
    if (!selectedFlowForModal) return;

    const graphId = selectedFlowForModal.id || `graph-${Date.now()}`;
    const sessionId = await createSession(graphId);

    if (sessionId) {
      setShowAddFlowModal(false);
      setSelectedFlowForModal(null);

      // Find and select the new session
      await refreshSessions();
    }
  };

  const handleCancelAddFlow = () => {
    setShowAddFlowModal(false);
    setSelectedFlowForModal(null);
  };

  // Cleanup effect when modal closes
  useEffect(() => {
    if (!showAddFlowModal && selectedFlowForModal) {
      setSelectedFlowForModal(null);
    }
  }, [showAddFlowModal]);

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

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-heading font-semibold">AI Assistant</h2>
          <p className="text-sm text-gray-400 mt-1">
            Interact with your AI assistant and monitor execution details
          </p>
        </div>
      </div>

      <div className="flex resizable-container gap-0" style={{ height: "calc(100vh - 230px)" }}>
        {/* Available Chats Sidebar */}
        <ChatHistorySidebar
          sessions={chatSessions}
          selectedSession={selectedSession}
          isLoading={isLoading}
          isCreatingSession={isCreatingSession}
          onSessionSelect={handleSessionSelect}
          onDeleteChat={handleDeleteChat}
          onAddFlow={handleAddFlowClick}
          title="Available Chats"
          showUsersButton={true}
          addFlowUmamiEvent={UmamiEvents.AGENT_CHAT_ADD_FLOW_BUTTON}
          deleteUmamiEvent={UmamiEvents.AGENT_CHAT_DELETE_CHAT_BUTTON}
          emptyMessage="No chat sessions available"
          style={{ width: `${chatSidebarWidth}%` }}
        />

        {/* First Resizable divider */}
        <div
          className={`w-1 cursor-col-resize transition-colors duration-200 flex-shrink-0 ${
            isResizing && activeResizer === 'left' ? 'opacity-100' : 'opacity-50'
          }`}
          style={{
            backgroundColor: 'hsl(var(--primary))',
          }}
          onMouseDown={handleMouseDown('left')}
          title="Drag to resize panels"
        />

        {/* ChatInterface Area - Dynamic width */}
        <div className="flex-shrink-0 flex flex-col" style={{ width: `${chatInterfaceWidth}%` }}>
          <div className="flex-grow">
            <ChatInterface
              runId={selectedSession?.id || ''}
              triggerExecution={triggerExecution}
              initialMessages={currentSessionMessages}
              blueprintExists={selectedSession?.blueprintExists ?? true}
              isSharingDisabled={isSharingDisabled}
              blueprintValid={isBlueprintValid}
              isValidatingBlueprint={isValidatingBlueprint}
              onToggleBlueprintGraph={toggleBlueprintGraph}
              isBlueprintGraphHidden={isBlueprintGraphHidden}
              isChatOnlyMode={isChatOnlyMode}
            />
          </div>

          {/* ExecutionStream - conditionally rendered within ChatInterface area */}
          {selectedSession && showExecutionStream && (
            <div className="h-1/3 border-t border-gray-800 mt-2">
              <ExecutionStream
                blueprintId={selectedSession.blueprintId}
                isLiveRequest={isLiveRequest}
              />
            </div>
          )}
        </div>

        {/* Second Resizable divider - only show when right panel is visible */}
        {(isChatOnlyMode || !isBlueprintGraphHidden) && (
          <div
            className={`w-1 transition-colors duration-200 flex-shrink-0 ${
              isChatOnlyMode ? 'cursor-default' : 'cursor-col-resize'
            } ${
              isResizing && activeResizer === 'right' ? 'opacity-100' : 'opacity-50'
            }`}
            style={{
              backgroundColor: 'hsl(var(--primary))',
            }}
            onMouseDown={isChatOnlyMode ? undefined : handleMouseDown('right')}
            title={isChatOnlyMode ? "Workflow not available for chat-only sessions" : "Drag to resize panels"}
          />
        )}

        {/* Blueprint Graph Visualization or Chat-Only Message - Dynamic width */}
        {(isChatOnlyMode || !isBlueprintGraphHidden) && (
          <div className="flex-shrink-0" style={{ width: `${blueprintGraphWidth}%` }}>
            <Card className="bg-background-card shadow-card border-gray-800 h-full flex flex-col ml-0">
              <CardContent className="p-0 flex-grow">
                {isChatOnlyMode ? (
                  <div className="flex items-center justify-center h-full text-gray-400 text-sm flex-col p-6">
                    <p className="mb-2 text-base">This session was created from a shared chat link</p>
                    <p className="text-xs text-gray-500 mb-1">
                      Workflow: <span className="font-medium text-gray-300">
                        {isLoadingBlueprintName ? "Loading..." : (sharedLinkBlueprintName || "Unknown")}
                      </span>
                    </p>
                    <p className="text-xs text-gray-500">Workflow details are not available in shared link sessions</p>
                    {isSharingDisabled && (
                      <div className="mt-4 p-3 bg-red-900/20 border border-red-800 rounded-md">
                        <p className="text-xs text-red-400">Chat sharing has been disabled for this workflow</p>
                      </div>
                    )}
                  </div>
                ) : selectedSession?.blueprintId ? (
                  <ReactFlowProvider key={`main-graph-${selectedSession.blueprintId}`}>
                    <ReactFlowGraph
                      blueprintId={selectedSession.blueprintId}
                      height="100%"
                      showControls={true}
                      showMiniMap={false}
                      showBackground={true}
                      interactive={true}
                      isLiveRequest={isLiveRequest}
                      validationResults={blueprintValidationResults}
                      isValidating={isValidatingBlueprint}
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
        )}
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
              <WorkflowsPanel
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
