import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { Button } from "@/components/ui/button";
import {
  ElementType,
  ElementSchema,
  ElementInstance,
} from "../../../types/workspace";
import { FieldRenderer } from "./FieldRenderer";
import {
  isArrayWithRefItems,
  getArrayItemsSchema,
  extractCategoryFromField,
  extractRefCategories,
} from "./schemaHelpers";
import {
  isFirstLevelField,
  isSystemField,
  isGuiManagedField,
  isCfgDictField,
  FIRST_LEVEL_REQUIRED_FIELDS,
} from "./fieldConstants";
import {
  isHiddenField,
  isSecretField,
  getValidationHint,
  getPopulateHint,
  isArrayField,
  isStringField,
  hasAnyOfArrayType,
  hasAnyOfStringType,
  isBooleanField,
  isObjectField,
} from "./schemaTypeUtils";

interface ElementFormProps {
  isOpen: boolean;
  onClose: () => void;
  elementType: ElementType;
  elementSchema: ElementSchema;
  elementActions?: any[];
  editingElement: ElementInstance | null;
  onSave: (data: any) => Promise<void>;
}

export const ElementForm: React.FC<ElementFormProps> = ({
  isOpen,
  onClose,
  elementType,
  elementSchema,
  elementActions = [],
  editingElement,
  onSave,
}) => {
  const [formData, setFormData] = useState<any>({});
  const [isSaving, setIsSaving] = useState(false);
  const [refOptions, setRefOptions] = useState<{ [category: string]: any[] }>(
    {},
  );
  const [fieldValidationStates, setFieldValidationStates] = useState<{ [fieldName: string]: boolean }>({});

  const { fetchResourcesForCategory } = useWorkspaceData();

  const handleValidationChange = (fieldName: string, isValid: boolean) => {
    setFieldValidationStates(prev => ({
      ...prev,
      [fieldName]: isValid
    }));
  };

  const handlePopulateResult = (fieldName: string, results: string[], multiSelect: boolean) => {
    // Update form data with populated results
    if (multiSelect) {
      // For multi-select, set the array of selected values
      handleInputChange(fieldName, results);
    } else {
      // For single select, set the first (and only) selected value
      handleInputChange(fieldName, results.length > 0 ? results[0] : "");
    }
  };



  // Initialize form data
  useEffect(() => {
    if (elementSchema && isOpen) {
      const initialData: any = {};

      // Set default values from combined schema, excluding hidden fields
      Object.entries(elementSchema.config_schema.properties).forEach(
        ([key, property]: [string, any]) => {
          // Skip hidden fields - don't initialize them
          if (isHiddenField(property)) {
            return;
          }
          
          if (property.default !== undefined) {
            initialData[key] = property.default;
          } else if (isArrayField(property)) {
            initialData[key] = [];
          } else if (isBooleanField(property)) {
            initialData[key] = false;
          } else if (isObjectField(property)) {
            initialData[key] = {};
          } else {
            initialData[key] = "";
          }
        },
      );

      // If editing, populate with existing data (override defaults)
      if (editingElement) {
        // Handle first-level fields directly from editingElement
        // Only handle 'name' field explicitly to avoid TypeScript indexing errors
        if (editingElement.name !== undefined) {
          initialData.name = editingElement.name;
        }

        // Handle config data, excluding hidden fields
        if (editingElement.config) {
          Object.entries(editingElement.config).forEach(([key, value]) => {
            const fieldSchema = elementSchema.config_schema.properties[key];
            
            // Skip hidden fields - don't populate them in edit mode
            if (isHiddenField(fieldSchema)) {
              return;
            }
            
            // Handle $ref values - extract the rid from $ref:rid format
            // Note: Secret fields are handled like normal fields - FieldRenderer handles masking for display
            if (typeof value === "string" && value.startsWith("$ref:")) {
              initialData[key] = value.substring(5); // Remove '$ref:' prefix
            } else if (Array.isArray(value)) {
              // Handle array of $ref values
              initialData[key] = value.map((item: any) =>
                typeof item === "string" && item.startsWith("$ref:")
                  ? item.substring(5)
                  : item,
              );
            } else {
              initialData[key] = value;
            }
          });
        }
      }

      setFormData(initialData);
    }
  }, [elementSchema, editingElement, isOpen]);

  // Re-apply form data when ref options are loaded (for proper pre-selection)
  useEffect(() => {
    if (editingElement?.config && Object.keys(refOptions).length > 0) {
      setFormData((prevData: any) => {
        const updatedData = { ...prevData };

        Object.entries(editingElement.config).forEach(([key, value]) => {
          const fieldSchema = elementSchema?.config_schema.properties[key];
          
          // Skip hidden fields - don't re-apply them
          if (isHiddenField(fieldSchema)) {
            return;
          }
          
          if (typeof value === "string" && value.startsWith("$ref:")) {
            const rid = value.substring(5);
            updatedData[key] = rid;
          } else if (Array.isArray(value)) {
            // Handle array of $ref values
            updatedData[key] = value.map((item: any) =>
              typeof item === "string" && item.startsWith("$ref:")
                ? item.substring(5)
                : item,
            );
          }
        });

        return updatedData;
      });
    }
  }, [refOptions, editingElement]);

  // Load reference options for $ref fields
  useEffect(() => {
    if (elementSchema && isOpen) {
      const refCategories = extractRefCategories(
        elementSchema.config_schema.properties,
        elementSchema.config_schema
      );

      // Fetch actual reference options from Resources API
      const loadRefOptions = async () => {
        const options: { [category: string]: any[] } = {};

        for (const category of Array.from(refCategories)) {
          try {
            const resources = await fetchResourcesForCategory(category);
            options[category] = resources;
          } catch (error) {
            console.error(
              `Failed to load resources for category ${category}:`,
              error,
            );
            options[category] = [];
          }
        }

        setRefOptions(options);
      };

      if (refCategories.size > 0) {
        loadRefOptions();
      }
    }
  }, [elementSchema, isOpen, fetchResourcesForCategory]);

  const handleInputChange = (field: string, value: any) => {
    setFormData((prev: any) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleArrayChange = (field: string, index: number, value: any) => {
    setFormData((prev: any) => ({
      ...prev,
      [field]: prev[field].map((item: any, i: number) =>
        i === index ? value : item,
      ),
    }));
  };

  const addArrayItem = (field: string) => {
    setFormData((prev: any) => ({
      ...prev,
      [field]: [...(prev[field] || []), ""],
    }));
  };

  const removeArrayItem = (field: string, index: number) => {
    setFormData((prev: any) => ({
      ...prev,
      [field]: prev[field].filter((_: any, i: number) => i !== index),
    }));
  };

  // Check if all required fields are filled and validated
  const isFormValid = () => {
    if (!elementSchema) return false;

    // Check all required fields from combined schema, excluding hidden fields
    const required = elementSchema.config_schema.required || [];
    return required.every((field) => {
      const fieldSchema = elementSchema.config_schema.properties[field];
      
      // Skip validation for hidden fields
      if (isHiddenField(fieldSchema)) {
        return true;
      }
      
      const value = formData[field];
      
      // Check if field has validation hint
      const hasValidationHint = !!getValidationHint(fieldSchema);
      
      // Basic value validation
      let hasValue = false;
      if (Array.isArray(value)) {
        hasValue = value.length > 0;
      } else {
        hasValue = value !== undefined && value !== null && value !== "" && 
                  (typeof value !== "string" || value.trim() !== "");
      }
      
      // If field has validation hint and a value, check validation state
      if (hasValidationHint && hasValue) {
        return fieldValidationStates[field] === true;
      }
      
      // Otherwise, just check if value exists
      return hasValue;
    });
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);

      // Validate all required fields from combined schema, excluding hidden fields
      const required = elementSchema.config_schema.required || [];
      const missing = required.filter((field) => {
        const fieldSchema = elementSchema.config_schema.properties[field];
        
        // Skip validation for hidden fields
        if (isHiddenField(fieldSchema)) {
          return false;
        }
        
        const value = formData[field];
        if (Array.isArray(value)) {
          return value.length === 0;
        }
        return !value || (typeof value === "string" && value.trim() === "");
      });

      if (missing.length > 0) {
        alert(`Please fill in required fields: ${missing.join(", ")}`);
        return;
      }

      // Prepare data for saving
      const saveData: any = {};
      const configForSave: any = {};

      // Separate first-level fields and config fields
      Object.entries(formData).forEach(([fieldName, value]) => {
        const fieldSchema = elementSchema.config_schema.properties[fieldName];

        // Skip hidden fields - don't include them in save payload
        if (isHiddenField(fieldSchema)) {
          return;
        }

        if (isFirstLevelField(fieldName)) {
          saveData[fieldName] = typeof value === "string" ? value.trim() : value;
        } else if (!isSystemField(fieldName)) {
          // This is a config field
          let processedValue = value;

          // Convert reference fields back to $ref:rid format and handle empty values
          if (fieldSchema) {
            if (
              fieldSchema.$ref &&
              value &&
              value !== ""
            ) {
              processedValue = `$ref:${value}`;
            }
            // Handle anyOf with $ref
            else if (
              fieldSchema.anyOf &&
              fieldSchema.anyOf.some((option: any) => option.$ref) &&
              value &&
              value !== ""
            ) {
              processedValue = `$ref:${value}`;
            }
            // Handle array fields with $ref items
            else if (
              isArrayWithRefItems(fieldSchema) &&
              Array.isArray(value)
            ) {
              processedValue = value.map((rid: string) => `$ref:${rid}`);
            }
            // Handle empty values based on field type
            else {
              // For array fields, ensure empty arrays instead of empty strings or null
              if (isArrayField(fieldSchema) || hasAnyOfArrayType(fieldSchema)) {
                if (!value || value === "" || (Array.isArray(value) && value.length === 0)) {
                  processedValue = [];
                } else if (Array.isArray(value)) {
                  processedValue = value;
                } else {
                  processedValue = [];
                }
              }
              // For string fields, ensure empty strings instead of null
              else if (isStringField(fieldSchema) || hasAnyOfStringType(fieldSchema)) {
                if (value === null || value === undefined) {
                  processedValue = "";
                } else {
                  processedValue = value;
                }
              }
              // For other types, keep the original value but handle null/undefined
              else {
                if (value === null || value === undefined) {
                  // Skip this field entirely for null/undefined values in non-string, non-array fields
                  return;
                }
                processedValue = value;
              }
            }
          }

          // Only include the field if it has a meaningful value or is required
          const isRequired = elementSchema.config_schema.required?.includes(fieldName);

          // Always include required fields, even if empty
          if (isRequired) {
            configForSave[fieldName] = processedValue;
          }
          // For non-required fields, only include if they have meaningful values
          else if (processedValue !== "" && processedValue !== null && processedValue !== undefined && 
                   !(Array.isArray(processedValue) && processedValue.length === 0)) {
            configForSave[fieldName] = processedValue;
          }
        }
      });

      // Add cfg_dict to save data
      saveData.cfg_dict = configForSave;

      const result = await onSave(saveData);

      // Only close the dialog if save was successful (result is not null/false)
      if (result !== null) {
        onClose();
      }
    } catch (error) {
      console.error("Error saving element:", error);
    } finally {
      setIsSaving(false);
    }
  };

  const renderFormField = (fieldName: string, fieldSchema: any) => {
    const isRequired = elementSchema.config_schema.required?.includes(fieldName);
    const value = formData[fieldName] || "";
    const validationHint = getValidationHint(fieldSchema);
    const populateHint = getPopulateHint(fieldSchema);
    const fieldType = isSecretField(fieldSchema) ? "secret" : "public";

    // Create wrapper functions that pass configSchema to helpers
    const extractCategoryWrapper = (schema: any) => 
      extractCategoryFromField(schema, elementSchema.config_schema);

    return (
      <FieldRenderer
        fieldName={fieldName}
        fieldSchema={fieldSchema}
        value={value}
        isRequired={isRequired}
        validationHint={validationHint}
        populateHint={populateHint}
        editingElement={editingElement}
        elementActions={elementActions}
        elementType={elementType}
        formData={formData}
        refOptions={refOptions}
        fieldType={fieldType}
        isArrayWithRefItems={isArrayWithRefItems}
        getArrayItemsSchema={getArrayItemsSchema}
        extractCategoryFromField={extractCategoryWrapper}
        onInputChange={handleInputChange}
        onArrayChange={handleArrayChange}
        onAddArrayItem={addArrayItem}
        onRemoveArrayItem={removeArrayItem}
        onValidationChange={handleValidationChange}
        onPopulateResult={handlePopulateResult}
      />
    );
  };

  if (!elementSchema) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-background-card border-gray-800 text-foreground max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {editingElement ? "Edit" : "Create"} {elementType.name}
          </DialogTitle>
          <DialogDescription>{elementSchema.description}</DialogDescription>
        </DialogHeader>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSave();
          }}
          className="space-y-4"
        >
          {/* Render fields from combined schema */}
          {Object.entries(elementSchema.config_schema.properties)
            .filter(([fieldName, fieldSchema]) => {
              // Always exclude GUI-managed fields (category, type)
              if (isGuiManagedField(fieldName)) {
                return false;
              }

              // Filter out hidden fields
              if (isHiddenField(fieldSchema)) {
                return false;
              }

              // Show first-level required fields (name is required from resource.schema)
              if (FIRST_LEVEL_REQUIRED_FIELDS.includes(fieldName as any)) {
                return true;
              }

              // Show all cfg_dict fields (element-specific config fields)
              // These are fields that are NOT first-level fields from resource.schema
              return isCfgDictField(fieldName);
            })
            .map(([fieldName, fieldSchema]) => renderFormField(fieldName, fieldSchema))}

          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-primary hover:bg-opacity-80"
              disabled={isSaving || !isFormValid()}
            >
              {isSaving ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};