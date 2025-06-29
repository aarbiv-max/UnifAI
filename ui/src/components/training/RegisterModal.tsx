import React, { useEffect, useState } from 'react';
import {MenuItem, Button, Box, Modal, Typography, TextField} from '@mui/material';
import axiosLLM from '../../http/axiosLLMConfig';
import { getTrainedModels, registeredModel } from '../../http/training';
import { ModelEntry } from '../types/constants';

type RegisterModalProps = {
  open: boolean;
  model: ModelEntry;
  setModels: React.Dispatch<React.SetStateAction<ModelEntry[]>>;
  setRegisteringModel: ((RegisterModalProps: ModelEntry | null) => void);
};

export const RegisterModal: React.FC<RegisterModalProps> = ({open, model, setModels, setRegisteringModel}) => {
  const [epochOptions, setEpochOptions] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [epoch, setEpoch] = useState('');
  const [checkpoint, setCheckpoint] = useState('');
  const [baseCheckpoint, setBaseCheckpoint] = useState('')
  const finetuneSteps = model.finetuneSteps;
  const fileList = model.modelFileList;

  useEffect(() => {
    const getEpochOptions = () => {
      const epochCount = parseInt(finetuneSteps["epochs"] || '0', 10);
      const options = Array.from({ length: epochCount }, (_, i) => String(i + 1));
      setEpochOptions(options);
    };


    const getBaseCheckpoint = () => {
      const checkpointSet = new Set<number>();

      fileList.forEach((file: string) => {
        const match = file.match(/^checkpoint-(\d+)\//);
        if (match) {
          checkpointSet.add(Number(match[1]));
        }
        const sortedCheckpointSet = Array.from(checkpointSet).sort((a, b) => Number(a) - Number(b));
        const minCheckpoint = String(sortedCheckpointSet[0]);
        setBaseCheckpoint(minCheckpoint);
      });


    };

    getEpochOptions();
    getBaseCheckpoint();
  }
 , []);


  useEffect(() => {
   const getCheckpointByEpoch = () => {    
    const CheckpointByEpoch = Number(baseCheckpoint) * Number(epoch);
    setCheckpoint(String(CheckpointByEpoch));
   };

   if (epoch) {
     getCheckpointByEpoch();
   }

  },[epoch]);  


  const handleRegister = async () => {
    try {
      setLoading(true);
      const res = await axiosLLM.post('/api/backend/registerAdapter', {repoId: model.repoPath, epoch: Number(epoch), checkpointStep: Number(checkpoint)});
      if (res.status == 200) {
        await registeredModel(model.id);
        setLoading(false);
        setEpoch('');
        setCheckpoint('');
        setRegisteringModel(null);
        const models = await getTrainedModels();
        setModels(models);
      } else {
        throw new Error('Failed to register model');
      }
    } catch (error) {
      console.error('Registration failed:', error);
    }
  };

  return (
    <Modal
      open={open}
      onClose={() => setRegisteringModel(null)}
      
    >
      <Box
        sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '30%',
          bgcolor: 'background.paper',
          p: 3,
          boxShadow: 24,
          borderRadius: 2,
        }}
      >
        <Typography variant="h6" sx={{ mb: 2 }}>
          Register Model
        </Typography>

        <TextField
          label="Model Repository"
          margin="dense"
          fullWidth
          value={model.huggingfaceUrl}
          disabled
        />

        <TextField
          select
          label="Epoch"
          margin="dense"
          fullWidth
          value={epoch}
          onChange={(e) => setEpoch(e.target.value)}
          sx={{ mt: 2 }}
        >
          {epochOptions.map((option) => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </TextField>

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3, gap: 1, }}>
          <Button onClick={() => setRegisteringModel(null)} sx={{ color: 'red' }}>
            Cancel
          </Button>
          <Button className="end-button"  variant="contained" onClick={handleRegister} disabled={!epoch || !checkpoint}>
            {loading ? "Registering..." : 'Submit'}
          </Button>
        </Box>
      </Box>
    </Modal>

  );
};
