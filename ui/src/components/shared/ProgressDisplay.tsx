import React, { useEffect, useState } from 'react';
import { Box, Typography, Divider, CircularProgress } from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import Charts, { ChartData } from '../shared/Charts';

interface ProgressDisplayProps {
  datasetDetails: any;
}

interface PromptLabStats {
  _id: string;
  number_of_elements: number;
  number_of_prompts: number;
  prompts_retried: number;
  prompts_failed: number;
  prompts_pass: number;
  prompts_processed: number;
  exported: string;
}

const ChartContainer: React.FC<{ title: string; type: 'pie' | 'bar' | 'line'; data: ChartData[]; colors: string[]; isHidden?: boolean }> = ({ title, type, data, colors, isHidden }) => {
  return (
    <Box sx={{ width: '50%', bgcolor: 'white', boxShadow: 3, borderRadius: 2, p: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 1 }}>
        {title}
      </Typography>
      <Divider sx={{ mb: 2 }} />
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <Charts type={type} data={data} className="progress-graph-container" colors={colors} isHidden={isHidden} />
      </div>
    </Box>
  );
};

const ProgressTime: React.FC<{ startTime: string | null; endTime?: any }> = ({ startTime, endTime }) => {
  const [elapsedTime, setElapsedTime] = useState<number | string>('Calculating...');
  useEffect(() => {
    if (!startTime) return;
    const start = new Date(startTime).getTime();

    if (endTime) {
      // If endTime exists, calculate the fixed elapsed time and stop here
      const end = new Date(endTime.$date).getTime();
      setElapsedTime(Math.floor((end - start) / 1000));
      return;
    }

    const interval = setInterval(() => {
      const diff = Math.floor((new Date().getTime() - start) / 1000);
      setElapsedTime(diff > 0 ? diff : 'Calculating...');
    }, 1000);

    return () => clearInterval(interval);
  }, [startTime, endTime]); 

  if (!startTime) return null;

  const formatTime = (elapsed: number | string) => {
    if (typeof elapsed === 'string') return elapsed;

    const days = Math.floor(elapsed / (3600 * 24));
    const hours = Math.floor((elapsed % (3600 * 24)) / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;

    let timeString = '';
    if (days > 0) timeString += `${days} day${days > 1 ? 's' : ''}, `;
    if (hours > 0 || days > 0) timeString += `${hours} hour${hours > 1 ? 's' : ''}, `;
    if (minutes > 0 || hours > 0 || days > 0) timeString += `${minutes} minute${minutes > 1 ? 's' : ''}, `;
    timeString += `${String(seconds).padStart(2, '0')} second${seconds > 1 ? 's' : ''}`;

    return timeString;
  };

  return (
    <Box sx={{ width: '80%', bgcolor: 'white', boxShadow: 3, borderRadius: 2, p: 2, marginTop: '30px' }}>
      <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 1 }}>
        Total Running Time
      </Typography>
      <Divider sx={{ mb: 2 }} />
      <Typography variant="subtitle1" align="center" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <AccessTimeIcon sx={{ color: '#9fb0b9' }} />
        {formatTime(elapsedTime)}
      </Typography>
    </Box>
  );
};


const ChartsStatistics: React.FC<{ promptLabData: PromptLabStats | null }> = ({ promptLabData }) => {
  const remainingPrompts = promptLabData ? promptLabData.number_of_prompts - promptLabData.prompts_processed : 0;

  const passFailRemainColors = ['#54bc89', '#e75d57', '#99b4be'];
  const counterColors = ['#ffd028', '#54bc89', '#e75d57', '#0386a9'];

  const counterData = promptLabData
    ? [
        { label: 'Processed', value: promptLabData.prompts_processed },
        { label: 'Passed', value: promptLabData.prompts_pass },
        { label: 'Failed', value: promptLabData.prompts_failed },
        { label: 'Retried', value: promptLabData.prompts_retried },
      ]
    : [];

  const overviewData = promptLabData
    ? [
        { id: 0, label: `PASS (${promptLabData.prompts_pass})`, value: promptLabData.prompts_pass },
        { id: 1, label: `FAIL (${promptLabData.prompts_failed})`, value: promptLabData.prompts_failed },
        { id: 2, label: `REMAINING (${remainingPrompts})`, value: remainingPrompts },
      ]
    : [];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'row', width: '96%', gap: 2, p: 2, bgcolor: 'white', alignItems: 'center', justifyContent: 'center' }}>
      <ChartContainer title="Prompt Lab Counters View" type="bar" data={counterData} colors={counterColors} isHidden={true} />
      <ChartContainer title="Prompt Lab Overview" type="pie" data={overviewData} colors={passFailRemainColors} />
    </Box>
  );
};

const ProgressDisplay: React.FC<ProgressDisplayProps> = ({ datasetDetails }) => {
  const [promptLabData, setPromptLabData] = useState<PromptLabStats | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        let promptLabResponse = datasetDetails?.stats;
        setPromptLabData(promptLabResponse);
      } catch (error) {
        console.error('Error fetching statistics:', error);
      }
    };
    fetchData();
  }, [datasetDetails]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, p: 2, bgcolor: 'white', alignItems: 'center' }}>
        <ProgressTime startTime={datasetDetails.first_deployed} endTime={datasetDetails.finished_running} />
        <ChartsStatistics promptLabData={promptLabData} />
    </Box>
  );
};

export default ProgressDisplay;
