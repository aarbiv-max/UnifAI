import React, { useEffect, useState } from 'react';
import { Box, Modal, LinearProgress, Table, TableBody, TableCell, TableHead, TableRow, TableSortLabel, Typography, Tooltip } from '@mui/material'; 
import DeleteIcon from '@mui/icons-material/Delete';
import CancelIcon from '@mui/icons-material/Cancel';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import DescriptionIcon from '@mui/icons-material/Description';
import '../../styles.css';
import ProgressDisplay from './ProgressDisplay';
import moment from 'moment';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { ConfirmationModal } from '../shared/ConfirmationModal';
import { TableTooltip } from '../shared/TableTooltip';
import { displayedDeployments, dprDelete, dprUninstall, getConfigFile, getStats } from '../../http/dpr';

const FINISHED_STATUSES = ["DONE", "UNINSTALLED"];

type ActionModalProps = {
  datasetDetails: any;
  handleConfirm: (datasetId: string, setOpen: React.Dispatch<React.SetStateAction<boolean>>) => Promise<void>;
  icon: React.ElementType;
  title: string;
  disabledCondition: boolean;
  confirmationText: string;
  loaderText: string;
};

const ActionModal: React.FC<ActionModalProps> = ({ datasetDetails, handleConfirm, icon, title, disabledCondition, confirmationText, loaderText }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
    
  const handleConfirmClick = async () => {
    setLoading(true);
    await handleConfirm(datasetDetails, setOpen);
    setLoading(false);
  };
  
  return (
    <>
      <TableTooltip icon={icon} title={title} setOpen={setOpen} disabled={disabledCondition} />
      <ConfirmationModal text={confirmationText} open={open} onClose={() => setOpen(false)} loading={loading} loaderText={loaderText} handleClick={handleConfirmClick} />
    </>
  );
};

const StatisticsModal = (datasetDetails: any) => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <TableTooltip icon={ShowChartIcon} title="Display more statistics" setOpen={setOpen} />
      <Modal open={open} onClose={() => setOpen(false)} >
        <Box sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', height: '60%', width: '65%', bgcolor: 'background.paper' }}>
          <ProgressDisplay datasetDetails={datasetDetails.datasetDetails} />
        </Box>
      </Modal>
    </>
  );
};

const ConfigModal = ({ datasetId }: { datasetId: string }) => {
  const [open, setOpen] = useState(false);
  const [config, setConfig] = useState<any>(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await getConfigFile(datasetId);
        setConfig(response || {});
      } catch (error) {
        console.error('Error fetching config:', error);
      }
    };

    if (open) {
      fetchConfig();
    }
  }, [open, datasetId]);

  return (
    <>
      <TableTooltip icon={DescriptionIcon} title="Display configuration json file" setOpen={setOpen} />
      <Modal open={open} onClose={() => setOpen(false)}>
        <Box sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', height: '70%', width: '80%', bgcolor: 'background.paper', padding: 3, overflow: 'auto' }}>
          <Typography variant="h6" component="h2" sx={{ mb: 2 }}>
            Dataset Config
          </Typography>
          <SyntaxHighlighter language="json" style={atomOneDark}>
            {JSON.stringify(config, null, 2)}
          </SyntaxHighlighter>
        </Box>
      </Modal>
    </>
  );
};

