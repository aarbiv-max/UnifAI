import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Tabs, 
  Tab, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow,
  Paper,
  Alert,
  Tooltip,
  Link
} from '@mui/material';
import { CheckCircle, Cancel } from '@mui/icons-material';

interface ValidationDetail {
  args?: any;
  url?: any;
  command?: string;
  matchLevel?: string;
  exists: boolean;
  name: string;
  
}

interface ValidationDetails {
  [key: string]: ValidationDetail[];
}

interface ValidationResponse {
    error?: boolean;
    message?: string;
    is_valid?: boolean;
    summary?: string;
    verification_details?: ValidationDetails;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

interface ValidationTableProps {
  data: ValidationDetail[];
  title: string;
}

const AccuracyIndicator: React.FC<{ accuracy: number }> = ({ accuracy }) => {
  const isAccurate = accuracy >= 75.00;
  
  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      gap: '8px', 
    }}>
      <div style={{
        width: '12px',
        height: '12px',
        borderRadius: '50%',
        backgroundColor: isAccurate ? '#4CAF50' : '#F44336',
        marginLeft: '10px',
        display: 'inline-block',
        verticalAlign: 'middle'
      }} />
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {accuracy}% of the suggested code elements exist in the original repository
      </Typography>
    </div>
  );
};

const ValidationTable: React.FC<ValidationTableProps>  = ({ data, title }) => {
  const isCyCommands = title.toLowerCase().includes('cycommand');

  return (
    <TableContainer component={Paper} elevation={0}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontWeight: 600 }}>Element</TableCell>
            <TableCell align="center" sx={{ fontWeight: 600 }}>Exists</TableCell>
            {isCyCommands && (
              <>
                <TableCell align="center" sx={{ fontWeight: 600 }}>Match Level</TableCell>
                <TableCell align="center" sx={{ fontWeight: 600 }}>Args</TableCell>
                <TableCell align="center" sx={{ fontWeight: 600 }}>Link</TableCell>
              </>
            )}
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((item, index) => (
            <TableRow
              key={`${title}-${index}`}
              sx={{ backgroundColor: index % 2 === 0 ? '#f9fafb' : 'white' }}
            >
              <TableCell>{item.name || item.command}</TableCell>
              <TableCell align="center">
                {item.exists ? (
                  <CheckCircle sx={{ color: '#2e7d32' }} />
                ) : (
                  <Cancel sx={{ color: '#d32f2f' }} />
                )}
              </TableCell>

              {isCyCommands && (
                <>
                  <TableCell align="center">{item.matchLevel}</TableCell>
                  <TableCell align="center">
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {item.args?.join(', ') || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    {item.url ? (
                      <Link href={item.url} target="_blank" rel="noopener">
                        View
                      </Link>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                </>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`validation-tabpanel-${index}`}
    aria-labelledby={`validation-tab-${index}`}
    style={{ marginTop: '1rem' }}
  >
    {value === index && children}
  </div>
);

const ValidationResponseViewer: React.FC<{ data: ValidationResponse, accuracy: number }> = ({ data, accuracy }) => {
    const [selectedTab, setSelectedTab] = useState(0);
    
    if (!data) return null;
  
    if (data.error) {
      return (
        <Box sx={{ width: '100%' }}>
          <Typography variant="h6" sx={{ fontWeight: 600, marginBottom: 2 }}>
            Validation Response
          </Typography>
          <Alert 
            severity="error"
            sx={{ marginBottom: 2 }}
          >
            {data.message || 'An unexpected error occurred'}
          </Alert>
        </Box>
      );
    }
  
    const { summary, verification_details } = data;
    const tabNames = ['Summary', ...(verification_details ? Object.keys(verification_details) : [])];
  
    const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
      setSelectedTab(newValue);
    };
  
    return (
      <Box sx={{ width: '100%' }}>
        <Typography variant="h6" sx={{ fontWeight: 600, marginBottom: 2 }}>
          Validation Response
          <AccuracyIndicator accuracy={accuracy} />
        </Typography>
        
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs 
            value={selectedTab} 
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
          >
            {tabNames.map((name, index) => (
              <Tab 
                key={name}
                label={name.charAt(0).toUpperCase() + name.slice(1)} 
                id={`validation-tab-${index}`}
                sx={{ textTransform: 'capitalize' }}
              />
            ))}
          </Tabs>
        </Box>
  
        <TabPanel value={selectedTab} index={0}>
          <Alert 
            severity={data.is_valid ? "success" : "warning"}
            sx={{ marginBottom: 2 }}
          >
            {data.is_valid ? "Validation Successful" : "Validation Failed"}
          </Alert>
          <Typography 
            component="pre" 
            sx={{ 
              backgroundColor: '#f9fafb',
              padding: 2,
              borderRadius: 1,
              whiteSpace: 'pre-wrap'
            }}
          >
            {summary}
          </Typography>
        </TabPanel>
  
        {verification_details && Object.entries(verification_details).map(([key, details], index) => (
          <TabPanel value={selectedTab} index={index + 1} key={key}>
            <ValidationTable 
              data={details} 
              title={key}
            />
          </TabPanel>
        ))}
      </Box>
    );
  };

export default ValidationResponseViewer;