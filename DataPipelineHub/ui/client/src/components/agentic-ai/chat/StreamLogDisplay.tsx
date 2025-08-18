import React, { memo, useCallback } from 'react';
import { Message } from './types';
import { StreamLogItem } from './StreamLogItem';

interface StreamLogDisplayProps {
  message: Message;
  onToggleExpansion: (messageId: string, nodeId: string) => void;
}

export const StreamLogDisplay = memo(({ message, onToggleExpansion }: StreamLogDisplayProps) => {
  const memoizedToggleExpansion = useCallback((messageId: string, nodeId: string) => {
    onToggleExpansion(messageId, nodeId);
  }, [onToggleExpansion]);

  if (!message.streamLogs || message.streamLogs.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 space-y-2 w-full">
      {message.streamLogs.map((log) => (
        <StreamLogItem
          key={log.nodeId}
          log={log}
          messageId={message.id}
          onToggleExpansion={memoizedToggleExpansion}
        />
      ))}
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison for memo - optimized for streaming updates
  const prevLogs = prevProps.message.streamLogs || [];
  const nextLogs = nextProps.message.streamLogs || [];
  
  // If the number of logs changed, definitely re-render
  if (prevLogs.length !== nextLogs.length) {
    return false;
  }
  
  // Check if message ID changed
  if (prevProps.message.id !== nextProps.message.id) {
    return false;
  }
  
  // Optimized comparison of streamLogs - focus on structural changes
  for (let i = 0; i < prevLogs.length; i++) {
    const prevLog = prevLogs[i];
    const nextLog = nextLogs[i];
    
    // Check critical properties that require re-render
    if (
      prevLog.nodeId !== nextLog.nodeId ||
      prevLog.status !== nextLog.status ||
      prevLog.isExpanded !== nextLog.isExpanded ||
      prevLog.nodeName !== nextLog.nodeName
    ) {
      return false;
    }
    
    // For message content, only re-render if it's not a streaming append
    if (prevLog.message !== nextLog.message) {
      // If the new message doesn't start with the old message, it's a replacement
      if (!nextLog.message.startsWith(prevLog.message)) {
        return false;
      }
    }
    
    // Check tools length (tools being added/removed)
    const prevTools = prevLog.tools || [];
    const nextTools = nextLog.tools || [];
    if (prevTools.length !== nextTools.length) {
      return false;
    }
  }
  
  return true;
});