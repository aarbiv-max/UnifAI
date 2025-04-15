import { Button } from "@mui/material";


interface FormButtonProps {
    type: "button" | "submit" | "reset" | undefined;
    text: string;
    onClick?: any;
    disabled?: boolean;
}

export const FormButton: React.FC<FormButtonProps> = ({type, text, onClick, disabled}) => (
    <Button type={type} variant="contained" className="end-button" onClick={onClick} disabled={disabled}>
        {text}
    </Button>
);
