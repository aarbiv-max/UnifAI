import React, { useState, useEffect } from 'react';
import { styled } from '@mui/material/styles';
import { Stepper, Step, StepLabel, StepConnector, stepConnectorClasses, StepIconProps, Typography, CircularProgress } from '@mui/material';
import axios from '../../http/axiosConfig';

const CustomConnector = styled(StepConnector, {
  shouldForwardProp: (prop) => prop !== 'isLastStepCompleted',
})<{
  isLastStepCompleted?: boolean;
}>(({ isLastStepCompleted }) => ({
  [`&.${stepConnectorClasses.alternativeLabel}`]: {
    top: 22,
  },
  [`&.${stepConnectorClasses.active}`]: {
    [`& .${stepConnectorClasses.line}`]: {
      backgroundImage: isLastStepCompleted
        ? 'linear-gradient(136deg, rgb(131, 212, 117) 0%, rgb(87, 200, 77) 50%, rgb(46, 182, 44) 100%)' // Green if DONE is completed
        : 'linear-gradient(95deg, rgb(242,113,33) 0%,rgb(233,64,87) 50%,rgb(138,35,135) 100%)', // Default red active
    },
  },
  [`&.${stepConnectorClasses.completed}`]: {
    [`& .${stepConnectorClasses.line}`]: {
      backgroundImage: 'linear-gradient(136deg, rgb(131, 212, 117) 0%, rgb(87, 200, 77) 50%, rgb(46, 182, 44) 100%)',
    },
  },
  [`& .${stepConnectorClasses.line}`]: {
    height: 3,
    border: 0,
    backgroundColor: '#eaeaf0',
    borderRadius: 1,
  },
}));

const CustomStepIconRoot = styled('div')<{
  ownerState: { completed?: boolean; active?: boolean; isLastStep?: boolean };
}>(({ ownerState }) => ({
  backgroundColor: '#ccc', // Default grey
  zIndex: 1,
  color: '#fff',
  width: 50,
  height: 50,
  display: 'flex',
  borderRadius: '50%',
  justifyContent: 'center',
  alignItems: 'center',

  ...(ownerState.isLastStep && ownerState.active
    ? {
        backgroundImage: 'linear-gradient(136deg, rgb(131, 212, 117) 0%, rgb(87, 200, 77) 50%, rgb(46, 182, 44) 100%)',
      }
    : ownerState.completed
    ? {
        backgroundImage: 'linear-gradient(136deg, rgb(131, 212, 117) 0%, rgb(87, 200, 77) 50%, rgb(46, 182, 44) 100%)',
      }
    : ownerState.active
    ? {
        backgroundImage: 'linear-gradient(95deg, rgb(242,113,33) 0%, rgb(233,64,87) 50%, rgb(138,35,135) 100%)',
        boxShadow: '0 4px 10px 0 rgba(0,0,0,.25)',
      }
    : {})
}));

const getCustomStepIcon = (statuses: any[], statusValues: any) => (props: StepIconProps) => {
  const { active, completed, className } = props;
  const step = statuses[Number(props.icon) - 1];
  const isLastStep = step?.value === statusValues.DONE;

  return (
    <CustomStepIconRoot ownerState={{ completed, active, isLastStep }} className={className} style={{ position: 'relative' }}>
      {active && !completed && step?.value !== statusValues.DONE && (
        <CircularProgress
          size={58}
          sx={{
            position: 'absolute',
            top: '-4px',
            left: '-4px',
            color: 'rgb(242,113,33)',
          }}
        />
      )}
      {step?.icon}
    </CustomStepIconRoot>
  );
};
 
const StepTextContainer = styled('span')(({ theme }) => ({
  backgroundColor: '#E9EAEC', 
  color: '#636873',
  borderRadius: '12px',
  padding: '6px 12px',
  display: 'inline-block', 
  border: '1px solid #ddd',
  boxShadow: '0px 1px 3px rgba(0, 0, 0, 0.1)', 
}));

export default function StatusStepper({ id, apiFetch, statuses, statusValues }: any) {
  const [currentStatus, setCurrentStatus] = useState('');

  useEffect(() => {
    let intervalId: any;
  
    const fetchStatus = async () => {
      try {
        const response = await axios.get(apiFetch, { params: { formId: id } });
        const formStatus = response.data.status;
        if (formStatus) {
          setCurrentStatus(formStatus);
          // Clear the interval if status is done
          if (formStatus === statusValues.DONE && intervalId) {
            clearInterval(intervalId);
          }
        }
      } catch (error) {
        console.error('Error fetching status:', error);
      }
    };
  
    // Call immediately on mount
    fetchStatus();
    
    intervalId = setInterval(fetchStatus, 2000);
    // Clean up the interval on unmount
    return () => clearInterval(intervalId);
  }, [id]);

  const currentIndex = statuses.findIndex((status: { value: string; }) => status.value === currentStatus);
  const isLastStepCompleted = currentStatus === statusValues.DONE;
  const CustomStepIcon = getCustomStepIcon(statuses, statusValues);


  return (
    <Stepper activeStep={currentIndex} alternativeLabel connector={<CustomConnector isLastStepCompleted={isLastStepCompleted} />}>
      {statuses.map((status: any) => (
        <Step key={status.value}>
          <StepLabel StepIconComponent={CustomStepIcon}>
            <StepTextContainer>{status.label}</StepTextContainer>
          </StepLabel>
        </Step>
      ))}
    </Stepper>
  );
}
