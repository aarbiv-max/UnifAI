import { Box, IconButton, Tooltip } from "@mui/material";

interface TableTooptipProps {
    icon: any;
    title: string;
    setOpen: (open: boolean) => void;
    disabled?: boolean;

}

export const TableTooltip: React.FC<TableTooptipProps> = ({icon: Icon, title, setOpen, disabled}) => (
    <Box display="flex" alignItems="center" gap={1}>
          <Tooltip title={title}>
            <span> 
              <IconButton onClick={() => setOpen(true)} sx={{ color: 'red' }} disabled={disabled}>
                <Icon/>
              </IconButton>
            </span>
          </Tooltip>
        </Box>
);