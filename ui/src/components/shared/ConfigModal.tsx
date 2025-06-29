import { Box, Modal, Typography } from "@mui/material";
import { TableTooltip } from "./TableTooltip";
import { useState } from "react";
import SyntaxHighlighter from "react-syntax-highlighter";
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import DescriptionIcon from '@mui/icons-material/Description';


export const ConfigModal = ({ config }: { config: object }) => {
    const [open, setOpen] = useState(false);

    return (
      <>
        <TableTooltip icon={DescriptionIcon} title="Configuration File" setOpen={setOpen} />
        <Modal open={open} onClose={() => setOpen(false)}>
          <Box sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', height: '70%', width: '80%', bgcolor: 'background.paper', padding: 3, overflow: 'auto' }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Model Config</Typography>
            <SyntaxHighlighter language="json" style={atomOneDark}>
              {JSON.stringify(config, null, 2)}
            </SyntaxHighlighter>
          </Box>
        </Modal>
      </>
    );
  };