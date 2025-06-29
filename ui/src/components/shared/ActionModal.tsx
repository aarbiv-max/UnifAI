import { useState } from "react";
import { TableTooltip } from "./TableTooltip";
import { ConfirmationModal } from "./ConfirmationModal";

type ActionModalProps = {
  datasetDetails: any;
  handleConfirm: (dataset: any, setOpen: React.Dispatch<React.SetStateAction<boolean>>) => Promise<void>;
  icon: React.ElementType;
  title: string;
  disabledCondition: boolean;
  confirmationText: string;
  loaderText: string;
};

export const ActionModal: React.FC<ActionModalProps> = ({
  datasetDetails, handleConfirm, icon, title, disabledCondition, confirmationText, loaderText
}) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleConfirmClick = async () => {
    setLoading(true);
    await handleConfirm(datasetDetails, setOpen);
    setLoading(false);
  };

  return (
    <>
      <TableTooltip icon={icon} title={title} setOpen={setOpen} disabled={disabledCondition} />
      <ConfirmationModal
        text={confirmationText}
        open={open}
        onClose={() => setOpen(false)}
        loading={loading}
        loaderText={loaderText}
        handleClick={handleConfirmClick}
      />
    </>
  );
};
