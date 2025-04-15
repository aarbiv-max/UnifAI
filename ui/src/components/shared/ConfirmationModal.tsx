import { Box, Button, Modal, Typography } from "@mui/material";

interface ConfirmationModalProps {
    text: string;
    open: boolean;
    onClose?: any;
    loading?: boolean;
    loaderText?: string;
    handleClick: () => void;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({text, open, onClose, loading, loaderText, handleClick}) => (
    <Modal open={open} onClose={onClose}>
        <Box sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: 400, bgcolor: 'background.paper', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)', p: 3 }}>
            <Typography variant="h6" component="h2" sx={{ mb: 2, fontWeight: 500, color: '#1a1a1a' }}>
                {text}
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3, pt: 2, borderTop: '1px solid #eaeaea' }}>
                <Button onClick={onClose} disabled={loading} style={{padding: '8px 16px', borderRadius: '6px', border: '1px solid #e0e0e0', backgroundColor: '#ffffff', color: '#666666', cursor: 'pointer', transition: 'all 0.2s', fontWeight: 500}}>
                No
                </Button>
                <Button onClick={handleClick} disabled={loading} style={{padding: '8px 16px', borderRadius: '6px', border: 'none', backgroundColor: '#dc2626', color: 'white', cursor: 'pointer', transition: 'all 0.2s', fontWeight: 500,}}>
                {loading ? loaderText : 'Yes'}
                </Button>
            </Box>
        </Box>
    </Modal>
);