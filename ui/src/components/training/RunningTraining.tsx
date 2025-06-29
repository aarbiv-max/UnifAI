import React, { useEffect, useState } from 'react';
import StatusTimeline from '../shared/StatusStepper';
import { RestartAlt, CloudDownload, Code, UploadFile, CheckCircle, Folder } from '@mui/icons-material';
import { Box, CircularProgress, Typography } from '@mui/material';
import CancelIcon from '@mui/icons-material/Cancel';
import { getRunningDeployment, trainingUninstall } from '../../http/training';
import { ConfigModal } from '../shared/ConfigModal';
import moment from 'moment';
import { ActionModal } from '../shared/ActionModal';


const STATUS_VALUES = {
  INITIALIZING: 'initializing',
  PREPARING: 'preparing',
  TRAINING: 'training',
  UPDATING: 'updating',
  UPLOADING: 'uploading to Hugging Face',
  DONE: 'done',
};

const statuses = [
  { label: 'INITIALIZING POD', value: STATUS_VALUES.INITIALIZING, icon: <RestartAlt /> },
  { label: 'PREPARING FILES', value: STATUS_VALUES.PREPARING, icon: <CloudDownload /> },
  { label: 'TRAINING SELECTED FILES', value: STATUS_VALUES.TRAINING, icon: <Code /> },
  { label: 'UPDATING CARD FILE', value: STATUS_VALUES.UPDATING, icon: <Folder /> },
  { label: 'EXPORT TO HUGGING FACE', value: STATUS_VALUES.UPLOADING, icon: <UploadFile /> },
  { label: 'DONE', value: STATUS_VALUES.DONE, icon: <CheckCircle /> },
];

type ModelEntry = {
  id: string;
  name: string;
  config: object;
  startTime: any;
};

const RunningTraining: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [model, setModel] = useState<ModelEntry>({id: '', name: '', config: {}, startTime: ''});
  
  useEffect(() => {
    const getRunningTraining = async () => {
      setLoading(true);
      const response = await getRunningDeployment();
      setModel(response);
      setLoading(false)
    }

    getRunningTraining();
  }, [])

   const handleUninstallConfirm = async () => {
       try {
         await trainingUninstall(model.id, "UNINSTALLED");
         const response = await getRunningDeployment();
         setModel(response);
       } catch (error) {
         console.error('Error uninstalling:', error);
       }
     };
  

  return (
    <>
    {loading && 
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <CircularProgress sx={{ color: "red" }} />
      </div>}
    {!loading && (model.id ? 
    (<Box sx={{marginTop: '30px'}}>
      <Box sx={{ display: 'flex', flexDirection: 'row', gap: 2, p: 2, alignItems: 'center', justifyContent: 'center' }}>
            <Box sx={{ width: '50%', bgcolor: 'white', boxShadow: 3, borderRadius: 2, p: 2 }}>
        <Typography><b>Training Name:</b> {model.name}</Typography>
        <Typography><b>Training Start Time:</b> {moment(model.startTime).format("MMM DD, YYYY [at] hh:mm A")}</Typography>
         <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', marginTop: '10px' }}>
         <ConfigModal config={model.config} />
          <ActionModal datasetDetails={model} handleConfirm={handleUninstallConfirm} icon={CancelIcon} title={"Trigger uninstall"} disabledCondition={false} confirmationText="Are you sure you want to uninstall?" loaderText="Uninstalling..." />
        
          </div>
        </Box>
      </Box>
      {model.id && 
        <StatusTimeline id={model.id} apiFetch={'/api/training/getStatus'} statuses={statuses} statusValues={STATUS_VALUES}/>}
    </Box>) :
  (
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'black', padding: '50px', borderRadius: '8px', textAlign: 'center' }}>
      <Typography>No training is currently in progress</Typography>
    </Box>)
    )}
    </>
  );
};

export default RunningTraining;
