import React, { useEffect, useState } from 'react';
import { useForm, SubmitHandler } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { FormCheckbox, FormDropdown, FormField } from '../shared/FormFields'
import { Box, Button, Step, StepContent, Stepper } from '@mui/material'; 
import '../../styles.css';
import { CustomStepIcon, CustomStepLabel } from '../shared/StepperIcons';
import { LoadingOverlay } from '../shared/LoadingOverlay';
import { FormButton } from '../shared/FormButton';
import axios from 'axios';
import { getDatasetsForTraining } from '../../http/training';


type InputSelectionProps = {
    combinedDataset: string;
    DATASET_REPO: string;
    DATASET_FILE_NAME: string;
};

type GlobalProps = {
    deployment_name: string;
    namespace: string;
    cluster: string;
};

type TrainingProps = {
    GPU_NUM: string;
    PROJECT: string;
    MODEL_NAME_OR_PATH: string;
    LORA_RANK: string;
    LORA_ALPHA: string;
    LORA_DROPOUT: string;
    TEMPLATE: string;
    MAX_SAMPLES: string;
    NUM_TRAIN_EPOCHS: string;
    GRADIENT_ACCUMULATION_STEPS: string;
    PER_DEVICE_TRAIN_BATCH_SIZE: string;
    LEARNING_RATE: string;
    QUANTIZATION: boolean;
};

const schema = yup.object().shape({
    inputSelection: yup.object({
        combinedDataset: yup.string().required('Dataset selection is required'),
        DATASET_REPO: yup.string().required('Cluster Selection is required'),
        DATASET_FILE_NAME: yup.string().required('Dataset file name is required'),
    }),
    Global: yup.object({
        deployment_name: yup.string().required('Deployment name is required'),      
        namespace: yup.string().required('Namespace is required'),      
        cluster: yup.string().required('Cluster is required')
    }),
    training: yup.object({
        GPU_NUM: yup.string().required('GPU Number is required'),
        PROJECT: yup.string().required('Project is required'),
        MODEL_NAME_OR_PATH: yup.string().required('Prompt Lab Model HuggingFace ID is required').default('meta-llama/Llama-3.1-8B-Instruct'),
        LORA_RANK: yup.string().required('Orbiter Batch Size is required').typeError('Orbiter Batch Size should be a number'),
        LORA_ALPHA: yup.string().required('Queue Target Size is required').typeError('Queue Target Size should be a number'),
        LORA_DROPOUT: yup.string(),
        TEMPLATE: yup.string().required('Template Agent is required').default('TAG'),
        MAX_SAMPLES: yup.string().required('Max Generation Length is required').typeError('Max Generation Length should be a number'),
        NUM_TRAIN_EPOCHS: yup.string().required('Max Context Length is required').typeError('Max Context Length should be a number'),
        GRADIENT_ACCUMULATION_STEPS: yup.string(),
        PER_DEVICE_TRAIN_BATCH_SIZE: yup.string(),
        LEARNING_RATE: yup.string().required('Template Type is required'),
        QUANTIZATION: yup.boolean().required('Template Type is required')
    })
});

type CreateTrainingJsonProps = {
    onSubmit: SubmitHandler<any>;
    isLoading: boolean;
};

