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


type GlobalProps = {
    api_url: string;
    enable_toleration: boolean;
    multiple_gpu_per_pod: boolean;
    number_of_gpu: number;
    enable_reviewer: boolean;
    deployment_name: string;
    vllm_reviewer_replica: number;
    vllm_orbiter_replica: number;
    hf_token: string;
    orbiter_replica: number;
    reviewer_replica: number;
    namespace: string;
};

type PromptLabProps = {
    vllm_orbiter_args: {maxLength: number, gpuMemoryUtilization: number};
    PROMPT_LAB_BATCH_SIZE: number;
    QUEUE_TARGET_SIZE: number;
    TEMPLATE_PROJECT_CONTEXT: string;
    PROMPT_LAB_MODEL_HF_ID: string;
    MAX_RETRY: number;
    TEMPLATE_AGENT: string;
    PROMPT_LAB_MAX_GENERATION_LENGTH: number;
    PROMPT_LAB_MAX_CONTEXT_LENGTH: number;
    PROJECT_REPO: string;
    PROJECT_ID: string;
    TEMPLATE_TYPE: string;
    TEMPLATE_NAME: string;
    OUTPUT_DATASET_FILE_NAME: string;
    OUTPUT_DATASET_REPO: string;
};

type ReviewerProps = {
    vllm_reviewer_args: {maxLength: number, gpuMemoryUtilization: number};
    REVIEWER_MODEL_HF_ID: string;
    REVIEWER_MAX_GENERATION_LENGTH: number;
    REVIEWER_MAX_CONTEXT_LENGTH: number;
    REVIEWER_BATCH_SIZE: number;
    REVIEWER_SCORE_THRESHOLD: number;
};

type FileProps = {
    INPUT_DATASET_REPO: string;
    INPUT_DATASET_FILE_NAME: string;
};