const DatasetPreparationTable: React.FC = () => {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [orderBy, setOrderBy] = useState('Start Time');
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');

  const fetchListData = async () => {
    try {
      const response = await displayedDeployments();
      if (Array.isArray(response)) {
        setDatasets((prevDatasets) => {return response})
      } else {
        console.error("Expected array but got:", response.data);
      }
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  useEffect(() => {
    fetchListData();
  }, []);

  useEffect(() => {
    if (datasets.length > 0) {
        fetchListData();
        const intervalId = setInterval(fetchListData, 30000);
        return () => clearInterval(intervalId);
    }
  }, [datasets.length]); 

  const handleUninstallConfirm = async (datasetDetails: any, setOpen: ((open: boolean) => void)) => {
    if (datasetDetails) {
      try {
        await dprUninstall(datasetDetails._id, "UNINSTALLED");
        setOpen(false);
        fetchListData();
      } catch (error) {
        console.error('Error deleting prompt:', error);
      }
    }
  };

  const handleRemoveConfirm = async (dataset: any, setOpen: ((open: boolean) => void)) => {
    if (dataset) {
      try {
        await dprDelete(dataset._id);
        setOpen(false);
        fetchListData();
      } catch (error) {
        console.error('Error deleting prompt:', error);
      }
    }
  };

  const handleRequestSort = (property: any) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const widthByColumns = {
    'Dataset Name': '25%',
    'Start Time': '25%',
    'Progress': '42%',
    'Statistics': '2%',
    'Config': '2%', 
    'Cancel': '2%',
    'Remove': '2%'
  };

  const displayNameByColumns = {
    'Dataset Name': 'Dataset Name',
    'Start Time': 'Start Time',
    'Progress': 'Progress',
    'Statistics': '',
    'Config': '', 
    'Cancel': '',
    'Remove': ''
  };

  return (
    <Box className="form-container">
      <Table className="forms-table">
        <TableHead>
          <TableRow>
            {(['Dataset Name', 'Start Time', 'Progress', 'Statistics', 'Config', 'Cancel', 'Remove'] as const).map((column) => (
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
          {datasets?.map((row) => {
            const stats = row.stats || {};

            const passed = stats.prompts_pass || 0;
            const failed = stats.prompts_failed || 0;
            const promptsProcessed = stats.prompts_processed || 0;
            const totalPrompts = stats.number_of_prompts || 0;
            const remaining = totalPrompts - promptsProcessed;

            const progressPercentage = totalPrompts > 0 ? (promptsProcessed / totalPrompts) * 100 : 0;

            const displayRemaining = remaining >= 0 ? remaining : 'TBD';
            return (
              <TableRow key={row._id}>
                <TableCell>{row.name}</TableCell>
                <TableCell>{moment(row.first_deployed).format("MMM DD, YYYY [at] hh:mm A")}</TableCell>
                <TableCell>
                  <Box sx={{ width: '100%', mt: 2 }}>
                    <Tooltip title={<p className="custom-tooltip-text">Passed Prompts: {passed}, Failed Prompts: {failed}, Remaining: {displayRemaining}</p>} classes={{ tooltip: "custom-tooltip" }}>
                      <Box sx={{ width: "100%", mt: 2 }}>
                        <LinearProgress className="linear-progress-red" variant="determinate" value={progressPercentage} />
                        <Typography variant="caption" textAlign="center" display="block" mt={1}>
                          {`${Math.round(progressPercentage)}%`}
                        </Typography>
                      </Box>
                    </Tooltip>
                  </Box>
                </TableCell>
                <TableCell>
                  <Box sx={{display: 'flex', justifyContent: 'center'}}>
                    <StatisticsModal datasetDetails={row} />
                  </Box>
                </TableCell>
                <TableCell>
                  <Box sx={{display: 'flex', justifyContent: 'center'}}>
                    <ConfigModal datasetId={row._id} />
                  </Box>
                </TableCell>
                <TableCell>
                  <Box sx={{display: 'flex', justifyContent: 'center'}}>
                    <ActionModal 
                      datasetDetails={row} 
                      handleConfirm={handleUninstallConfirm} 
                      icon={CancelIcon} 
                      title={FINISHED_STATUSES.includes(row.status) ? "Deployment has already been uninstalled" : "Trigger uninstall of the helm process"} 
                      disabledCondition={FINISHED_STATUSES.includes(row.status)} 
                      confirmationText="Are you sure you want to uninstall?" 
                      loaderText="Uninstalling..." 
                    />
                  </Box>
                </TableCell>
                <TableCell>
                  <Box sx={{display: 'flex', justifyContent: 'center'}}>
                    <ActionModal 
                      datasetDetails={row} 
                      handleConfirm={handleRemoveConfirm} 
                      icon={DeleteIcon} 
                      title={FINISHED_STATUSES.includes(row.status) ? "Remove this process from the table" : "You can't remove this row before the deployment is uninstalled"} 
                      disabledCondition={!FINISHED_STATUSES.includes(row.status)} 
                      confirmationText="Are you sure you want to remove this deployment from the table?" 
                      loaderText="Removing..." 
                    />
                  </Box>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Box>
  );
};

export default DatasetPreparationTable;
