import React from 'react';
import CreateTrainingJson from './CreateTrainingJson';
import InstallForm from '../shared/InstallForm';
import { trainingInstall } from '../../http/training';
import UploadJsonForm from '../shared/UploadJsonForm';

const exampleJson = `
      {"api_url": "https://api.stc-ai-e1-prod.rtc9.p1.openshiftapps.com:6443",
      "Global":{
          "deployment_name": "genie-training-new",
          "namespace": "tag-ai--pipeline",
          "cluster": "production"},
      "ConfigMap":{
      "data": {
          "GPU_NUM": "2",
          "PROJECT": "openshift-builds-operator",
          "DATASET_REPO": "cia-tools/openshift-builds-operator",
          "DATASET_FILE_NAME": "train-openshift-builds-operator.json"
          }
      },
      "ConfigMapTrainerArgs":{
      "data": {
          "MODEL_NAME_OR_PATH": "Qwen/Qwen2.5-Coder-14B-Instruct",
          "LORA_RANK": "16",
          "LORA_ALPHA": "16",
          "LORA_DROPOUT": "0.1",
          "TEMPLATE": "qwen",
          "MAX_SAMPLES": "500000",
          "NUM_TRAIN_EPOCHS": "3",
          "GRADIENT_ACCUMULATION_STEPS": "16",
          "PER_DEVICE_TRAIN_BATCH_SIZE": "1",
          "LEARNING_RATE": "!!float 5e-5",
          "QUANTIZATION": "True"}}}
          `;

const TrainingForm: React.FC = () => (
  <InstallForm
    apiFunction={trainingInstall}
    uploadComponent={UploadJsonForm}
    createComponent={CreateTrainingJson}
    redirectPath="/deployed-training"
    exampleJson={exampleJson}
  />
);

export default TrainingForm;
