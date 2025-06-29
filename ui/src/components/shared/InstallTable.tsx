import React, { useState, useEffect } from 'react';
import {
  Box, Modal, LinearProgress, Table, TableBody, TableCell, TableHead, TableRow,
  TableSortLabel, Typography, Tooltip
} from '@mui/material';
import moment from 'moment';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { TableTooltip } from '../shared/TableTooltip';
import ProgressDisplay from '../shared/ProgressDisplay';
import CancelIcon from '@mui/icons-material/Cancel';
import DeleteIcon from '@mui/icons-material/Delete';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import DescriptionIcon from '@mui/icons-material/Description';
import { ActionModal } from './ActionModal';
import { ConfigModal } from './ConfigModal';
import { DatasetColumnKey } from '../types/constants';

const FINISHED_STATUSES = ["DONE", "UNINSTALLED"];

const StatisticsModal = ({ datasetDetails }: { datasetDetails: any }) => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <TableTooltip icon={ShowChartIcon} title="Display more statistics" setOpen={setOpen} />
      <Modal open={open} onClose={() => setOpen(false)}>
        <Box sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', height: '60%', width: '65%', bgcolor: 'background.paper' }}>
          <ProgressDisplay datasetDetails={datasetDetails} />
        </Box>
      </Modal>
    </>
  );
};


type InstallTableProps = {
  deployments: any[];
  handleUninstallConfirm: (dataset: any, setOpen: (open: boolean) => void) => Promise<void>;
  handleRemoveConfirm: (dataset: any, setOpen: (open: boolean) => void) => Promise<void>;
  widthByColumns: any;
  displayNameByColumns: any;
  columns: string[];
};

const InstallTable: React.FC<InstallTableProps> = ({
    deployments, handleUninstallConfirm, handleRemoveConfirm, widthByColumns, displayNameByColumns, columns
}) => {
  const [orderBy, setOrderBy] = useState('Start Time');
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');

  const handleRequestSort = (property: string) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  return (
    <Box className="form-container">
      <Table className="forms-table">
        <TableHead>
          <TableRow>
            {(columns as DatasetColumnKey[]).map((column) => (
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
          {deployments.map((row) => {
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
                  <Tooltip
                    title={<p className="custom-tooltip-text">Passed: {passed}, Failed: {failed}, Remaining: {displayRemaining}</p>}
                    classes={{ tooltip: "custom-tooltip" }}
                  >
                    <Box sx={{ width: "100%", mt: 2 }}>
                      <LinearProgress className="linear-progress-red" variant="determinate" value={progressPercentage} />
                      <Typography variant="caption" textAlign="center" display="block" mt={1}>
                        {`${Math.round(progressPercentage)}%`}
                      </Typography>
                    </Box>
                  </Tooltip>
                </TableCell>
                <TableCell><Box sx={{ display: 'flex', justifyContent: 'center' }}><StatisticsModal datasetDetails={row} /></Box></TableCell>
                <TableCell><Box sx={{ display: 'flex', justifyContent: 'center' }}><ConfigModal config={row.config} /></Box></TableCell>
                <TableCell><Box sx={{ display: 'flex', justifyContent: 'center' }}><ActionModal datasetDetails={row} handleConfirm={handleUninstallConfirm} icon={CancelIcon} title={FINISHED_STATUSES.includes(row.status) ? "Already uninstalled" : "Trigger uninstall"} disabledCondition={FINISHED_STATUSES.includes(row.status)} confirmationText="Are you sure you want to uninstall?" loaderText="Uninstalling..." /></Box></TableCell>
                <TableCell><Box sx={{ display: 'flex', justifyContent: 'center' }}><ActionModal datasetDetails={row} handleConfirm={handleRemoveConfirm} icon={DeleteIcon} title={FINISHED_STATUSES.includes(row.status) ? "Remove from table" : "You can't remove before uninstalling"} disabledCondition={!FINISHED_STATUSES.includes(row.status)} confirmationText="Are you sure you want to remove this deployment?" loaderText="Removing..." /></Box></TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Box>
  );
};

export default InstallTable;
