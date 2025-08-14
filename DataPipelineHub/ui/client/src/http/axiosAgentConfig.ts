import axios from 'axios';

export const AXIOS_AGENTS_IP= 'https://unifai-dataflow-server-tag-ai--pipeline.apps.stc-ai-e1-prod.rtc9.p1.openshiftapps.com'

const axiosInstance = axios.create({
  baseURL: 'https://unifai-dataflow-server-tag-ai--pipeline.apps.stc-ai-e1-prod.rtc9.p1.openshiftapps.com',
  timeout: 300000, // 300 seconds
});

export default axiosInstance;