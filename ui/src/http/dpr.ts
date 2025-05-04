import apiClient from "./axiosConfig";

export const dprInstall = async (data: any, mode: string): Promise<any> => {
    try {      
      const response = await apiClient.post<{ response: any }>("/api/dpr/install", { data: data, mode: mode });  
      return response.data || {}; 
    } catch (error) {
      console.error("❌ Error starting install:", error);
      return [];
    }
};

export const dprUninstall = async (datasetId: string, status: string): Promise<any> => {
    try {      
      const response = await apiClient.post<{ response: any }>("/api/dpr/uninstall", { id: datasetId, status: status });  
      return response.data || ''; 
    } catch (error) {
      console.error("❌ Error starting uninstall:", error);
      return [];
    }
};

export const dprDelete = async (datasetId: string): Promise<any> => {
    try {      
      const response = await apiClient.post<{ response: any }>("/api/dpr/delete", { id: datasetId });  
      return response.data || ''; 
    } catch (error) {
      console.error("❌ Error deleting row:", error);
      return [];
    }
};

export const getStats = async (datasetId: string): Promise<any> => {
  try {
    const response = await apiClient.get<{ response: any }>("/api/dpr/getStats", { params: { id: datasetId} });
    return response.data || {};
  } catch (error) {
    console.error("Error fetching statistics:", error);
    return [];
  }
};

// export const getMetrics = async (datasetId: string, name: string): Promise<any> => {
//   try {
//     const response = await apiClient.get<{ response: any }>("/api/dpr/metrics", { params: { id: datasetId, name: name} });
//     return response.data || [];
//   } catch (error) {
//     console.error("Error fetching metrics:", error);
//     return [];
//   }
// };

export const getConfigFile = async (datasetId: string): Promise<any> => {
  try {
    const response = await apiClient.get<{ response: any }>("/api/dpr/getConfigFile", { params: { id: datasetId } });
    return response.data || [];
  } catch (error) {
    console.error("Error fetching configuration file:", error);
    return [];
  }
};

export const displayedDeployments = async (): Promise<any> => {
  try {
    const response = await apiClient.get<{ response: any }>("/api/dpr/displayDeployments");
    console.log(response)
    return response.data || {};
  } catch (error) {
    console.error("Error fetching displayed deployments:", error);
    return [];
  }
};