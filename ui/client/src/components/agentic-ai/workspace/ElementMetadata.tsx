import React from "react";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

interface ElementMetadataProps {
  fieldName: string;
  fieldSchema: any;
  isRequired: boolean;
  fieldType: "secret" | "public";
  validationHint: any;
  populateHint: any;
  category?: string | null;
  htmlFor?: string;
  labelClassName?: string;
}

export const ElementMetadata: React.FC<ElementMetadataProps> = ({
  fieldName,
  fieldSchema,
  isRequired,
  fieldType,
  validationHint,
  populateHint,
  category,
  htmlFor,
  labelClassName,
}) => {
  const isSecret = fieldType === "secret";

  return (
    <>
      <Label htmlFor={htmlFor || fieldName} className={labelClassName}>
        {fieldName} {isRequired && <span className="text-red-400">*</span>}
        {category && (
          <Badge variant="outline" className="ml-2 text-xs">
            {category}
          </Badge>
        )}
        {isSecret && (
          <Badge variant="outline" className="ml-2 text-xs">
            secret
          </Badge>
        )}
        {validationHint && (
          <Badge variant="outline" className="ml-2 text-xs">
            validation
          </Badge>
        )}
        {populateHint && (
          <Badge variant="outline" className="ml-2 text-xs">
            populate
          </Badge>
        )}
      </Label>
      {fieldSchema.description && (
        <p className="text-xs text-gray-400">{fieldSchema.description}</p>
      )}
    </>
  );
};