const schema = yup.object().shape({
    file: yup.object({
        INPUT_DATASET_REPO: yup.string().required('Dataset Repository is required'),
        INPUT_DATASET_FILE_NAME: yup.string().required('Dataset File Name is required')
    }),
    global: yup.object({
        api_url: yup.string().required('Cluster Selection is required'),
        deployment_name: yup.string().required('Deployment Name is required'),
        vllm_reviewer_replica: yup.number().when('global.enable_reviewer', (enable_reviewer, schema) => 
            enable_reviewer ? schema.required('Reviewer Model HuggingFace ID is required') : schema.notRequired()
        ),
        vllm_orbiter_replica: yup.number().required('VLLM Orbiter Replica is required').positive().integer().typeError('VLLM Orbiter Replica should be a number'),
        hf_token: yup.string().required('HuggingFace Token is required'),
        orbiter_replica: yup.number().required('Orbiter Replica is required').positive().integer().typeError('Orbiter Replica should be a number'),
        reviewer_replica: yup.number().when('global.enable_reviewer', (enable_reviewer, schema) => 
            enable_reviewer ? schema.required('Reviewer Model HuggingFace ID is required') : schema.notRequired()
        ),
        namespace: yup.string().required('Namespace is required'),
        enable_toleration: yup.boolean().default(false),
        multiple_gpu_per_pod: yup.boolean().default(false),
        number_of_gpu: yup.number().required('Number of GPU is required').positive().integer().typeError('Number of GPU should be a number'),
        enable_reviewer: yup.boolean().default(true),
    }),
    promptLab: yup.object({
        vllm_orbiter_args: yup.object({
            maxLength: yup.number().required('VLLM Orbiter Max Model Length is required').positive().integer().typeError('VLLM Orbiter Max Model Length should be a number'),
            gpuMemoryUtilization: yup.number().required('VLLM Orbiter GPU Memory Utilization is required').positive().typeError('VLLM Orbiter GPU Memory Utilization should be a number'),
        }),
        PROMPT_LAB_MODEL_HF_ID: yup.string().required('Prompt Lab Model HuggingFace ID is required').default('meta-llama/Llama-3.1-8B-Instruct'),
        PROMPT_LAB_BATCH_SIZE: yup.number().required('Orbiter Batch Size is required').positive().integer().typeError('Orbiter Batch Size should be a number'),
        QUEUE_TARGET_SIZE: yup.number().required('Queue Target Size is required').positive().integer().typeError('Queue Target Size should be a number'),
        TEMPLATE_PROJECT_CONTEXT: yup.string(),
        MAX_RETRY: yup.number().required('Max Retries is required').positive().integer().typeError('Max Retries should be a number'),
        TEMPLATE_AGENT: yup.string().required('Template Agent is required').default('TAG'),
        PROMPT_LAB_MAX_GENERATION_LENGTH: yup.number().required('Max Generation Length is required').positive().integer().typeError('Max Generation Length should be a number'),
        PROMPT_LAB_MAX_CONTEXT_LENGTH: yup.number().required('Max Context Length is required').positive().integer().typeError('Max Context Length should be a number'),
        PROJECT_REPO: yup.string(),
        PROJECT_ID: yup.string(),
        TEMPLATE_TYPE: yup.string().required('Template Type is required'),
        TEMPLATE_NAME: yup.string(),
        OUTPUT_DATASET_REPO: yup.string().required('Output Dataset Repository is required'),
        OUTPUT_DATASET_FILE_NAME: yup.string().required('Output Dataset Filename is required')
    }),
    reviewer: yup.object({
        vllm_reviewer_args: yup.object({
            maxLength: yup.number().when('global.enable_reviewer', (enable_reviewer, schema) => 
                enable_reviewer ? schema.required('VLLM Reviewer Max Model Length is required').positive().integer().typeError('VLLM Reviewer Max Model Length should be a number') : schema.notRequired()
            ),
            gpuMemoryUtilization: yup.number().when('global.enable_reviewer', (enable_reviewer, schema) => 
                enable_reviewer ? schema.required('VLLM Reviewer GPU Memory Utilization is required').positive().typeError('VLLM Reviewer GPU Memory Utilization should be a number') : schema.notRequired()
            ),
        }),
        REVIEWER_MODEL_HF_ID: yup.string().when('global.enable_reviewer', (enable_reviewer, schema) => 
            enable_reviewer ? schema.required('Reviewer Model HuggingFace ID is required') : schema.notRequired()
        ),
        REVIEWER_MAX_GENERATION_LENGTH: yup.number().when('global.enable_reviewer', (enable_reviewer, schema) => 
            enable_reviewer ? schema.required('Reviewer Max Generation Length is required').positive().integer().typeError('Reviewer Max Generation Length should be a number') : schema.notRequired()
        ),
        REVIEWER_MAX_CONTEXT_LENGTH: yup.number().when('global.enable_reviewer', (enable_reviewer, schema) => 
            enable_reviewer ? schema.required('Reviewer Max Context Length is required').positive().integer().typeError('Reviewer Max Context Length should be a number') : schema.notRequired()
        ),
        REVIEWER_BATCH_SIZE: yup.number().when('global.enable_reviewer', (enable_reviewer, schema) => 
            enable_reviewer ? schema.required('Reviewer Batch Size is required').positive().integer().typeError('Reviewer Batch Size should be a number') : schema.notRequired()
        ),
        REVIEWER_SCORE_THRESHOLD: yup.number().when('global.enable_reviewer', (enable_reviewer, schema) => 
            enable_reviewer ? schema.required('Reviewer Score Threshold is required').positive().typeError('Reviewer Score Threshold should be a number') : schema.notRequired()
        ),
    }),
});

type CreateHelmJsonProps = {
    onSubmit: SubmitHandler<any>;
    isLoading: boolean;
};

