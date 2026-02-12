import axios from '@/http/axiosAgentConfig';

export interface CreateSessionParams {
  blueprintId: string;
  userId: string;
}

export async function createSession(params: CreateSessionParams) {
  const response = await axios.post('/sessions/user.session.create', params);
  return response.data;
}