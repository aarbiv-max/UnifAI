/**
 * Reusable Chat History Sidebar Component
 * Used by both ExecutionTab and PublicChat for displaying chat session lists
 */

import React from 'react';
import { motion } from 'framer-motion';
import { MessageSquare, Clock, Plus, Trash2, Users, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChatSession } from '@/types/session';
import { UmamiTrack } from '@/components/ui/umamitrack';

// ────────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────────

export interface ChatHistorySidebarProps {
  /** List of chat sessions to display */
  sessions: ChatSession[];
  /** Currently selected session */
  selectedSession: ChatSession | null;
  /** Loading state for sessions */
  isLoading: boolean;
  /** Creating session state */
  isCreatingSession?: boolean;
  /** Callback when a session is selected */
  onSessionSelect: (session: ChatSession) => void;
  /** Callback when delete is clicked on a session */
  onDeleteChat: (session: ChatSession, event: React.MouseEvent) => void;
  /** Callback when new chat button is clicked (optional - shown if provided) */
  onNewChat?: () => void;
  /** Callback when add flow button is clicked (optional - shown if provided) */
  onAddFlow?: () => void;
  /** Title for the sidebar */
  title?: string;
  /** Show user/collaboration button */
  showUsersButton?: boolean;
  /** Umami event for new chat button */
  newChatUmamiEvent?: string;
  /** Umami event for add flow button */
  addFlowUmamiEvent?: string;
  /** Umami event for delete button */
  deleteUmamiEvent?: string;
  /** Custom empty state message */
  emptyMessage?: string;
  /** Additional class name for the container */
  className?: string;
  /** Style for the container (for dynamic widths) */
  style?: React.CSSProperties;
}

// ────────────────────────────────────────────────────────────────────────────────
// Component
// ────────────────────────────────────────────────────────────────────────────────

export const ChatHistorySidebar: React.FC<ChatHistorySidebarProps> = ({
  sessions,
  selectedSession,
  isLoading,
  isCreatingSession = false,
  onSessionSelect,
  onDeleteChat,
  onNewChat,
  onAddFlow,
  title = 'Available Chats',
  showUsersButton = false,
  newChatUmamiEvent,
  addFlowUmamiEvent,
  deleteUmamiEvent,
  emptyMessage = 'No chat sessions available',
  className = '',
  style,
}) => {
  const renderNewChatButton = () => {
    const button = (
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 text-primary hover:bg-primary/20 flex-shrink-0"
        onClick={onNewChat}
        disabled={isCreatingSession}
        title="Start new chat"
      >
        {isCreatingSession ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <Plus className="h-4 w-4" />
        )}
      </Button>
    );

    if (newChatUmamiEvent) {
      return <UmamiTrack event={newChatUmamiEvent}>{button}</UmamiTrack>;
    }
    return button;
  };

  const renderAddFlowButton = () => {
    const button = (
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 text-[#03DAC6] hover:bg-[#03DAC6] hover:bg-opacity-20 flex-shrink-0"
        onClick={onAddFlow}
        title="Add new chat from flow"
      >
        <Plus className="h-3 w-3" />
      </Button>
    );

    if (addFlowUmamiEvent) {
      return <UmamiTrack event={addFlowUmamiEvent} includeUserData={false}>{button}</UmamiTrack>;
    }
    return button;
  };

  const renderDeleteButton = (session: ChatSession) => {
    const button = (
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 text-gray-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
        onClick={(e) => onDeleteChat(session, e)}
      >
        <Trash2 className="h-3 w-3" />
      </Button>
    );

    if (deleteUmamiEvent) {
      return <UmamiTrack event={deleteUmamiEvent} includeUserData={false}>{button}</UmamiTrack>;
    }
    return button;
  };

  return (
    <div className={`flex-shrink-0 ${className}`} style={style}>
      <Card className="bg-background-card shadow-card border-gray-800 h-full flex flex-col mr-0">
        <CardHeader className="py-3 px-4 border-b border-gray-800 overflow-hidden">
          <div className="flex justify-between items-center min-w-0 w-full max-w-full">
            <CardTitle className="text-sm font-medium truncate flex-1 min-w-0 mr-2">
              {title} ({sessions.length})
            </CardTitle>
            <div className="flex items-center gap-1 flex-shrink-0 max-w-fit">
              {showUsersButton && (
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0 flex-shrink-0">
                  <Users className="h-3 w-3" />
                </Button>
              )}
              {onAddFlow && renderAddFlowButton()}
              {onNewChat && renderNewChatButton()}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0 flex-grow overflow-y-auto">
          {isLoading ? (
            <div className="p-4 text-center">
              <Loader2 className="h-5 w-5 animate-spin mx-auto text-primary" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-4 text-center text-gray-400 text-sm">
              {emptyMessage}
            </div>
          ) : (
            <div className="h-full max-h-[75vh] overflow-y-auto py-2">
              {sessions.map((session) => (
                <motion.div
                  key={session.id}
                  className={`group px-4 py-3 border-l-2 cursor-pointer ${
                    selectedSession?.id === session.id
                      ? 'border-[hsl(var(--primary))] bg-primary/20'
                      : 'border-transparent hover:bg-background-surface'
                  } ${
                    !session.blueprintExists || session.isSharingDisabled
                      ? 'opacity-50 bg-gray-800/30'
                      : ''
                  }`}
                  onClick={() => onSessionSelect(session)}
                  whileHover={{ x: 2 }}
                  transition={{ duration: 0.1 }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center min-w-0 flex-1">
                      <MessageSquare className="h-4 w-4 mr-2 text-gray-400 flex-shrink-0" />
                      <span className="text-sm font-medium truncate text-white">
                        {session.title}
                      </span>
                    </div>
                    {renderDeleteButton(session)}
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
  );
};

export default ChatHistorySidebar;

