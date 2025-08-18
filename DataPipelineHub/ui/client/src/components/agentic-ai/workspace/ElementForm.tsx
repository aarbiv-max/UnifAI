import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  ElementType,
  ElementSchema,
  ElementInstance,
} from "../../../types/workspace";
import { useWorkspaceData } from "../../../hooks/useWorkspaceData";
import { FieldValidation } from "./FieldValidation";
import { FieldPopulation } from "./FieldPopulation";

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
  const [populateResults, setPopulateResults] = useState<{ [fieldName: string]: string[] }>({});

  const { fetchResourcesForCategory } = useWorkspaceData();

  const handleValidationChange = (fieldName: string, isValid: boolean) => {
    setFieldValidationStates(prev => ({
      ...prev,
      [fieldName]: isValid
    }));
  };

  const handlePopulateResult = (fieldName: string, results: string[], multiSelect: boolean) => {
    setPopulateResults(prev => ({
      ...prev,
      [fieldName]: results
    }));
    
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

      // Set default values from combined schema
      Object.entries(elementSchema.config_schema.properties).forEach(
        ([key, property]: [string, any]) => {
          if (property.default !== undefined) {
            initialData[key] = property.default;
          } else if (property.type === "array") {
            initialData[key] = [];
          } else if (property.type === "boolean") {
            initialData[key] = false;
          } else if (property.type === "object") {
            initialData[key] = {};
          } else {
            initialData[key] = "";
          }
        },
      );

      // If editing, populate with existing data (override defaults)
      if (editingElement) {
        // Handle first-level fields directly from editingElement
        Object.keys(editingElement).forEach((field) => {
          if (field !== 'config' && editingElement[field] !== undefined) {
            initialData[field] = editingElement[field];
          }
        });

        // Handle config data
        if (editingElement.config) {
          Object.entries(editingElement.config).forEach(([key, value]) => {
            // Handle $ref values - extract the rid from $ref:rid format
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
      setFormData((prevData) => {
        const updatedData = { ...prevData };

        Object.entries(editingElement.config).forEach(([key, value]) => {
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

  // Helper function to check if a field is an array with $ref items
  const isArrayWithRefItems = (fieldSchema: any) => {
    // Direct array type
    if (
      fieldSchema.type === "array" &&
      fieldSchema.items &&
      fieldSchema.items.$ref
    ) {
      return true;
    }
    // anyOf structure (like tools field)
    if (fieldSchema.anyOf && Array.isArray(fieldSchema.anyOf)) {
      return fieldSchema.anyOf.some(
        (option: any) =>
          option.type === "array" && option.items && option.items.$ref,
      );
    }
    return false;
  };

  // Helper function to get array items schema from anyOf or direct structure
  const getArrayItemsSchema = (fieldSchema: any) => {
    if (fieldSchema.type === "array" && fieldSchema.items) {
      return fieldSchema.items;
    }
    if (fieldSchema.anyOf && Array.isArray(fieldSchema.anyOf)) {
      const arrayOption = fieldSchema.anyOf.find(
        (option: any) => option.type === "array" && option.items,
      );
      return arrayOption?.items;
    }
    return null;
  };

  // Helper function to parse JSON path from reference string
  const parseJsonPath = (ref: string): string[] | null => {
    if (!ref || typeof ref !== 'string' || !ref.startsWith('#/')) {
      return null;
    }

    // Remove the '#/' prefix and split by '/'
    const pathString = ref.substring(2);
    if (!pathString) {
      return null;
    }

    return pathString.split('/').filter(segment => segment.length > 0);
  };

  // Generic helper function to resolve JSON path in an object
  const resolveJsonPath = (obj: any, pathSegments: string[]): any | null => {
    if (!obj || !pathSegments || pathSegments.length === 0) {
      return null;
    }

    let current = obj;
    for (const segment of pathSegments) {
      if (!current || typeof current !== 'object' || !(segment in current)) {
        return null;
      }
      current = current[segment];
    }

    return current;
  };

  // Helper function to find definition in schema by reference path
  const findDefinitionByRef = (ref: string): any | null => {
    const pathSegments = parseJsonPath(ref);
    if (!pathSegments || !elementSchema?.config_schema) {
      return null;
    }

    return resolveJsonPath(elementSchema.config_schema, pathSegments);
  };

  // Helper function to resolve $ref to actual definition with full details
  const resolveRef = (ref: string): any | null => {
    const definition = findDefinitionByRef(ref);
    if (definition) {
      console.log(`Resolved $ref ${ref} to:`, definition);
      return definition;
    }

    console.warn(`Could not resolve $ref: ${ref}`);
    return null;
  };

  // Helper function to extract category from resolved definition
  const extractCategoryFromDefinition = (definition: any): string | null => {
    if (!definition || typeof definition !== 'object') {
      return null;
    }

    // Direct category property
    if (definition.category && typeof definition.category === 'string') {
      return definition.category;
    }

    return null;
  };

  // Helper function to extract category from $ref field or anyOf structure
  const extractCategoryFromField = (fieldSchema: any): string | null => {
    // Handle direct $ref by resolving it
    if (fieldSchema.$ref) {
      const resolved = resolveRef(fieldSchema.$ref);
      const category = extractCategoryFromDefinition(resolved);
      if (category) {
        return category;
      }
    }

    // Handle items with $ref (for arrays)
    if (fieldSchema.items && fieldSchema.items.$ref) {
      const resolved = resolveRef(fieldSchema.items.$ref);
      const category = extractCategoryFromDefinition(resolved);
      if (category) {
        return category;
      }
    }

    // Category from anyOf structure
    if (fieldSchema.anyOf && Array.isArray(fieldSchema.anyOf)) {
      // Check for direct $ref in anyOf
      for (const option of fieldSchema.anyOf) {
        if (option.$ref) {
          const resolved = resolveRef(option.$ref);
          const category = extractCategoryFromDefinition(resolved);
          if (category) {
            return category;
          }
        }

        // Check for array with $ref items in anyOf
        if (option.type === "array" && option.items && option.items.$ref) {
          const resolved = resolveRef(option.items.$ref);
          const category = extractCategoryFromDefinition(resolved);
          if (category) {
            return category;
          }
        }
      }
    }
    return null; // Return null if no category is found
  };

  // Load reference options for $ref fields
  useEffect(() => {
    if (elementSchema && isOpen) {
      const refFields = Object.entries(
        elementSchema.config_schema.properties,
      ).filter(
        ([, property]: [string, any]) =>
          property.$ref ||
          (property.items && property.items.$ref) ||
          (property.type === "array" &&
            property.items &&
            property.items.$ref) ||
          isArrayWithRefItems(property) ||
          (property.anyOf && property.anyOf.some((option: any) => option.$ref)),
      );

      const refCategories = new Set<string>();
      refFields.forEach(([, property]: [string, any]) => {
        const category = extractCategoryFromField(property);
        if (category) {
          refCategories.add(category);
        }
      });

      // Fetch actual reference options from Resources API
      const loadRefOptions = async () => {
        const options: { [category: string]: any[] } = {};

        for (const category of refCategories) {
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
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleArrayChange = (field: string, index: number, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field]: prev[field].map((item: any, i: number) =>
        i === index ? value : item,
      ),
    }));
  };

  const addArrayItem = (field: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]: [...(prev[field] || []), ""],
    }));
  };

  const removeArrayItem = (field: string, index: number) => {
    setFormData((prev) => ({
      ...prev,
      [field]: prev[field].filter((_: any, i: number) => i !== index),
    }));
  };

  // Check if all required fields are filled and validated
  const isFormValid = () => {
    if (!elementSchema) return false;

    // Check all required fields from combined schema
    const required = elementSchema.config_schema.required || [];
    return required.every((field) => {
      const value = formData[field];
      const fieldSchema = elementSchema.config_schema.properties[field];
      
      // Check if field has validation hint
      const hasValidationHint = fieldSchema?.hints?.action?.hint_type === 'validate';
      
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

      // Validate all required fields from combined schema
      const required = elementSchema.config_schema.required || [];
      const missing = required.filter((field) => {
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

        // Define which fields are first-level fields from resource schema
        const firstLevelResourceFields = ['name', 'category', 'type', 'cfg_dict', 'version', 'created', 'updated', 'nested_refs', 'rid', 'user_id'];

        // Only include 'name' as a first-level field for saving (exclude version and system fields)
        const isFirstLevelField = fieldName === 'name';

        // System fields that should never be included in save payload
        const systemFields = ['version', 'created', 'updated', 'nested_refs', 'rid', 'user_id', 'category', 'type', 'cfg_dict'];

        if (isFirstLevelField) {
          saveData[fieldName] = typeof value === "string" ? value.trim() : value;
        } else if (!systemFields.includes(fieldName)) {
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
              if (fieldSchema.type === "array" || 
                  (fieldSchema.anyOf && fieldSchema.anyOf.some((option: any) => option.type === "array"))) {
                if (!value || value === "" || (Array.isArray(value) && value.length === 0)) {
                  processedValue = [];
                } else if (Array.isArray(value)) {
                  processedValue = value;
                } else {
                  processedValue = [];
                }
              }
              // For string fields, ensure empty strings instead of null
              else if (fieldSchema.type === "string" || 
                       (fieldSchema.anyOf && fieldSchema.anyOf.some((option: any) => option.type === "string"))) {
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
      if (result !== null && result !== false) {
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
    const validationHint = fieldSchema.hints?.action?.hint_type === 'validate' ? fieldSchema.hints.action : null;
    const populateHint = fieldSchema.hints?.action?.hint_type === 'populate' ? fieldSchema.hints.action : null;

    // Handle array fields with $ref items (multi-select dropdown)
    if (isArrayWithRefItems(fieldSchema)) {
      const itemsSchema = getArrayItemsSchema(fieldSchema);
      const category = extractCategoryFromField(fieldSchema);

      if (!category) {
        console.warn(`No category found for array field ${fieldName}`);
        return null;
      }

      const validOptions = (refOptions[category] || []).filter(
        (option: any) => option.rid && option.rid.trim() !== "",
      );

      return (
        <div key={fieldName} className="space-y-2">
          <Label htmlFor={fieldName}>
            {fieldName} {isRequired && <span className="text-red-400">*</span>}
            {category && (
              <Badge variant="outline" className="ml-2 text-xs">
                {category}
              </Badge>
            )}
          </Label>
          <div className="space-y-2">
            <Select
              value=""
              onValueChange={(newValue) => {
                if (newValue && newValue !== "__no_options_disabled__") {
                  const currentArray = formData[fieldName] || [];
                  if (!currentArray.includes(newValue)) {
                    handleInputChange(fieldName, [...currentArray, newValue]);
                  }
                }
              }}
            >
              <SelectTrigger className="bg-background-dark">
                <SelectValue placeholder={`Add ${category}`} />
              </SelectTrigger>
              <SelectContent>
                {validOptions.map((option: any) => (
                  <SelectItem key={option.rid} value={option.rid}>
                    {option.name} ({option.type})
                  </SelectItem>
                ))}
                {validOptions.length === 0 && (
                  <SelectItem value="__no_options_disabled__" disabled>
                    No {category} resources available
                  </SelectItem>
                )}
              </SelectContent>
            </Select>

            {/* Show selected items */}
            {value && Array.isArray(value) && value.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {value.map((selectedRid: string, index: number) => {
                  const selectedOption = validOptions.find(
                    (opt: any) => opt.rid === selectedRid,
                  );
                  return (
                    <Badge
                      key={index}
                      variant="secondary"
                      className="flex items-center gap-1"
                    >
                      {selectedOption
                        ? `${selectedOption.name} (${selectedOption.type})`
                        : selectedRid}
                      <button
                        type="button"
                        onClick={() => {
                          const newArray = value.filter(
                            (_: any, i: number) => i !== index,
                          );
                          handleInputChange(fieldName, newArray);
                        }}
                        className="ml-1 text-xs hover:text-red-400"
                      >
                        ×
                      </button>
                    </Badge>
                  );
                })}
              </div>
            )}
          </div>
          {fieldSchema.description && (
            <p className="text-xs text-gray-400">{fieldSchema.description}</p>
          )}
        </div>
      );
    }

    // Handle $ref fields (dropdown selection) - including anyOf with $ref
    const hasRefField = fieldSchema.$ref || 
      (fieldSchema.anyOf && fieldSchema.anyOf.some((option: any) => option.$ref));

    if (hasRefField) {
      const category = extractCategoryFromField(fieldSchema);


      if (category) {
        const validOptions = (refOptions[category] || []).filter(
          (option: any) => option.rid && option.rid.trim() !== "",
        );

        return (
          <div key={fieldName} className="space-y-2">
            <Label htmlFor={fieldName}>
              {fieldName} {isRequired && <span className="text-red-400">*</span>}
              {category && (
                <Badge variant="outline" className="ml-2 text-xs">
                  {category}
                </Badge>
              )}
            </Label>
            <Select
              value={value && value !== "" ? value : undefined}
              onValueChange={(newValue) => {
                handleInputChange(fieldName, newValue);
              }}
            >
              <SelectTrigger className="bg-background-dark">
                <SelectValue placeholder={`Select ${fieldName}`} />
              </SelectTrigger>
              <SelectContent>
                {validOptions.map((option: any) => (
                  <SelectItem key={option.rid} value={option.rid}>
                    {option.name} ({option.type})
                  </SelectItem>
                ))}
                {validOptions.length === 0 && (
                  <SelectItem value="__no_options_disabled__" disabled>
                    No {category} resources available
                  </SelectItem>
                )}
              </SelectContent>
            </Select>

            {fieldSchema.description && (
              <p className="text-xs text-gray-400">{fieldSchema.description}</p>
            )}
          </div>
        );
      }
    }

    // Handle object fields (like 'extra')
    if (fieldSchema.type === "object") {
      return (
        <div key={fieldName} className="space-y-2">
          <Label htmlFor={fieldName}>
            {fieldName} {isRequired && <span className="text-red-400">*</span>}
          </Label>
          <Textarea
            id={fieldName}
            value={
              typeof value === "object" ? JSON.stringify(value, null, 2) : value
            }
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value);
                handleInputChange(fieldName, parsed);
              } catch (error) {
                // If invalid JSON, store as string for now
                handleInputChange(fieldName, e.target.value);
              }
            }}
            rows={6}
            className="bg-background-dark resize-none font-mono text-sm"
            placeholder="Enter JSON object (e.g., {})"
          />
          {fieldSchema.description && (
            <p className="text-xs text-gray-400">{fieldSchema.description}</p>
          )}
        </div>
      );
    }

    // Handle array fields (non-$ref arrays)
    if (fieldSchema.type === "array") {
      return (
        <div key={fieldName} className="space-y-2">
          <Label>
            {fieldName} {isRequired && <span className="text-red-400">*</span>}
          </Label>
          <div className="space-y-2">
            {(value || []).map((item: any, index: number) => (
              <div key={index} className="flex gap-2">
                <Input
                  value={item}
                  onChange={(e) =>
                    handleArrayChange(fieldName, index, e.target.value)
                  }
                  className="bg-background-dark flex-1"
                  placeholder={`${fieldName} item ${index + 1}`}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => removeArrayItem(fieldName, index)}
                >
                  Remove
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => addArrayItem(fieldName)}
            >
              Add {fieldName}
            </Button>
          </div>
          {fieldSchema.description && (
            <p className="text-xs text-gray-400">{fieldSchema.description}</p>
          )}
        </div>
      );
    }

    // Handle boolean fields
    if (fieldSchema.type === "boolean") {
      return (
        <div key={fieldName} className="space-y-2">
          <div className="flex items-center space-x-2">
            <Checkbox
              id={fieldName}
              checked={value}
              onCheckedChange={(checked) =>
                handleInputChange(fieldName, checked)
              }
            />
            <Label htmlFor={fieldName}>
              {fieldName}{" "}
              {isRequired && <span className="text-red-400">*</span>}
            </Label>
          </div>
          {fieldSchema.description && (
            <p className="text-xs text-gray-400">{fieldSchema.description}</p>
          )}
        </div>
      );
    }

    // Handle number fields (including anyOf with integer/number types)
    const isNumberField = fieldSchema.type === "integer" || 
      fieldSchema.type === "number" ||
      (fieldSchema.anyOf && fieldSchema.anyOf.some((option: any) => 
        option.type === "integer" || option.type === "number"
      ));

    if (isNumberField) {
      return (
        <div key={fieldName} className="space-y-2">
          <Label htmlFor={fieldName}>
            {fieldName} {isRequired && <span className="text-red-400">*</span>}
          </Label>
          <Input
            id={fieldName}
            type="number"
            value={value || ""}
            onChange={(e) => {
              const numValue = e.target.value === "" ? null : parseFloat(e.target.value);
              handleInputChange(fieldName, numValue);
            }}
            className="bg-background-dark"
            placeholder={fieldSchema.description}
          />
          {fieldSchema.description && (
            <p className="text-xs text-gray-400">{fieldSchema.description}</p>
          )}
        </div>
      );
    }

    // Handle long text fields
    if (
      fieldName.includes("message") ||
      fieldName.includes("prompt") ||
      fieldName.includes("description")
    ) {
      return (
        <div key={fieldName} className="space-y-2">
          <Label htmlFor={fieldName}>
            {fieldName} {isRequired && <span className="text-red-400">*</span>}
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
          <Textarea
            id={fieldName}
            value={value}
            onChange={(e) => handleInputChange(fieldName, e.target.value)}
            rows={4}
            className="bg-background-dark resize-none"
            placeholder={fieldSchema.description}
            readOnly={!!populateHint}
            disabled={!!populateHint}
          />
          {validationHint && (
            <FieldValidation
              fieldName={fieldName}
              fieldValue={value}
              validationHint={validationHint}
              elementActions={elementActions}
              selectedElementType={elementType}
              onValidationChange={handleValidationChange}
            />
          )}
          {populateHint && (
            <FieldPopulation
              fieldName={fieldName}
              populateHint={populateHint}
              elementActions={elementActions}
              selectedElementType={elementType}
              formData={formData}
              onPopulateResult={handlePopulateResult}
            />
          )}
          {fieldSchema.description && (
            <p className="text-xs text-gray-400">{fieldSchema.description}</p>
          )}
        </div>
      );
    }

    // Handle regular string fields
    return (
      <div key={fieldName} className="space-y-2">
        <Label htmlFor={fieldName}>
          {fieldName} {isRequired && <span className="text-red-400">*</span>}
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
        <Input
          id={fieldName}
          value={value}
          onChange={(e) => handleInputChange(fieldName, e.target.value)}
          className="bg-background-dark"
          placeholder={fieldSchema.description}
          readOnly={!!populateHint}
          disabled={!!populateHint}
        />
        {validationHint && (
          <FieldValidation
            fieldName={fieldName}
            fieldValue={value}
            validationHint={validationHint}
            elementActions={elementActions}
            selectedElementType={elementType}
            onValidationChange={handleValidationChange}
          />
        )}
        {populateHint && (
          <FieldPopulation
            fieldName={fieldName}
            populateHint={populateHint}
            elementActions={elementActions}
            selectedElementType={elementType}
            formData={formData}
            onPopulateResult={handlePopulateResult}
          />
        )}
        {fieldSchema.description && (
            <p className="text-xs text-gray-400">{fieldSchema.description}</p>
          )}
      </div>
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
            .filter(([fieldName]) => {
              // Always exclude category and type (handled by GUI)
              if (['category', 'type'].includes(fieldName)) {
                return false;
              }

              // For both Create New and Edit mode: show only first-level required fields (name) + all cfg_dict fields
              // Show first-level required fields (name is required from resource.schema)
              const firstLevelRequiredFields = ['name'];
              if (firstLevelRequiredFields.includes(fieldName)) {
                return true;
              }

              // Show all cfg_dict fields (element-specific config fields)
              // These are fields that are NOT first-level fields from resource.schema
              const firstLevelFields = ['name', 'category', 'type', 'cfg_dict', 'version', 'created', 'updated', 'nested_refs', 'rid', 'user_id'];
              const isCfgDictField = !firstLevelFields.includes(fieldName);
              return isCfgDictField;

              // Comment out the old edit mode logic that showed extra fields
              // // For Edit mode: show all fields (except category/type)
              // if (editingElement) {
              //   return true;
              // }
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