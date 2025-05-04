import React, { useState, useEffect } from 'react';
import { Box, Dialog, DialogTitle, DialogContent, DialogActions, Button, CircularProgress, Typography } from '@mui/material';
import { ExpandMore, ExpandLess } from '@mui/icons-material';
import axiosBE from '../../http/axiosConfig';
import ValidationResponseViewer from './CodeValidationResponseViewer';
import '../../styles.css';

interface CodeValidationModalProps {
  open: boolean;
  onClose: () => void;
  code: string;
  framework: string | null;
  setCode: (code: string) => void;
  llmResponse: string;
  repositoryLocation: string;
  modelType: 'llama' | 'qwen' | null;
  reformatText: (text: string, modelType: 'llama' | 'qwen', enableCodeValidation: boolean) => string;
  regenerateResponse: (contextEnrichment: boolean) => void
}

interface ValidationResponse {
  is_valid?: boolean;
  percentages_accuracy?: number;
  summary?: string;
  verification_details?: any;
  status?: string;

  error?: boolean;
  message?: string;
}

const CodeValidationModal: React.FC<CodeValidationModalProps> = ({
  open,
  onClose,
  code,
  setCode,
  llmResponse,
  repositoryLocation,
  modelType,
  reformatText,
  regenerateResponse,
  framework
}) => {
  const [validationResponse, setValidationResponse] = useState<ValidationResponse | null>(null);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [isLLMResponseVisible, setIsLLMResponseVisible] = useState<boolean>(false);

  useEffect(() => {
    if (code) {
      handleValidate();
    }
  }, [code]);

  const handleValidate = async () => {
    setIsValidating(true);
    try {
      const response = await axiosBE.post('/api/chat/evaluate', {
        code,
        repositoryLocation,
        framework
      });
      
      // Ensure we're working with parsed JSON
      const jsonResponse = typeof response.data.result === 'string' 
        ? JSON.parse(response.data.result) 
        : response.data.result;
        
      setValidationResponse(jsonResponse);
    } catch (error) {
      console.error('Error validating code:', error);
      setValidationResponse({
        error: true,
        message: 'An error occurred during validation.'
      });
    } finally {
      setIsValidating(false);
    }
  };

  const handleCodeChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setCode(event.target.value);
  };

  const handleRegenerate = () => {
    handleClose();
    // Trigger API for regeneration
    regenerateResponse(true)
  };

  const handleClose = () => {
    setCode('');
    setValidationResponse(null);
    onClose();
  };

  const toggleLLMResponse = () => {
    setIsLLMResponseVisible((prev) => !prev);
  };

  const accuracy = validationResponse?.percentages_accuracy ?? 0;
  const isAccurate = accuracy >= 75.00;

  return (
    <Dialog 
      open={open} 
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        style: { 
          minHeight: '80vh',
          padding: '20px'
        }
      }}
    >
      {/* <DialogTitle>Code Validation</DialogTitle> */}
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 2 }}>
          {validationResponse && !isValidating && (
              <Box sx={{ mt: 3 }}>
                <ValidationResponseViewer data={validationResponse} accuracy={accuracy} />
              </Box>
            )}

            <Box>
              <Typography 
                variant="h6" 
                style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                onClick={toggleLLMResponse}
              >
                LLM Response
                {isLLMResponseVisible ? <ExpandLess sx={{ marginLeft: '8px' }} /> : <ExpandMore sx={{ marginLeft: '8px' }} />}
              </Typography>
              
              {isLLMResponseVisible && (
                <div 
                  style={{ 
                    backgroundColor: '#f9fafb',
                    padding: '1rem',
                    borderRadius: '0.375rem'
                  }}
                  dangerouslySetInnerHTML={{ 
                    __html: modelType ? reformatText(llmResponse, modelType, false) : llmResponse 
                  }} 
                />
              )}
            </Box>
          
          {/* <TextField
            label="Paste the generated code for validation"
            multiline
            rows={8}
            value={code}
            onChange={handleCodeChange}
            variant="outlined"
            fullWidth
          /> */}
        </Box>
      </DialogContent>
      <DialogActions>
        <div className="form-bottom-button">
          <Button 
            onClick={handleClose}
            variant="contained"
            className="end-button"
            style={{ marginRight: '10px' }}
          >
            Cancel
          </Button>

          <Button 
            onClick={handleRegenerate}
            disabled={isValidating || isAccurate}
            variant="contained"
            className="end-button"
          >
            {isValidating ? <CircularProgress size={24} /> : 'Re-Generate Response'}
          </Button>
        </div>
      </DialogActions>
    </Dialog>
  );
};

export default CodeValidationModal;