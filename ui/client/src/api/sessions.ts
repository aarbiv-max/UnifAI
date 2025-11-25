/**
 * API service for session-related operations.
 * Centralized source of truth for all session API calls.
 */

import axios from '../http/axiosAgentConfig';

export interface CreateSessionRequest {
  blueprintId: string;
  userId: string;
  metadata?: Record<string, any>;
}

export interface SessionStateData {
  final_output: string;
  messages: Array<{
    content: string;
    role: 'user' | 'assistant';
  }>;
}

export interface ChatSessionData {
  metadata: Record<string, any>;
  blueprint_id: string;
  session_id: string;
  started_at: string;
  blueprint_exists: boolean;
}

/**
 * Create a new user session
 * @param request - Session creation request
 * @returns Promise resolving to the session run_id
 */
export const createUserSession = async (
  request: CreateSessionRequest
): Promise<string> => {
  const response = await axios.post(
    "/sessions/user.session.create",
    {
      blueprintId: request.blueprintId,
      userId: request.userId,
      ...(request.metadata && { metadata: request.metadata }),
    }
  );
  return response.data;
};

/**
 * Get session state (messages and final output)
 * @param sessionId - The session ID
 * @returns Promise resolving to session state data
 */
export const getSessionState = async (
  sessionId: string
): Promise<SessionStateData | null> => {
  try {
    const response = await axios.get(
      `/sessions/session.state.get?sessionId=${sessionId}`
    );
    return response.data;
  } catch (err) {
    console.error('Error fetching session state:', err);
    return null;
  }
};

/**
 * Get all chat sessions for a user
 * @param userId - The user ID
 * @returns Promise resolving to array of chat session data
 */
export const getUserChatSessions = async (
  userId: string
): Promise<ChatSessionData[]> => {
  const response = await axios.get(
    `/sessions/session.user.chat.get?userId=${userId}`
  );
  return response.data;
};

/**
 * Delete a session
 * @param sessionId - The session ID to delete
 * @returns Promise that resolves when deletion is complete
 */
export const deleteSession = async (sessionId: string): Promise<void> => {
  await axios.delete(`/sessions/session.delete?sessionId=${sessionId}`);
};

/**
 * Execute a session
 * @param payload - Session execution payload
 * @returns Promise resolving to the execution response
 */
export const executeSession = async (payload: {
  sessionId: string;
  inputs: Record<string, any>;
  stream?: boolean;
  streamMode?: string[];
  scope?: 'public' | 'private';
  loggedInUser?: string;
}): Promise<any> => {
  const response = await axios.post(
    "/sessions/user.session.execute",
    {
      sessionId: payload.sessionId,
      inputs: payload.inputs,
      stream: payload.stream ?? false,
      streamMode: payload.streamMode ?? ["custom"],
      scope: payload.scope ?? "public",
      loggedInUser: payload.loggedInUser ?? "",
    }
  );
  return response.data;
};

