import React from 'react';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { Box, Typography } from '@mui/material';

interface MessageProps {
  text: string;
}

const SuccessMessage: React.FC<MessageProps> = ({text}) => {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'row',
        color: 'black',
        padding: '50px',
        borderRadius: '8px',
        textAlign: 'center',
        height: '85%', 
      }}
    >
      <CheckCircleIcon sx={{ fontSize: 100, color: 'white', fill: 'green !important'  }} />
      <Typography
        variant="h5"
        sx={{
          margin: '20px',
        }}
      >
        {text}
      </Typography>
    </Box>
  );
};

export default SuccessMessage;
