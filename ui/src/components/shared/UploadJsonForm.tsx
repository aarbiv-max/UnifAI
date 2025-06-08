import React, { useEffect, useState } from 'react';
import { Box, Button, IconButton, Modal, Tooltip, Typography } from '@mui/material';
import { SubmitHandler, useForm } from 'react-hook-form';
import { FormFileUploadHelm } from './FormFields';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { LoadingOverlay } from './LoadingOverlay';

interface UploadJsonFormProps {
  onSubmit: SubmitHandler<any>;
  isLoading: boolean;
  title?: string;
  exampleJson?: string;
  loadingText?: string;
  jsonValidation?: (data: any) => boolean; // We have an open story to implement this
  buttonLabel?: string;
}

const UploadJsonForm: React.FC<UploadJsonFormProps> = ({onSubmit, isLoading, title = 'Upload JSON File', exampleJson, loadingText = 'Submitting...', jsonValidation, buttonLabel = 'Submit'}) => {
  const [isModalOpen, setModalOpen] = useState(false);
  const [jsonDisplay, setJsonDisplay] = useState<string | null>(null);

  const { control, handleSubmit, setValue, formState: { errors } } = useForm({
    defaultValues: { jsonFile: {} },
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
          if (jsonValidation && !jsonValidation(jsonData)) {
            throw new Error('JSON validation failed.');
          }
          setJsonDisplay(JSON.stringify(jsonData, null, 2));
          setValue('jsonFile', jsonData);
        } catch (error) {
          console.error('Invalid JSON file:', error);
          alert('Invalid JSON: ' + (error as Error).message);
        }
      };
      reader.readAsText(file);
    }
  };

  return (
    <>
      {isLoading ? (
        <LoadingOverlay text={loadingText} />
      ) : (
        <Box className="form-container">
          <form className="form-section" onSubmit={handleSubmit(onSubmit)}>
            <Box display="flex" alignItems="center" mb={1}>
              <Typography variant="h6" component="label">
                {title}
              </Typography>
              {exampleJson && (
                <Tooltip title="Click to see an example JSON">
                  <IconButton size="small" onClick={() => setModalOpen(true)}>
                    <InfoOutlinedIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
            </Box>

            <FormFileUploadHelm name="jsonFile" label="" control={control} errors={errors} onFileUpload={handleFileUpload} accept="application/json,.json"/>

            {jsonDisplay && (
              <SyntaxHighlighter className="code-visualizer" language="json" style={atomOneDark}>
                {jsonDisplay}
              </SyntaxHighlighter>
            )}

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', marginTop: '10px' }}>
                <Button type="submit" variant="contained" className="end-button" disabled={false}>
                    {buttonLabel}
                </Button>
            </div>
          </form>
        </Box>
      )}

      {exampleJson && (
        <Modal open={isModalOpen} onClose={() => setModalOpen(false)}>
          <Box sx={{position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '80%', maxHeight: '80vh', overflowY: 'auto', bgcolor: 'background.paper', borderRadius: 2, boxShadow: 24, p: 3}}>
            <Typography variant="h6" gutterBottom>Example JSON</Typography>
            <SyntaxHighlighter language="json" style={atomOneDark}>
              {exampleJson}
            </SyntaxHighlighter>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', marginTop: '10px' }}>
              <Button variant="contained" className="end-button" onClick={() => setModalOpen(false)}>Close</Button>
            </div>
          </Box>
        </Modal>
      )}
    </>
  );
};

export default UploadJsonForm;
