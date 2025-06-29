import React, { useEffect, useState } from 'react';
import {
  Box, Table, TableBody, TableCell, TableHead, TableRow,
  Typography, Button, Tooltip, TableSortLabel,
} from '@mui/material';
import LinkIcon from '@mui/icons-material/Link';
import CheckIcon from '@mui/icons-material/Check';
import { ConfigModal } from '../shared/ConfigModal';
import { RegisterModal } from './RegisterModal';
import { ModelEntry } from '../types/constants';
import { getTrainedModels } from '../../http/training';


type ColumnKey = 'Training Name' | 'Config' | 'Hugging Face' | 'Register';

const widthByColumns: Record<ColumnKey, string> = {
  'Training Name': '80%',
  'Config': '3%',
  'Hugging Face': '5%',
  'Register': '7%',
};

const displayNameByColumns: Record<ColumnKey, string> = {
  'Training Name': 'Training Name',
  'Config': 'Config',
  'Hugging Face': 'HF',
  'Register': 'Register',
};

const TrainedModelsTable: React.FC = () => {
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [registeringModel, setRegisteringModel] = useState<ModelEntry | null>(null);
  const [loading, setLoading] = useState(false);
  const [orderBy, setOrderBy] = useState<ColumnKey>('Training Name');
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');

  useEffect(() => {
    const fetchModels = async () => {
      setLoading(true);
      try {
        const res = await getTrainedModels();
        setModels(res);
      } catch (error) {
        console.error('Error fetching models:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchModels();
  }, []);

  const handleRequestSort = (property: ColumnKey) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  return (
    <Box className="form-container">
      <Typography variant="h5" sx={{ mb: 2 }}>Trained Models</Typography>
      <Table className="forms-table">
        <TableHead>
          <TableRow>
            {(['Training Name', 'Config', 'Hugging Face', 'Register'] as ColumnKey[]).map((column) => (
              <TableCell key={column} sx={{ borderRight: '1px solid #ddd', width: widthByColumns[column] }}>
                <TableSortLabel
                  active={orderBy === column}
                  direction={orderBy === column ? order : 'asc'}
                  onClick={() => handleRequestSort(column)}
                >
                  {displayNameByColumns[column]}
                </TableSortLabel>
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {loading ? (
            <TableRow>
              <TableCell colSpan={4}>Loading models...</TableCell>
            </TableRow>
          ) : models?.length ? (
            models.map((model) => (
              <TableRow key={model.id}>
                <TableCell>{model.name}</TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                    <ConfigModal config={model.config} />
                  </Box>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                    <Tooltip title="Open Hugging Face Repo">
                      <Button variant="outlined" sx={{ color: "red", borderColor: "red" }} startIcon={<LinkIcon />} href={model.huggingfaceUrl} target="_blank" rel="noopener noreferrer">
                        Repo
                      </Button>
                    </Tooltip>
                  </Box>
                </TableCell>
                <TableCell>
                <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                  {model.registered ? (
                    <Button className="green-disabled-button" variant="outlined" color="success" startIcon={<CheckIcon />} disabled>
                      Registered
                    </Button>
                  ) : (
                    <Button className="end-button" variant="contained" color="success" onClick={() => setRegisteringModel(model)}>
                      Register
                    </Button>
                  )}
                  
                </Box>
              </TableCell>
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={4}>No models found.</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {registeringModel && 
                <RegisterModal
                  open={!!registeringModel}
                  model={registeringModel}
                  setModels={setModels}
                  setRegisteringModel={setRegisteringModel}
                />}
    </Box>
  );
};

export default TrainedModelsTable;
