import { TextField, MenuItem, FormControlLabel, Checkbox, Typography, Box, Tooltip, styled, TooltipProps, tooltipClasses, Button } from '@mui/material';
import { Controller } from 'react-hook-form';
import InfoIcon from '@mui/icons-material/Info';
import { useRef } from 'react';
interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

interface FormFieldProps {
  name: string;
  label: string;
  control: any;
  errors: any;
  type?: string;
  disabled?: boolean;
  secret?: boolean;
  tooltip?: string;
}

interface FormDropdownProps {
  name: string;
  label: string;
  control: any;
  errors: any;
  options: string[];
  onSelect?: (value: string) => void; // Optional onSelect prop
  disabled?: boolean;
}

interface FormCheckboxProps {
  name: string;
  label: string;
  control: any;
  errors: any;
}

interface FormFileUploadProps {
  name: string;
  label: string;
  control: any;
  errors: any;
  onFileUpload: (files: FileList | null) => void;
  accept?: string;
}

const LightTooltip = styled(({ className, ...props }: TooltipProps) => (
  <Tooltip {...props} classes={{ popper: className }} />
))(({ theme }) => ({
  [`& .${tooltipClasses.tooltip}`]: {
    backgroundColor: theme.palette.common.white,
    color: 'rgba(0, 0, 0, 0.87)',
    boxShadow: theme.shadows[1],
    fontSize: 15,
  },
}));

export const FormField: React.FC<FormFieldProps> = ({
  name,
  label,
  control,
  errors,
  type = "text",
  disabled = false,
  secret = false,
  tooltip,
}) => {
  return (
    <div className="form-group">
      <div style={{ display: "flex", alignItems: "center", gap: 1, cursor: "pointer" }}>
        {tooltip &&
          <LightTooltip title={tooltip || ""} disableHoverListener={!tooltip} arrow>
              <InfoIcon fontSize={'small'} sx={{ color: "gray", margin: "0px 4px 5px 0px" }} />
          </LightTooltip>}
        <label>{label}</label>
      </div>
      <Controller
        name={name}
        control={control}
        render={({ field }) => (
          <TextField
            {...field}
            type={secret ? "password" : type}
            fullWidth
            error={!!errors[name]}
            helperText={errors[name]?.message}
            disabled={disabled}
          />
        )}
      />
    </div>
  );
};

export const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`simple-tabpanel-${index}`}
    aria-labelledby={`simple-tab-${index}`}
    {...other}
  >
    {value === index && (
      <Box p={3}>
        <Typography>{children}</Typography>
      </Box>
    )}
  </div>
);


export const FormDropdown: React.FC<FormDropdownProps> = ({ name, label, control, errors, options, onSelect, disabled = false }) => (
  <div className="form-group">
    <label>{label}</label>
    <Controller
      name={name}
      control={control}
      render={({ field }) => (
        <TextField
          {...field}
          select
          fullWidth
          error={!!errors[name]}
          helperText={errors[name]?.message}
          disabled={disabled}
          onChange={(e) => {
            field.onChange(e); // Update react-hook-form field
            if (onSelect) {
              onSelect(e.target.value); // Call onSelect if provided
            }
          }}
        >
          {options.map((option) => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </TextField>
      )}
    />
  </div>
);

export const FormCheckbox: React.FC<FormCheckboxProps> = ({ name, label, control, errors }) => (
  <div className="form-group">
    <Controller
      name={name}
      control={control}
      render={({ field }) => (
        <FormControlLabel
          control={<Checkbox {...field} checked={field.value} />}
          label={label}
        />)}
    />
  </div>
);


export const FormFileUpload: React.FC<FormFileUploadProps> = ({ name, label, control, errors, onFileUpload }) => (
  <div className="form-group">
    <label>{label}</label>
    <Controller
      name={name}
      control={control}
      render={({ field }) => (
        <input
          type="file"
          accept=".py"
          onChange={(e) => {
            onFileUpload(e.target.files);
          }}
        />
      )}
    />
    {errors[name] && <Typography color="error">{errors[name]?.message}</Typography>}
  </div>
);

export const FormFileUploadHelm: React.FC<FormFileUploadProps> = ({ name, label, control, errors, onFileUpload, accept }) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleButtonClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div className="form-group">
      <label>{label}</label>
      <input
        type="file"
        accept={accept}
        ref={fileInputRef}
        style={{ display: 'none' }} 
        onChange={(e) => onFileUpload(e.target.files)}
      />
      <Button className="end-button" variant="contained" onClick={handleButtonClick}>
        Choose File
      </Button>
      {errors[name] && <Typography color="error">{errors[name]?.message}</Typography>}
    </div>
  );
};