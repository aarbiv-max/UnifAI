import React, { useEffect, useState } from 'react';
import InstallTable from '../shared/InstallTable';
import { displayedDprDeployments, dprDelete, dprUninstall } from '../../http/dpr';
import { DatasetColumnKey } from '../types/constants';

const widthByColumns: Record<DatasetColumnKey, string> = {
  'Dataset Name': '25%',
  'Start Time': '25%',
  'Progress': '42%',
  'Statistics': '2%',
  'Config': '2%', 
  'Cancel': '2%',
  'Remove': '2%',
};

const displayNameByColumns: Record<DatasetColumnKey, string> = {
  'Dataset Name': 'Dataset Name',
  'Start Time': 'Start Time',
  'Progress': 'Progress',
  'Statistics': '',
  'Config': '', 
  'Cancel': '',
  'Remove': ''
};

const DatasetGenerationTable: React.FC = () => {
  const [datasets, setDatasets] = useState<any[]>([]);

  const fetchListData = async () => {
    try {
      const response = await displayedDprDeployments();
      if (Array.isArray(response)) setDatasets(response);
      else console.error("Expected array but got:", response.data);
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  useEffect(() => {
    fetchListData();
  }, []);

  useEffect(() => {
    if (datasets.length > 0) {
      const intervalId = setInterval(fetchListData, 30000);
      return () => clearInterval(intervalId);
    }
  }, [datasets.length]);

  const handleUninstallConfirm = async (dataset: any, setOpen: (open: boolean) => void) => {
    try {
      await dprUninstall(dataset._id, "UNINSTALLED");
      setOpen(false);
      fetchListData();
    } catch (error) {
      console.error('Error uninstalling:', error);
    }
  };

  const handleRemoveConfirm = async (dataset: any, setOpen: (open: boolean) => void) => {
    try {
      await dprDelete(dataset._id);
      setOpen(false);
      fetchListData();
    } catch (error) {
      console.error('Error deleting:', error);
    }
  };

  return (
    <InstallTable
      deployments={datasets}
      handleUninstallConfirm={handleUninstallConfirm}
      handleRemoveConfirm={handleRemoveConfirm}
      widthByColumns={widthByColumns}
      displayNameByColumns={displayNameByColumns}
      columns={['Dataset Name', 'Start Time', 'Progress', 'Statistics', 'Config', 'Cancel', 'Remove']}
    />
  );
};

export default DatasetGenerationTable;
