import React, { useState } from 'react';
import { Button, Box } from '@mui/material';
import SuccessMessage from '../shared/SuccessMessage';
import { SubmitHandler } from 'react-hook-form';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import UploadHelmJson from './UploadHelmJson';
import CreateHelmJson from '../inference/CreateHelmJson';
import { useNavigate } from 'react-router-dom';  
import { dprInstall } from '../../http/dpr';

const HelmForm: React.FC = () => {
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [mode, setMode] = useState<'create' | 'upload'>('upload');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate(); 

  const onSubmit: SubmitHandler<any> = async (data, event) => {
    event?.preventDefault(); 
    try {
      setIsLoading(true);
      console.log('Submitting JSON file data:', data);
      const res = await dprInstall(data, mode);
      if (res.status === "success") {
        setFormSubmitted(true);
        console.log('Form submitted successfully:', data);
        setTimeout(() => {
          navigate('/deployed-datasets'); 
        }, 2000); 
      } else {
        toast.warn(res.data || "An error occured while triggering the installation.");
      }
    } catch (error) {
      console.error('Error submitting form:', error);
      toast.warn('An error occurred while submitting.');
    } finally {
      setIsLoading(false);
    }
  };

  const FormComponent = mode === 'upload' ? UploadHelmJson : CreateHelmJson;

  return (
    <>
      <Box className="mode-selection">
        <Button onClick={() => setMode('upload')} variant={mode === 'upload' ? 'contained' : 'outlined'}>
          Upload JSON File
        </Button>
        <Button onClick={() => setMode('create')} variant={mode === 'create' ? 'contained' : 'outlined'}>
          Create JSON File
        </Button>
      </Box>

      {!formSubmitted ? <FormComponent onSubmit={onSubmit} isLoading={isLoading} /> : <SuccessMessage text="Helm install has been triggered, redirecting to dataset table" />}

      <ToastContainer position="top-right" autoClose={5000} hideProgressBar />
    </>
  );
};

export default HelmForm;
