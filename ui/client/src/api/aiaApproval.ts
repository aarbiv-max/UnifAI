import { api } from '../http/queryClient';

export interface UserApprovalStatus {
  approved: boolean;
  username: string;
}

export interface ApproveUserResponse {
  status: string;
  message: string;
  username: string;
  approved: boolean;
}

/**
 * Check if a user has approved the AI transparency notice
 */
export async function checkUserApproval(username: string): Promise<UserApprovalStatus> {
  try {
    const response = await api.get(`aia_approval/check?username=${encodeURIComponent(username)}`);
    return response.data;
  } catch (error: any) {
    throw error;
  }
}

/**
 * Approve a user for AI transparency notice (add to approved list)
 */
export async function approveUser(username: string): Promise<ApproveUserResponse> {
  try {
    const response = await api.post('aia_approval/approve', { username });
    return response.data;
  } catch (error: any) {
    throw error;
  }
}

