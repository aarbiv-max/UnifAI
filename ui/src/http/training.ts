import apiClient from "./axiosConfig";

export const trainingInstall = async (data: any, mode: string): Promise<any> => {
  try {      
    const response = await apiClient.post<{ response: any }>("/api/training/install", { data: data, mode: mode });  
    return response.data || {}; 
  } catch (error) {
    console.error("❌ Error starting install:", error);
    return [];
  }
};

export const trainingUninstall = async (modelId: string, status: string): Promise<any> => {
    try {      
      const response = await apiClient.post<{ response: any }>("/api/training/uninstall", { id: modelId, status: status });  
      return response.data.response || ''; 
    } catch (error) {
      console.error("❌ Error starting uninstall:", error);
      return [];
    }
};

export const getRunningDeployment = async (): Promise<any> => {
  try {
    const response = await apiClient.get<{ response: any }>("/api/training/runningDeployment");
    return response.data.response || {};
  } catch (error) {
    console.error("Error fetching displayed deployments:", error);
    return [];
  }
};

export const getDatasetsForTraining = async (): Promise<any> => {
  try {
    const response = await apiClient.get<{ response: any }>("/api/training/availableDatasets");
    return response.data.response || {};
  } catch (error) {
    console.error("Error fetching displayed deployments:", error);
    return [];
  }
};

export const getTrainedModels = async (): Promise<any> => {
  try {
    const response = await apiClient.get<{ response: any }>("/api/training/trainedModels");
    return response.data.response || [];
  } catch (error) {
    console.error("Error fetching displayed deployments:", error);
    return [];
  }
};

export const registeredModel = async (modelId: string): Promise<any> => {
  try {
    const response = await apiClient.post<{ response: any }>("/api/training/register", { id: modelId });   ;
    return response.data.response || [];
  } catch (error) {
    console.error("Error fetching displayed deployments:", error);
    return [];
  }
};