import { Checkbox } from "@/components/ui/checkbox";

/**
 * A unified selection checkbox component for both single row and "select all" scenarios.
 * 
 * @param checked - Whether the checkbox is currently checked
 * @param onCheckedChange - Callback fired when the checked state changes
 * @param ariaLabel - Accessibility label for the checkbox
 * @param align - Alignment of the checkbox container (left, center, right)
 */
interface SelectionCheckboxProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  ariaLabel?: string;
  align?: "left" | "center" | "right";
  disabled?: boolean;
  title?: string;
}

export function SelectionCheckbox({
  checked,
  onCheckedChange,
  ariaLabel = "Select",
  align = "left",
  disabled = false,
  title,
}: SelectionCheckboxProps) {
  const alignmentClass = 
    align === "center" ? "justify-center" : 
    align === "right" ? "justify-end" : 
    "justify-start";
  
  return (
    <div className={`flex items-center ${alignmentClass}`} title={title}>
      <div 
        className="flex items-center"
        onClick={(e) => e.stopPropagation()}
      >
        <Checkbox
          checked={checked}
          onCheckedChange={(value) => onCheckedChange(value === true)}
          aria-label={ariaLabel}
          disabled={disabled}
        />
      </div>
    </div>
  );
}

