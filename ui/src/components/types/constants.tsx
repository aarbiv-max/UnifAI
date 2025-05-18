export interface FormData {
    projectName: string;
    trainingName: string;
    gitUrl: string;
    gitCredentialKey: string;
    gitFolderPath?: string;
    gitBranchName: string;
    testsCodeFramework: string;
    numberOfTests: number;
    datasetGradingUpgrade?: boolean;}

export interface TableFormData {
    projectName: string;
    trainingName: string;
    baseModelName: 'Mistral' | 'Llama' | 'Granite' | 'Qwen';
    testsCodeFramework: 'Python' | 'Robot' | 'Go' | 'Jmeter' | '-';
    status: 'Initial' | 'In progress' | 'Finished';
    progress: string; // Represented by percentage (e.g., "50%")
    modelType: 'finetuned' | 'foundational' | 'checkpoint';
    checkpoint?: string;
}

export interface ModelDataResponse {
    base_model_name: string;
    quantized: boolean;
    adapters: Adapters[];
    uid: string;
    model_type: 'llama' | 'qwen' | null;
}

export interface Adapters {
    name: string;
    project: string;
    quantized: boolean,
    base_model: string;
    context_length: number;
    local_adapter_path: string;
    adapter_uid: string;
    repo_internal_location?: string; 
}

export interface ModelData {
    modelId: string;
    modelName: string;
    hfRepoId?: string;
    repoInternalLocation?: string; 
    trainingName: string;
    modelMaxSeqLen: number;
    modelType: 'llama' | 'qwen' | null;
    gitReposLink?: string[];
    project: string;
    checkpoint?: string,
    finetuneSteps?: any[], 
    promptTemplate?: {
        assistant_tag: string;
        end_tag: string;
        user_tag: string;
    };
    isRagEnabled?: boolean;
    isPackageSelectionRagEnabled?: boolean;
    // numTests: string,
    // dataSize: string,
}
