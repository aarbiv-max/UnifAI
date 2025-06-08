import React, { useEffect, useState } from 'react';
import { useForm, SubmitHandler } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import axios from '../../http/axiosConfig';
import { FormData } from '../types/constants'
import { FormField, FormDropdown } from '../shared/FormFields'
import { Alert, Box, Button, CircularProgress, Step, StepContent, Stepper } from '@mui/material'; 
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import python from 'react-syntax-highlighter/dist/esm/languages/hljs/python';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import GitForm from '../git/GitTree';
import '../../styles.css';
import { CustomStepIcon, CustomStepLabel } from '../shared/StepperIcons';
import { fetchExtensions } from '../../http/extensions';
import { startParser } from '../../http/parser';
import { CloudDownload, Code, UploadFile, CheckCircle } from '@mui/icons-material';
import StatusTimeline from '../shared/StatusStepper';

SyntaxHighlighter.registerLanguage('python', python);

const STATUS_VALUES = {
  CLONING: 'cloning',
  PARSING: 'parsing',
  UPLOADING: 'uploading to Hugging Face',
  DONE: 'done',
};

const statuses = [
  { label: 'CLONING GIT FILES', value: STATUS_VALUES.CLONING, icon: <CloudDownload /> },
  { label: 'PARSING SELECTED FILES', value: STATUS_VALUES.PARSING, icon: <Code /> },
  { label: 'EXPORT TO HUGGING FACE', value: STATUS_VALUES.UPLOADING, icon: <UploadFile /> },
  { label: 'DONE', value: STATUS_VALUES.DONE, icon: <CheckCircle /> },
];

const gitUrlPattern = /^https:\/\/([\w.-]+)\/([\w.-]+)\/([\w.-]+)(\.git)?$/;

const schema = yup.object().shape({
    projectName: yup.string().required('Project Name is required'),
    trainingName: yup.string().required('Training Name is required'),
    gitUrl: yup.string().required('Git Repo Url is required'),
    gitCredentialKey: yup.string().required('Git Credential Key is required'),
    gitBranchName: yup.string().required('Git Branch Name is required'),
    gitFolderPath: yup.string(),
    // gitFolderPath: yup.string().required('Git Path to Expand From is required'),
    testsCodeFramework:  yup.string().required("Tests Code Language is required"),
    numberOfTests: yup.number().required('Number of Tests is required').positive().integer(),
    datasetGradingUpgrade: yup.boolean(),
    // datasetGradingUpgrade: yup.boolean().required('Dataset Grading Upgrade is required'),
});

interface TestItem {
  file: string;
  in_db: string;
}

