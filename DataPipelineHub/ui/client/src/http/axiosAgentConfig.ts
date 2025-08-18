import axios from 'axios';

// export const AXIOS_AGENTS_IP= 'http://10.46.254.131:8002'
export const AXIOS_AGENTS_IP= 'http://unifai-multiagent-be-tag-ai--pipeline.apps.stc-ai-e1-prod.rtc9.p1.openshiftapps.com'

const axiosInstance = axios.create({
  baseURL: '/api2',
  timeout: 300000, // 300 seconds
});

export default axiosInstance;