import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";

/**
 * A unified selection checkbox component for both single row and "select all" scenarios.
 */
interface SelectionCheckboxProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  ariaLabel?: string;
  align?: "left" | "center" | "right";
}

const checkboxClassName =
  "h-[18px] w-[18px] rounded-[5px] border-2 border-muted-foreground/35 bg-background/80 shadow-sm transition-all duration-150 " +
  "data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground " +
  "hover:border-muted-foreground/55 focus-visible:ring-2 focus-visible:ring-primary/35 focus-visible:ring-offset-2 focus-visible:ring-offset-background";

export function SelectionCheckbox({
  checked,
  onCheckedChange,
  ariaLabel = "Select",
  align = "left",
}: SelectionCheckboxProps) {
  const alignmentClass =
    align === "center" ? "justify-center" : align === "right" ? "justify-end" : "justify-start";

  return (
    <div className={cn("flex items-center", alignmentClass)}>
      <div className="flex items-center rounded-md p-0.5 hover:bg-muted/40" onClick={(e) => e.stopPropagation()}>
        <Checkbox
          checked={checked}
          onCheckedChange={(value) => onCheckedChange(value === true)}
          aria-label={ariaLabel}
          className={checkboxClassName}
        />
      </div>
    </div>
  );
}

