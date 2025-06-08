// components/forms/InstallForm.tsx
import React, { useState } from 'react';
import { Box, Button } from '@mui/material';
import SuccessMessage from './SuccessMessage';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { SubmitHandler } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';

type Mode = 'upload' | 'create';

interface InstallFormProps {
  apiFunction: (data: any, mode: Mode) => Promise<any>;
  uploadComponent: React.ComponentType<any>;
  createComponent: React.ComponentType<any>;
  redirectPath?: string;
  exampleJson?: string
}

const InstallForm: React.FC<InstallFormProps> = ({apiFunction, uploadComponent: UploadComponent, createComponent: CreateComponent, redirectPath = '/', exampleJson = ''}) => {
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [mode, setMode] = useState<Mode>('upload');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const onSubmit: SubmitHandler<any> = async (data, event) => {
    event?.preventDefault();
    try {
      setIsLoading(true);
      const res = await apiFunction(data, mode);
      if (res.status === 'success') {
        setFormSubmitted(true);
        setTimeout(() => navigate(redirectPath), 2000);
      } else {
        toast.warn(res.data || 'An error occurred during the request.');
      }
    } catch (err) {
      console.error(err);
      toast.warn('An unexpected error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  const CurrentForm = mode === 'upload' ? UploadComponent : CreateComponent;

  return (
    <>
      <Box className="mode-selection">
        <Button onClick={() => setMode('upload')} variant={mode === 'upload' ? 'contained' : 'outlined'}>
          Upload JSON
        </Button>
        <Button onClick={() => setMode('create')} variant={mode === 'create' ? 'contained' : 'outlined'}>
          Create JSON
        </Button>
      </Box>

      {!formSubmitted ? (
        <CurrentForm onSubmit={onSubmit} isLoading={isLoading} exampleJson={exampleJson} />
      ) : (
        <SuccessMessage text="Install triggered. Redirecting..." />
      )}

      <ToastContainer position="top-right" autoClose={5000} hideProgressBar />
    </>
  );
};

export default InstallForm;
