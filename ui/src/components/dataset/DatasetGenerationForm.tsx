import React from 'react';
import CreateDatasetJson from './CreateDatasetJson';
import { dprInstall } from '../../http/dpr';
import InstallForm from '../shared/InstallForm';
import UploadJsonForm from '../shared/UploadJsonForm';

const exampleJson = `{
  global: {
      api_url: "https://api.stc-ai-e1-pp.imap.p1.openshiftapps.com:6443", // for prod: "https://api.stc-ai-e1-prod.rtc9.p1.openshiftapps.com:6443"
      deployment_name: "example", // the deployment name should be lowercase, and not contain any spaces, -, or _
      namespace: "tag-ai--mcarmi-nb",
      enable_toleration: false,
      multiple_gpu_per_pod: false,
      number_of_gpu: 1,
      vllm_orbiter_replica: 1,
      enable_reviewer: false, // if set to true, need to add more fields
      orbiter_replica: 1,
      hf_token: "mcarmi-hf-token",
      orbiter_model_hf_id: "Qwen/Qwen2.5-Coder-1.5B-Instruct",
      vllm_orbiter_args: ["--max_model_len", 16000, "--gpu_memory_utilization", 0.88],
      promptlab_env: {
          PROMPT_LAB_MODEL_HF_ID: "Qwen/Qwen2.5-Coder-1.5B-Instruct",
          PROMPT_LAB_MAX_GENERATION_LENGTH: 2048,
          PROMPT_LAB_MAX_CONTEXT_LENGTH: 16000,
          PROMPT_LAB_BATCH_SIZE: 8,
          QUEUE_TARGET_SIZE: 8,
          TEMPLATE_AGENT: "TAG",
          TEMPLATE_NAME: "",
          TEMPLATE_TYPE: "go",
          MAX_RETRY: 3,
          INPUT_DATASET_REPO: "mcarmi/testing_dpr",
          INPUT_DATASET_FILE_NAME: "myfile.json",
          OUTPUT_DATASET_REPO: "mcarmi/testing_dpr",
          OUTPUT_DATASET_FILE_NAME: "train-myfile_output", // this field must begin with "train-"
          TEMPLATE_PROJECT_CONTEXT: "",
          PROJECT_ID: "",
          PROJECT_REPO: ""
      }
  }
}`;


const DatasetGenerationForm: React.FC = () => (
  <InstallForm
    apiFunction={dprInstall}
    uploadComponent={UploadJsonForm}
    createComponent={CreateDatasetJson}
    redirectPath="/deployed-datasets"
    exampleJson={exampleJson}
  />
);

export default DatasetGenerationForm;
