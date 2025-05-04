import React, { useEffect, useState } from 'react';
import { Box, Button, IconButton, Modal, Tooltip, Typography } from '@mui/material';
import { SubmitHandler, useForm, } from 'react-hook-form';
import { FormFileUploadHelm } from '../shared/FormFields';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { LoadingOverlay } from '../shared/LoadingOverlay';

const exampleJson = `{
    global: {
        api_url: "https://api.stc-ai-e1-pp.imap.p1.openshiftapps.com:6443", // for prod: "https://api.stc-ai-e1-prod.rtc9.p1.openshiftapps.com:6443"
        deployment_name: "example",
        namespace: "tag-ai--mcarmi-nb",
        enable_toleration: false,
        multiple_gpu_per_pod: false,
        number_of_gpu: 1,
        vllm_orbiter_replica: 1,
        enable_reviewer: false,
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


interface HelmJsonProps {
    onSubmit: SubmitHandler<any>;
    isLoading: boolean;
}

const UploadHelmJson: React.FC<HelmJsonProps> = ({ onSubmit, isLoading }) => {
    const [isModalOpen, setModalOpen] = useState(false);
    const [jsonDisplay, setJsonDisplay] = useState<string | null>(null);

    const { control, handleSubmit, setValue, formState: { errors }, reset } = useForm({
        defaultValues: {jsonFile: {}},
    });

    useEffect(() => {
        setJsonDisplay(null);
    }, []);

    const handleFileUpload = (files: FileList | null) => {
        if (files && files.length > 0) {
            const file = files[0]; 
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const jsonData = JSON.parse(e.target?.result as string);
                    setJsonDisplay(JSON.stringify(jsonData, null, 2)); 
                    setValue('jsonFile', jsonData);
                } catch (error) {
                    console.error('Invalid JSON file:', error);
                }
            };
            reader.readAsText(file);
        }
    };

    return (
        <>
        {isLoading ?
        (<LoadingOverlay text="Helm installation has been triggered." />) :
        (<Box className="form-container">
            <form className="form-section" onSubmit={handleSubmit(onSubmit)}>
            <Box display="flex" alignItems="center" mb={1}>
                <Typography variant="h6" component="label">
                    Select a valid JSON file
                </Typography>
                <Tooltip title="Click to see an example JSON">
                    <IconButton size="small" onClick={() => setModalOpen(true)}>
                        <InfoOutlinedIcon fontSize="small" />
                    </IconButton>
                </Tooltip>
            </Box>
            <FormFileUploadHelm
                name="jsonFile"
                label=""
                control={control}
                errors={errors}
                onFileUpload={handleFileUpload}
                accept="application/json,.json"
            />
                
                {jsonDisplay && 
                    <SyntaxHighlighter className="code-visualizer" language="json" style={atomOneDark} >
                        {jsonDisplay}
                    </SyntaxHighlighter>
                }
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', marginTop: '10px' }}>
                    <Button type="submit" variant="contained" className="end-button" disabled={false}>
                        Install
                    </Button>
                </div>
            </form>
        </Box>)}

        <Modal open={isModalOpen} onClose={() => setModalOpen(false)}>
            <Box sx={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '80%',
                maxHeight: '80vh',
                overflowY: 'auto',
                bgcolor: 'background.paper',
                borderRadius: 2,
                boxShadow: 24,
                p: 3,
            }}>
                <Typography variant="h6" gutterBottom>
                    Example JSON
                </Typography>
                <SyntaxHighlighter language="json" style={atomOneDark}>
                    {exampleJson}
                </SyntaxHighlighter>
                <Box display="flex" justifyContent="flex-end" mt={2}>
                    <Button variant="contained" onClick={() => setModalOpen(false)}>
                        Close
                    </Button>
                </Box>
            </Box>
        </Modal>

        </>
    );
};

export default UploadHelmJson;