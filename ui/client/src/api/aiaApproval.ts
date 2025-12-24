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
    console.log('Check approval response:', response.data);
    return response.data;
  } catch (error: any) {
    console.error('Error checking user approval:', error);
    console.error('Error details:', error.response?.data, error.response?.status);
    throw error;
  }
}

/**
 * Approve a user for AI transparency notice (add to approved list)
 */
export async function approveUser(username: string): Promise<ApproveUserResponse> {
  try {
    console.log('Approving user:', username);
    const response = await api.post('aia_approval/approve', { username });
    console.log('Approve user response:', response.data);
    return response.data;
  } catch (error: any) {
    console.error('Error approving user:', error);
    console.error('Error details:', error.response?.data, error.response?.status, error.response?.config?.url);
    throw error;
  }
}