const CreateTrainingJson: React.FC<CreateTrainingJsonProps> = ({ onSubmit, isLoading }) => {
    const [activeStep, setActiveStep] = useState(0);
    const [isInputSelectionTabValid, setIsInputSelectionTabValid] = useState(false);
    const [isGlobalTabValid, setIsGlobalTabValid] = useState(false);
    const [isTrainingTabValid, setIsTrainingTabValid] = useState(false);
    const [inputSelectionList, setInputSelectionList] = useState<{ label: string; value: string }[]>([]);

    const defaultValues = {
        inputSelection:{
            combinedDataset: "",
            DATASET_REPO: "",
            DATASET_FILE_NAME: ""
        },
        Global: {
            deployment_name: "genie-training",
            namespace: "tag-ai--pipeline",
            cluster: "production"
        },
        training: {
            GPU_NUM: "2",
            PROJECT: "",
            MODEL_NAME_OR_PATH: "Qwen/Qwen2.5-Coder-14B-Instruct",
            LORA_RANK: "16",
            LORA_ALPHA: "16",
            LORA_DROPOUT: "0.1",
            TEMPLATE: "qwen",
            MAX_SAMPLES: "500000",
            NUM_TRAIN_EPOCHS: "1",
            GRADIENT_ACCUMULATION_STEPS: "16",
            PER_DEVICE_TRAIN_BATCH_SIZE: "1",
            LEARNING_RATE: "0.00005",
            QUANTIZATION: true
        }
    };

    const { control, handleSubmit, formState: { errors }, watch, reset, setValue } = useForm({
        resolver: yupResolver(schema),
        defaultValues, 
    });

    useEffect(() => {
        reset(defaultValues); 
    }, [reset]);

    const getRequiredFields = (schema: yup.ObjectSchema<any>): string[] => {
        return Object.keys(schema.fields).filter((key) => {
            const fieldSchema = schema.fields[key];
            if (fieldSchema && typeof fieldSchema === 'object' && 'spec' in fieldSchema) {
                const typedFieldSchema = fieldSchema as { spec: { optional?: boolean } };
                return typedFieldSchema.spec.optional === false;
            }
            return false;
        });
    };

    const checkTabValidity = (data: Record<string, any>, requiredFields: string[]): boolean => {
        return requiredFields.every((key) => {
            const value = data[key];
            return value !== null && value !== undefined && value !== "";
        });
    };

    const requiredInputFields = getRequiredFields(schema.fields.inputSelection as yup.ObjectSchema<any>);
    const requiredGlobalFields = getRequiredFields(schema.fields.Global as yup.ObjectSchema<any>);
    const requiredTrainingFields = getRequiredFields(schema.fields.training as yup.ObjectSchema<any>);

    const watchedInputValues = watch('inputSelection') || {} as InputSelectionProps;
    const watchedGlobalValues = watch('Global') || {} as GlobalProps;
    const watchedTrainingValues = watch('training') || {} as TrainingProps;


    useEffect(() => {
        if (watchedInputValues.combinedDataset) {
            const { repo, file } = JSON.parse(watchedInputValues.combinedDataset);
            setValue('inputSelection.DATASET_REPO', repo);
            setValue('inputSelection.DATASET_FILE_NAME', file);
        }
        setIsInputSelectionTabValid(checkTabValidity(watchedInputValues, requiredInputFields));
    }, [{...watchedInputValues}]);

    useEffect(() => {
        setIsGlobalTabValid(checkTabValidity(watchedGlobalValues, requiredGlobalFields));
    }, [{...watchedGlobalValues}]);

    useEffect(() => {
        setIsTrainingTabValid(checkTabValidity(watchedTrainingValues, requiredTrainingFields));
    }, [{...watchedTrainingValues}]);

    const handleNextClick = () => {
        setActiveStep(activeStep + 1);
    };

    const handleBackClick = () => {
      if (activeStep > 0) {
        setActiveStep((prev) => prev - 1);
      }
    };

    useEffect(() => {
        const fetchDatasetList = async () => {
            try {
                const datasets = await getDatasetsForTraining();
                setInputSelectionList(datasets?.map((item: any) => ({
                    label: `${item.repo}/${item.file}`,
                    value: JSON.stringify({ repo: item.repo, file: item.file })}
                )));
            } catch (error) {
                console.error("Error fetching data:", error);
            }
        };

        fetchDatasetList();
    }, []);
    

    const ClusterOptions = [
        { label: 'Production Cluster', value: 'production' },
        { label: 'Preproduction Cluster', value: 'preproduction' },
    ];


    return (
        <>
        {isLoading ?
        (<LoadingOverlay text="Helm installation has been triggered." />) :
        (<Box className="form-container">
            <Stepper activeStep={activeStep} orientation="vertical">
                <Step>
                    <CustomStepLabel StepIconComponent={(props) => <CustomStepIcon {...props} />}>
                        Input Selection
                    </CustomStepLabel>
                    <StepContent>
                        <Box className="form-section">
                            <FormDropdown
                                    name="inputSelection.combinedDataset"
                                    label="Select Dataset"
                                    control={control}
                                    errors={errors}
                                    options={inputSelectionList}
                                    />                      
                            <div className="form-bottom-button">
                                <Button type="button" variant="contained" className="end-button" onClick={handleNextClick} disabled={!isInputSelectionTabValid}>
                                    Next
                                </Button>
                            </div>
                        </Box>
                    </StepContent>
                </Step>
                <Step>
                    <CustomStepLabel StepIconComponent={(props) => <CustomStepIcon {...props} />}>
                        Global
                    </CustomStepLabel>
                    <StepContent>
                        <form className="form-section">
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                                <FormDropdown name="Global.cluster" label="Cluster Selection" control={control} errors={errors} options={ClusterOptions}/>
                                <FormField name="Global.namespace" label="Namespace" control={control} errors={errors} />
                                <FormField name="Global.deployment_name" label="Training Name" control={control} errors={errors}/>
                            </div>
                            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px'}}>
                                <FormButton type="button" text="Back" onClick={handleBackClick} />
                                <FormButton type="button" text="Next" onClick={handleNextClick} disabled={!isGlobalTabValid} />
                            </div>
                        </form>
                    </StepContent>
                </Step>
                <Step>
                    <CustomStepLabel StepIconComponent={(props) => <CustomStepIcon {...props} />}>
                    Training Arguments
                    </CustomStepLabel>
                    <StepContent>
                        <form className="form-section" onSubmit={handleSubmit(onSubmit)}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                                <FormField name="training.PROJECT" label="Project" control={control} errors={errors} />
                                <FormField name="training.MODEL_NAME_OR_PATH" label="Model Name or Path" control={control} errors={errors} />
                                <FormField name="training.TEMPLATE" label="Template" control={control} errors={errors} />
                                

                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr 1fr', gap: '16px' }}>
                                <FormField name="training.LORA_RANK" label="Lora Rank" control={control} errors={errors} />
                                <FormField name="training.LORA_ALPHA" label="Lora Alpha" control={control} errors={errors} />
                                <FormField name="training.LORA_DROPOUT" label="Lora Dropout" control={control} errors={errors} />
                                <FormField name="training.GPU_NUM" label="GPU Number" control={control} errors={errors} />
                                <FormField name="training.MAX_SAMPLES" label="Max Samples" control={control} errors={errors} />
                                <FormField name="training.NUM_TRAIN_EPOCHS" label="Train Epochs" control={control} errors={errors} />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 0.5fr', gap: '16px' }}>
                                <FormField name="training.GRADIENT_ACCUMULATION_STEPS" label="Gradient Accumulation Steps" control={control} errors={errors} />
                                <FormField name="training.PER_DEVICE_TRAIN_BATCH_SIZE" label="Batch Size" control={control} errors={errors} />
                                <FormField name="training.LEARNING_RATE" label="Learning Rate" control={control} errors={errors} />
                                <div style={{ alignSelf: 'center' }}>
                                    <FormCheckbox name="training.QUANTIZATION" label="Quantization" control={control} errors={errors} />
                                </div>
                            </div>
                            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px'}}>
                                <FormButton type="button" text="Back" onClick={handleBackClick} />
                                <FormButton type="submit" text="Install" disabled={!isTrainingTabValid} />
                            </div>
                        </form>
                    </StepContent>
                </Step>
            </Stepper>
        </Box>)
        }
      </>
    );
};

export default CreateTrainingJson;