const CreateHelmJson: React.FC<CreateHelmJsonProps> = ({ onSubmit, isLoading }) => {
    const [activeStep, setActiveStep] = useState(0);
    const [isFormTabValid, setIsFormTabValid] = useState(false);
    const [isGlobalTabValid, setIsGlobalTabValid] = useState(false);
    const [isPromptLabTabValid, setIsPromptLabTabValid] = useState(false);
    const [isReviewerTabValid, setIsReviewerTabValid] = useState(false);
    const [isReviewerEnabled, setIsReviewerEnabled] = useState(true);

    const defaultValues = {
        file: {
            INPUT_DATASET_REPO: '',
            INPUT_DATASET_FILE_NAME: '',
        },
        global: {
            api_url: 'Preproduction Cluster',
            deployment_name: 'dpr',
            vllm_reviewer_replica: 1,
            vllm_orbiter_replica: 1,
            hf_token: '',
            orbiter_replica: 1,
            reviewer_replica: 1,
            namespace: '',
            enable_toleration: false,
            multiple_gpu_per_pod: false,
            number_of_gpu: 1,
            enable_reviewer: true,
        },
        promptLab: {
            vllm_orbiter_args: {
                maxLength: 16000,
                gpuMemoryUtilization: 0.88,
            },
            PROMPT_LAB_MODEL_HF_ID: 'Qwen/Qwen2.5-Coder-1.5B-Instruct',
            PROMPT_LAB_BATCH_SIZE: 8,
            QUEUE_TARGET_SIZE: 16,
            TEMPLATE_PROJECT_CONTEXT: '',
            MAX_RETRY: 3,
            TEMPLATE_AGENT: 'TAG',
            PROMPT_LAB_MAX_GENERATION_LENGTH: 2048,
            PROMPT_LAB_MAX_CONTEXT_LENGTH: 16000,
            PROJECT_REPO: '',
            PROJECT_ID: '',
            TEMPLATE_TYPE: 'go',
            TEMPLATE_NAME: '',
            OUTPUT_DATASET_REPO: '',
            OUTPUT_DATASET_FILE_NAME: '',
        },
        reviewer: {
            vllm_reviewer_args: {
                maxLength: 16000,
                gpuMemoryUtilization: 0.88,
            },
            REVIEWER_MODEL_HF_ID: 'Qwen/Qwen2.5-Coder-1.5B-Instruct',
            REVIEWER_MAX_GENERATION_LENGTH: 16000,
            REVIEWER_MAX_CONTEXT_LENGTH: 2048,
            REVIEWER_BATCH_SIZE: 8,
            REVIEWER_SCORE_THRESHOLD: 75,
        },
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

    const requiredFileFields = getRequiredFields(schema.fields.file as yup.ObjectSchema<any>);
    const requiredGlobalFields = getRequiredFields(schema.fields.global as yup.ObjectSchema<any>);
    const requiredPromptLabFields = getRequiredFields(schema.fields.promptLab as yup.ObjectSchema<any>);
    const requiredReviewerFields = getRequiredFields(schema.fields.reviewer as yup.ObjectSchema<any>);

    const watchedFileValues = watch('file') || {} as FileProps;  
    const watchedGlobalValues = watch('global') || {} as GlobalProps;
    const watchedOrbitalValues = watch('promptLab') || {} as PromptLabProps;
    const watchedReviewerValues = watch('reviewer') || {} as ReviewerProps;

    useEffect(() => {
        setIsFormTabValid(checkTabValidity(watchedFileValues, requiredFileFields));

        if (watchedFileValues.INPUT_DATASET_REPO) {
            setValue('promptLab.OUTPUT_DATASET_REPO', watchedFileValues.INPUT_DATASET_REPO);
        }

        if (watchedFileValues.INPUT_DATASET_FILE_NAME) {
            const inputFileName = watchedFileValues.INPUT_DATASET_FILE_NAME;
            const outputFileName = inputFileName.endsWith('.json') ? inputFileName.replace('.json', '_output') : `${inputFileName}_output`;
            setValue('promptLab.OUTPUT_DATASET_FILE_NAME', outputFileName);
        }
    }, [{...watchedFileValues}]);

    useEffect(() => {
        setIsGlobalTabValid(checkTabValidity(watchedGlobalValues, requiredGlobalFields));
        setIsReviewerEnabled(watchedGlobalValues.enable_reviewer);
    }, [{...watchedGlobalValues}]);

    useEffect(() => {
        setIsPromptLabTabValid(checkTabValidity(watchedOrbitalValues, requiredPromptLabFields));
    }, [{...watchedOrbitalValues}]);

    useEffect(() => {
        setIsReviewerTabValid(checkTabValidity(watchedReviewerValues, requiredReviewerFields));
    }, [{...watchedReviewerValues}]);


    const handleNextClick = () => {
        setActiveStep(activeStep + 1);
    };

    const handleBackClick = () => {
      if (activeStep > 0) {
        setActiveStep((prev) => prev - 1);
      }
    };

    // this will be replaced with calling the db for the parser results
    const mockRepoOptions = ['oodeh/eco-gotest-testing', 'mcarmi/testing_dpr'];
    const mockFileOptions = ['eco-gotests_TAG_100_test_100_function.json', 'mysmallfile.json'];
    const ClusterOptions = ['Preproduction Cluster', 'Production Cluster']

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
                            <FormDropdown name="file.INPUT_DATASET_REPO" label="Choose Dataset Repository" control={control} errors={errors} options={mockRepoOptions}/>
                            <FormDropdown name="file.INPUT_DATASET_FILE_NAME" label="Choose Dataset File Name" control={control} errors={errors} options={mockFileOptions}/>
                            <div className="form-bottom-button">
                                <Button type="button" variant="contained" className="end-button" onClick={handleNextClick} disabled={!isFormTabValid}>
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
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '16px' }}>
                            <FormDropdown name="global.api_url" label="Cluster Selection" control={control} errors={errors} options={ClusterOptions}/>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 0.3fr 0.3fr', gap: '16px' }}>
                            <FormField name="global.deployment_name" label="Deployment Name" control={control} errors={errors} /> 
                            <FormField name="global.namespace" label="Namespace" control={control} errors={errors} />
                            <FormField name="global.vllm_orbiter_replica" label="VLLM Orbiter Replica" control={control} errors={errors}/>
                            <FormField name="global.orbiter_replica" label="Orbiter Replica" control={control} errors={errors} />
                        </div>
                        <FormField name="global.hf_token" label="HuggingFace Token" control={control} errors={errors} />
                        <div style={{ display: 'grid', gridTemplateColumns: '0.2fr 0.2fr 1fr', gap: '16px' }}>
                            <div style={{ alignSelf: 'center' }}>
                                <FormCheckbox name="global.enable_toleration" label="Enable Toleration" control={control} errors={errors} />
                            </div>                        
                            <div style={{ alignSelf: 'center' }}>
                                <FormCheckbox name="global.multiple_gpu_per_pod" label="Multiple GPU Per Pod" control={control} errors={errors} />
                            </div>
                            <FormField name="global.number_of_gpu" label="Number of GPU" control={control} errors={errors}/>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '0.3fr 1fr 1fr', gap: '16px' }}>
                            <div style={{ alignSelf: 'center' }}>
                                <FormCheckbox name="global.enable_reviewer" label="Enable Reviewer" control={control} errors={errors} />
                            </div>                            
                            <FormField name="global.vllm_reviewer_replica" label="VLLM Reviewer Replica" control={control} errors={errors} disabled={!isReviewerEnabled} />
                            <FormField name="global.reviewer_replica" label="Reviewer Replica" control={control} errors={errors} disabled={!isReviewerEnabled} />
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
                Prompt Lab Environment
                </CustomStepLabel>
                <StepContent>
                    <form className="form-section" onSubmit={handleSubmit(onSubmit)}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                            <FormField name="promptLab.OUTPUT_DATASET_REPO" label="Output Dataset Repository" control={control} errors={errors} />
                            <FormField name="promptLab.OUTPUT_DATASET_FILE_NAME" label="Output Dataset Filename" control={control} errors={errors} />
                        </div>
                        <FormField name="promptLab.PROMPT_LAB_MODEL_HF_ID" label="Prompt Lab Model HuggingFace ID" control={control} errors={errors} />
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr 1fr 1fr', gap: '16px' }}>
                            <FormField name="promptLab.PROMPT_LAB_BATCH_SIZE" label="Orbiter Batch Size" control={control} errors={errors} />
                            <FormField name="promptLab.QUEUE_TARGET_SIZE" label="Queue Target Size" control={control} errors={errors} />
                            <FormField name="promptLab.PROMPT_LAB_MAX_GENERATION_LENGTH" label="Max Generation Length" control={control} errors={errors} />
                            <FormField name="promptLab.PROMPT_LAB_MAX_CONTEXT_LENGTH" label="Max Context Length" control={control} errors={errors} />
                            <FormField name="promptLab.vllm_orbiter_args.maxLength" label="VLLM Max Model Length" control={control} errors={errors} />
                            <FormField name="promptLab.vllm_orbiter_args.gpuMemoryUtilization" label="VLLM GPU Memory Utilization" control={control} errors={errors} />
                            <FormField name="promptLab.MAX_RETRY" label="Maximum Retries" control={control} errors={errors} />
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '16px' }}>
                            <FormField name="promptLab.TEMPLATE_NAME" label="Template Name" control={control} errors={errors} />
                            <FormField name="promptLab.TEMPLATE_TYPE" label="Template Type" control={control} errors={errors} />
                            <FormField name="promptLab.TEMPLATE_AGENT" label="Template Agent" control={control} errors={errors} />
                            <FormField name="promptLab.TEMPLATE_PROJECT_CONTEXT" label="Template Project Context" control={control} errors={errors} />
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                            <FormField name="promptLab.PROJECT_REPO" label="Project Repository" control={control} errors={errors} />
                            <FormField name="promptLab.PROJECT_ID" label="Project ID" control={control} errors={errors} />
                        </div>
                        <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px'}}>
                            <FormButton type="button" text="Back" onClick={handleBackClick} />
                            {isReviewerEnabled ?  
                                <FormButton type="button" text="Next" onClick={handleNextClick} disabled={!isPromptLabTabValid} /> :
                                <FormButton type="submit" text="Install" disabled={!isPromptLabTabValid} />
                            }
                        </div>
                    </form>
                </StepContent>
            </Step>
            {isReviewerEnabled && 
            <Step>
                <CustomStepLabel StepIconComponent={(props) => <CustomStepIcon {...props} />}>
                    Reviewer Environment
                </CustomStepLabel>
                <StepContent>
                    <form className="form-section" onSubmit={handleSubmit(onSubmit)}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '16px' }}>
                            <FormField name="reviewer.REVIEWER_MAX_GENERATION_LENGTH" label="Reviewer Max Generation Length" control={control} errors={errors} />
                            <FormField name="reviewer.REVIEWER_MAX_CONTEXT_LENGTH" label="Reviewer Max Context Length" control={control} errors={errors} />
                            <FormField name="reviewer.vllm_reviewer_args.maxLength" label="VLLM Reviewer Max Model Length" control={control} errors={errors} />
                            <FormField name="reviewer.vllm_reviewer_args.gpuMemoryUtilization" label="VLLM Reviewer GPU Memory Utilization" control={control} errors={errors} />
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        <FormField name="reviewer.REVIEWER_BATCH_SIZE" label="Reviewer Batch Size" control={control} errors={errors} />
                        <FormField name="reviewer.REVIEWER_SCORE_THRESHOLD" label="Reviewer Score Threshold" control={control} errors={errors} />
                        </div>
                        <FormField name="reviewer.REVIEWER_MODEL_HF_ID" label="Reviewer Model HuggingFace ID" control={control} errors={errors} />
                        <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px'}}>
                            <FormButton type="button" text="Back" onClick={handleBackClick} />
                            <FormButton type="submit" text="Install" disabled={!isReviewerTabValid} />
                        </div>
                    </form>
                </StepContent>
            </Step>}
        </Stepper>
      </Box>)
    }
      </>
    );
};

export default CreateHelmJson;