const ProjectForm: React.FC = () => {
    const [activeStep, setActiveStep] = useState(0);
    const [uploadedCode, setUploadedCode] = useState<string | null>(null);
    const [triggerGitFormOpen, setTriggerGitFormOpen] = useState(false);
    const [isFirstTabValid, setIsFirstTabValid] = useState(false);
    const [isSecondTabValid, setIsSecondTabValid] = useState(false);
    const [gitLoading, setGitLoading] = useState(false);
    const [formSubmitted, setFormSubmitted] = useState(false);
    const [frameworks, setFrameworks] = useState<string[]>([]);
    const [extensions, setExtensions] = useState<Record<string, string[]>>({});
    const [availableExtensions, setAvailableExtensions] = useState<string[]>([]);
    const [gitFiles, setGitFiles] = useState<TestItem[]>([]);
    const [errorMessage, setErrorMessage] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [formId, setFormId] = useState(null);

    // Existing state for checked items
    const [checked, setChecked] = useState<string[]>([]);

    const { control, handleSubmit, formState: { errors }, watch, setValue} = useForm<FormData>({
        resolver: yupResolver(schema),
        mode: 'onChange', // This will validate the form on every change,
    });

    const selectedFrameworks = watch("testsCodeFramework", '') 

    const checkFirstTabValidity = (data: Array<string | null>): boolean => {
      const [projectName, trainingName, gitUrl, gitCredentialKey, gitBranchName, testsCodeFramework] = data;
      return (
        !!projectName && !!trainingName && !!gitUrl && !!gitCredentialKey && !!gitBranchName && !!testsCodeFramework
      );
    };

    const watchedFields = watch(['projectName', 'trainingName', 'gitUrl', 'gitCredentialKey', 'gitBranchName', 'testsCodeFramework']);

    useEffect(() => {
      const [projectName, trainingName, gitUrl, gitCredentialKey, gitBranchName, testsCodeFramework] = watchedFields;
      setIsFirstTabValid(checkFirstTabValidity([projectName, trainingName, gitUrl, gitCredentialKey, gitBranchName, testsCodeFramework]));
    }, [watchedFields]);

    useEffect(() => {
      setAvailableExtensions(selectedFrameworks ? extensions[selectedFrameworks] || [] : []);
    }, [selectedFrameworks, extensions]);
    
    
    useEffect(() => {
      const loadExtensions = async () => {
        const data = await fetchExtensions();
        setFrameworks(data.frameworks);
        setExtensions(data.extensions);
      };
  
      loadExtensions();
    }, []);

    // Update the validity of the second tab when the checked items change
    useEffect(() => {
      setIsSecondTabValid(checked.length > 0);
    }, [checked]);


    
    const filterFilesOnly = (selectedPaths: string[]) => {
      return selectedPaths.filter(path => availableExtensions.some(ext => path.endsWith(ext)));
    };

    const onSubmit: SubmitHandler<FormData> = async (data) => {
        try {
          const {projectName, trainingName, gitUrl, gitCredentialKey, gitFolderPath, gitBranchName, testsCodeFramework,
                 numberOfTests, datasetGradingUpgrade} = data;

          const filesPath = filterFilesOnly(checked);

          const insertResponse = await axios.post('/api/forms/insert', {projectName, trainingName, gitUrl, gitCredentialKey, gitFolderPath, gitBranchName, testsCodeFramework,
            numberOfTests, datasetGradingUpgrade, filesPath});

         // Extract the inserted_id
          const insertedId = insertResponse.data.inserted_id;  
          setFormId(insertedId)
          if (!insertedId) {
              console.error("No inserted_id received");
              return;
          }
          await startParser(insertedId);
          setFormSubmitted(true); // Set the state to true upon successful form submission
          console.log('Form submitted successfully:', data);
        } catch (error) {
          console.error('Error submitting form:', error);
        }
      };

    const handleNextClick = async () => {
        if (activeStep === 0) {

          setIsLoading(true);
          const error = await getTestsTree(); 
          setIsLoading(false); 
      
          if (error) {
            return; // Prevent proceeding if an error occurs
          }
              
          setTriggerGitFormOpen(true);
        }

        if (activeStep === 1) {
          setValue('numberOfTests', filterFilesOnly(checked).length);
        }
        
        setActiveStep(activeStep + 1);
    };

    const handleBackClick = () => {
      if (activeStep === 1) { // Reset the checked tests when going back to the first tab
        setChecked([]);
        setValue('numberOfTests', 0);
      }
      
      if (activeStep > 0) {
        setActiveStep((prev) => prev - 1);
      }
    };
    
    const getTestsTree = async () => {
      try {
        const response = await axios.get("/api/git/files", {
          params: {
            gitUrl: watch("gitUrl"),
            gitCredentialKey: watch("gitCredentialKey"),
            gitFolderPath: watch("gitFolderPath"),
            gitBranchName: watch("gitBranchName"),
          },
        });
    
        setGitFiles(response.data.result);
        setErrorMessage("");
        return null; 
    
      } catch (error: any) {
        setErrorMessage(error.message);
        return error.message; 
      }
    };

    return (
      <Box className="form-container">
        <Stepper activeStep={activeStep} orientation="vertical">
          <Step>
            <CustomStepLabel StepIconComponent={(props) => <CustomStepIcon {...props} />}>
              Project Form
            </CustomStepLabel>
            <StepContent>
              <form className="form-section">
                <FormField 
                  name="projectName" 
                  label="Project Name" 
                  control={control} 
                  errors={errors} 
                  tooltip="Enter your project name."
                />
                <FormField 
                  name="trainingName" 
                  label="Training Name" 
                  control={control} 
                  errors={errors} 
                  tooltip="Provide a name for the training process. Example: 'Sentiment Analysis Model Training', 'Customer Support Chatbot Fine-tuning'."
                />
                <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                  <div style={{ width: "50%" }}>
                    <FormField 
                      name="gitUrl" 
                      label="Git Repository URL" 
                      control={control} 
                      errors={errors} 
                      tooltip="Provide the full URL of your Git repository. Example: 'https://github.com/user/repo.git'."
                    />
                  </div>
                  <span style={{ fontSize: "20px", fontWeight: "bold", color: 'gray' }}>/</span>
                  <div style={{ width: "50%" }}>
                    <FormField 
                      name="gitFolderPath" 
                      label="Git Path to Fetch From" 
                      control={control} 
                      errors={errors} 
                      tooltip="Enter the directory path inside the Git repository where the required files are stored. Example: 'src/models', 'scripts/training'."
                    />
                  </div>
                </div>
                <FormField 
                  name="gitCredentialKey" 
                  label="Git Credential Key" 
                  control={control} 
                  errors={errors} 
                  secret={true} 
                  tooltip="Enter your Git authentication key (kept confidential). Example: 'ghp_123456abcdef'."
                />
                <FormField 
                  name="gitBranchName" 
                  label="Git Branch Name" 
                  control={control} 
                  errors={errors} 
                  tooltip="Specify the branch to pull code from. Example: 'main', 'develop', 'feature/new-feature'."
                />
                <FormDropdown name="testsCodeFramework" label="Tests Code Framework" control={control} errors={errors} options={frameworks} />
                {errorMessage && (
                  <Alert severity="error">{errorMessage}</Alert>
                )}
                <div className="form-bottom-button">
                  <Button
                    type="button"
                    variant="contained"
                    className="end-button"
                    onClick={handleNextClick}
                    disabled={!isFirstTabValid}
                    style={{ width: '5%' }}
                  >
                     {isLoading ? <CircularProgress size="30px" color="inherit" /> : "Next"}
                  </Button>
                </div>
              </form>
            </StepContent>
          </Step>
          <Step>
            <CustomStepLabel StepIconComponent={(props) => <CustomStepIcon {...props} />}>
              Git Form
            </CustomStepLabel>
            <StepContent>
                <form onSubmit={handleSubmit(onSubmit)}>
                  <div className="form-section">
                    <GitForm projectFormDetails={{
                              gitUrl: watch('gitUrl'),
                              gitCredentialKey: watch('gitCredentialKey'),
                              gitBranchName: watch('gitBranchName'),
                              gitFolderPath: watch('gitFolderPath') || '',
                              testsCodeFramework:  watch("testsCodeFramework") 
                            }} 
                            triggerOpen={triggerGitFormOpen} 
                            checked={checked} 
                            setChecked={setChecked} 
                            loading={gitLoading} 
                            setLoading={setGitLoading} 
                            testsList={gitFiles}
                            availableExtensions={availableExtensions}/>
                      <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px'}}>
                        <Button type="button" variant="contained" className="end-button" onClick={handleBackClick}>
                          Back
                        </Button>
                        <Button type="submit" variant="contained" className="end-button" onClick={handleNextClick} disabled={!isSecondTabValid || gitLoading} style={{ float: 'right',  }}>
                          Create Dataset
                      </Button>
                    </div>
                  </div>
                </form>
            </StepContent>
          </Step>
          <Step>
            <CustomStepLabel StepIconComponent={(props) => <CustomStepIcon {...props} />}>
              Parser Tracker
            </CustomStepLabel>
            <StepContent sx={{height: 400}}>
                <FormField name="numberOfTests" label="Number of Files" type="number" control={control} errors={errors} disabled={true} />
                {uploadedCode && (
                  <SyntaxHighlighter className="code-visualizer" language="python" style={atomOneDark}>
                      {uploadedCode}
                  </SyntaxHighlighter>
                )}
                {formId &&
                  <div style={{padding: "50px 0px 50px 0px"}}>
                      <StatusTimeline id={formId} apiFetch={'/api/forms/status'} statuses={statuses} statusValues={STATUS_VALUES}/>
                  </div>
                }
            </StepContent>
          </Step>
        </Stepper>
      </Box>
    );
};

export default ProjectForm;
