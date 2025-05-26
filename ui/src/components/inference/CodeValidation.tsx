import React, { useState, useEffect } from 'react';
import {
  Box, Dialog, DialogContent, DialogActions, Button, CircularProgress, Typography, Tabs, Tab,
  Tooltip
} from '@mui/material';
import { ExpandMore, ExpandLess } from '@mui/icons-material';
import axiosBE from '../../http/axiosConfig';
import ValidationResponseViewer from './CodeValidationResponseViewer';

import '../../styles.css';
import { SupportedFrameworks } from '../types/constants';

interface CodeValidationModalProps {
  open: boolean;
  onClose: () => void;
  code: string;
  framework: SupportedFrameworks;
  gitReposLink: string[];
  setCode: (code: string) => void;
  llmResponse: string;
  repositoryLocation: string;
  modelType: 'llama' | 'qwen' | null;
  reformatText: (text: string, modelType: 'llama' | 'qwen', enableCodeValidation: boolean) => string;
  regenerateResponse: (contextEnrichment: boolean) => void;
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
  framework,
  gitReposLink
}) => {
  const [validationResponses, setValidationResponses] = useState<Record<string, ValidationResponse>>({});
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<number>(0);
  const [isLLMResponseVisible, setIsLLMResponseVisible] = useState<boolean>(false);

  const activeRepo = gitReposLink[activeTab];

  useEffect(() => {
    if (open && code && activeRepo) {
      validateRepo(activeRepo);
    }
  }, [code, activeRepo, open]);

  const validateRepo = async (repoLink: string) => {
    if (validationResponses[repoLink]) return;
    setIsValidating(true);
    try {
      const response = await axiosBE.post('/api/chat/evaluate', {
        code,
        repositoryLocation,
        framework: framework[repoLink] || '',
        gitRepoLink: repoLink
      });

      const json = typeof response.data.result === 'string'
        ? JSON.parse(response.data.result)
        : response.data.result;

      setValidationResponses(prev => ({ ...prev, [repoLink]: json }));
    } catch (err) {
      console.error('Validation error:', err);
      setValidationResponses(prev => ({
        ...prev,
        [repoLink]: { error: true, message: `Validation failed for ${repoLink}` }
      }));
    } finally {
      setIsValidating(false);
    }
  };

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleClose = () => {
    setCode('');
    setValidationResponses({});
    onClose();
  };

  const handleRegenerate = () => {
    handleClose();
    regenerateResponse(true);
  };

  const toggleLLMResponse = () => {
    setIsLLMResponseVisible(prev => !prev);
  };

  const currentResponse = validationResponses[activeRepo];
  const accuracy = currentResponse?.percentages_accuracy ?? 0;
  const isAccurate = accuracy >= 75;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth PaperProps={{ style: { minHeight: '80vh' } }}>
      <DialogContent>
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tabs value={activeTab} onChange={handleTabChange} variant="scrollable" scrollButtons="auto">
            {gitReposLink.map((link, idx) => (
              <Tooltip key={link} title={link}>
                <Tab
                  label={
                    <span style={{
                      maxWidth: 160,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      display: 'inline-block',
                    }}>
                      {link}
                    </span>
                  }
                  value={idx}
                />
              </Tooltip>
            ))}
          </Tabs>

        </Box>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {isValidating ? (
            <CircularProgress />
          ) : (
            currentResponse && (
              <ValidationResponseViewer
                data={currentResponse}
                accuracy={accuracy}
              />
            )
          )}

          <Box>
            <Typography
              variant="h6"
              onClick={toggleLLMResponse}
              style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}
            >
              LLM Response
              {isLLMResponseVisible ? <ExpandLess sx={{ ml: 1 }} /> : <ExpandMore sx={{ ml: 1 }} />}
            </Typography>

            {isLLMResponseVisible && (
              <div
                style={{ background: '#f9fafb', padding: '1rem', borderRadius: 6 }}
                dangerouslySetInnerHTML={{
                  __html: modelType ? reformatText(llmResponse, modelType, false) : llmResponse
                }}
              />
            )}
          </Box>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} variant="contained" sx={{ mr: 2 }}>Cancel</Button>
        <Button onClick={handleRegenerate} variant="contained" disabled={isValidating || isAccurate}>
          {isValidating ? <CircularProgress size={24} /> : 'Re-Generate Response'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CodeValidationModal;
