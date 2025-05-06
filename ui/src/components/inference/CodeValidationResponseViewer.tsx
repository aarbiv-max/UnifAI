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
  path?: any;
  command?: string;
  matchLevel?: string;
  exists: boolean;
  name: string;
  issues?: any;
  usages?: any;
  
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
  // Dynamically gather all unique top-level keys across all items
  const columns = Array.from(
    new Set(
      data.flatMap(item => Object.keys(item))
        .filter(key => key !== 'usages') // usages rendered separately
    )
  );

  const isPrimitive = (val: any) =>
    val == null || typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean';
  
  const renderValue = (value: any) => {
    if (Array.isArray(value)) return value.join(', ');
    if (isPrimitive(value)) return String(value);
    return '-';
  };

  return (
    <TableContainer component={Paper} elevation={0}>
      <Table>
        <TableHead>
          <TableRow>
            {columns.map((col, i) => (
              <TableCell key={i} sx={{ fontWeight: 600 }}>
                {col.charAt(0).toUpperCase() + col.slice(1)}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((item, index) => (
            <React.Fragment key={`${title}-${index}`}>
              <TableRow
                sx={{ backgroundColor: index % 2 === 0 ? '#f9fafb' : 'white' }}
              >
              {columns.map((col, i) => {
                const value = (item as Record<string, any>)[col];
                const isLocal = item.path === 'local';
                const hasDirectIssues = Array.isArray(item.issues) && item.issues.length > 0;
                const hasUsageIssues =
                  Array.isArray(item.usages) &&
                  item.usages.some((u: any) => Array.isArray(u.issues) && u.issues.length > 0);
                const hasIssues = hasDirectIssues || hasUsageIssues;
                

                return (
                  <TableCell key={i} align="left">
                    {col === 'exists' ?  (
                      item.exists ? (
                        isLocal ? (
                          <CheckCircle sx={{ color: '#33d1ff' }} /> // Local
                        ) : hasIssues ? (
                          <CheckCircle sx={{ color: '#f7dc6f' }} /> // Exists with issues
                        ) : (
                          <CheckCircle sx={{ color: '#2e7d32' }} /> // Clean
                        )
                      ) : (
                        <Cancel sx={{ color: '#d32f2f' }} /> // Missing
                      )
                    ): col === 'url' && item.url ? (
                      <Link href={item.url} target="_blank" rel="noopener">
                        View
                      </Link>
                    ) : col === 'issues' && Array.isArray(value) && value.length ? (
                      value.map((issue: string, j: number) => (
                        <Typography
                          key={j}
                          variant="body2"
                          sx={{ fontFamily: 'monospace', color: '#d32f2f' }}
                        >
                          {issue}
                        </Typography>
                      ))
                    ) : (
                      renderValue(value)
                    )}
                  </TableCell>
                );
              })}
              </TableRow>

              {/* Render usages as sub-rows */}
              {Array.isArray(item.usages) &&
                item.usages.map((usage: any, uIdx: number) => (
                  <TableRow key={`usage-${index}-${uIdx}`} sx={{ backgroundColor: '#f0f0f0' }}>
                    <TableCell colSpan={columns.length}>
                      <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>
                        <strong>Args:</strong>{' '}
                        {Array.isArray(usage.args) ? usage.args.join(', ') : '—'}
                      </Typography>
                      {usage.issues?.length > 0 && (
                        <Typography variant="body2" sx={{ mt: 0.5 }}>
                          <strong>Issues:</strong>{' '}
                          {usage.issues.map((issue: string, i: number) => (
                            <span key={i} style={{ color: '#d32f2f', marginRight: 8 }}>
                              {issue}
                            </span>
                          ))}
                        </Typography>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
            </React.Fragment>
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
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <CheckCircle sx={{ color: '#2e7d32', fontSize: 18 }} />
            <Typography variant="body2">Exists and valid</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <CheckCircle sx={{ color: '#f7dc6f', fontSize: 18 }} />
            <Typography variant="body2">Exists but has issues</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <CheckCircle sx={{ color: '#33d1ff', fontSize: 18 }} />
            <Typography variant="body2">Locally defined</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Cancel sx={{ color: '#d32f2f', fontSize: 18 }} />
            <Typography variant="body2">Missing</Typography>
          </Box>
        </Box>
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