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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info, ExternalLink, ChevronDown, ChevronRight, Copy, Check } from "lucide-react";
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
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const [commandCopied, setCommandCopied] = useState(false);

  const { fetchResourcesForCategory } = useWorkspaceData();

  const toggleStep = (stepIndex: number) => {
    setExpandedStep(expandedStep === stepIndex ? null : stepIndex);
  };

  const copyCommandToClipboard = () => {
    const command = `cd ~/Downloads
mv local_mcp.txt local_mcp.sh
chmod +x local_mcp.sh
./local_mcp.sh \\
  --client_id "YOUR_CLIENT_ID" \\
  --client_secret "YOUR_CLIENT_SECRET" \\
  --user_email "your-email@example.com"`;
    
    navigator.clipboard.writeText(command).then(() => {
      setCommandCopied(true);
      setTimeout(() => setCommandCopied(false), 2000);
    }).catch(err => {
      console.error('Failed to copy:', err);
    });
  };

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

      // Set default values from combined schema, excluding hidden fields
      Object.entries(elementSchema.config_schema.properties).forEach(
        ([key, property]: [string, any]) => {
          // Skip hidden fields - don't initialize them
          if (property?.hints?.hidden?.hint_type === "hidden") {
            return;
          }
          
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
        // Handle first-level fields directly from editingElement using type-safe access
        (Object.keys(editingElement) as Array<keyof ElementInstance>).forEach((field) => {
          if (field !== 'config' && editingElement[field] !== undefined) {
            initialData[field] = editingElement[field];
          }
        });

        // Handle config data, excluding hidden fields
        if (editingElement.config) {
          Object.entries(editingElement.config).forEach(([key, value]) => {
            const fieldSchema = elementSchema.config_schema.properties[key];
            
            // Skip hidden fields - don't populate them in edit mode
            if (fieldSchema?.hints?.hidden?.hint_type === "hidden") {
              return;
            }
            
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
          const fieldSchema = elementSchema?.config_schema.properties[key];
          
          // Skip hidden fields - don't re-apply them
          if (fieldSchema?.hints?.hidden?.hint_type === "hidden") {
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

    // Check all required fields from combined schema, excluding hidden fields
    const required = elementSchema.config_schema.required || [];
    return required.every((field) => {
      const fieldSchema = elementSchema.config_schema.properties[field];
      
      // Skip validation for hidden fields
      if (fieldSchema?.hints?.hidden?.hint_type === "hidden") {
        return true;
      }
      
      const value = formData[field];
      
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

      // Validate all required fields from combined schema, excluding hidden fields
      const required = elementSchema.config_schema.required || [];
      const missing = required.filter((field) => {
        const fieldSchema = elementSchema.config_schema.properties[field];
        
        // Skip validation for hidden fields
        if (fieldSchema?.hints?.hidden?.hint_type === "hidden") {
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
        if (fieldSchema?.hints?.hidden?.hint_type === "hidden") {
          return;
        }

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

    // Debug logging for 'kind' field
    if (fieldName === 'kind') {
      console.log('[KIND FIELD DEBUG] Full analysis:', {
        fieldName,
        fieldSchema,
        hasEnum: !!fieldSchema.enum,
        hasAnyOf: !!fieldSchema.anyOf,
        hasAllOf: !!fieldSchema.allOf,
        value,
        '$defs': elementSchema?.config_schema?.$defs,
      });
      
      // Check if allOf path exists
      if (fieldSchema.allOf) {
        const refPath = fieldSchema.allOf.find((item: any) => item.$ref)?.$ref;
        console.log('[KIND FIELD DEBUG] allOf refPath:', refPath);
        if (refPath && elementSchema?.config_schema?.$defs) {
          const defName = refPath.split('/').pop();
          console.log('[KIND FIELD DEBUG] defName:', defName);
          console.log('[KIND FIELD DEBUG] enumDef:', elementSchema.config_schema.$defs[defName]);
        }
      }
    }

    // Handle direct $ref to enum definitions (Pydantic Enum types)
    if (fieldSchema.$ref && elementSchema?.config_schema?.$defs) {
      // Extract definition name from $ref path (e.g., "#/$defs/McpKind" -> "McpKind")
      const defName = fieldSchema.$ref.split('/').pop();
      const enumDef = elementSchema.config_schema.$defs[defName];
      
      if (enumDef?.enum && Array.isArray(enumDef.enum)) {
        console.log(`[DIRECT REF ENUM FIELD] ${fieldName}:`, enumDef);
        return (
          <div key={fieldName} className="space-y-2">
            <Label htmlFor={fieldName}>
              {fieldName} {isRequired && <span className="text-red-400">*</span>}
            </Label>
            <Select
              value={value || fieldSchema.default || enumDef.enum[0]}
              onValueChange={(newValue) => handleInputChange(fieldName, newValue)}
            >
              <SelectTrigger className="bg-background-dark">
                <SelectValue placeholder={`Select ${fieldName}`} />
              </SelectTrigger>
              <SelectContent>
                {enumDef.enum.map((option: string) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {fieldSchema.description && (
              <p className="text-xs text-gray-400">{fieldSchema.description}</p>
            )}
          </div>
        );
      }
    }

    // Handle allOf with $ref to enum definitions (Pydantic Enum types)
    if (fieldSchema.allOf && Array.isArray(fieldSchema.allOf)) {
      const refPath = fieldSchema.allOf.find((item: any) => item.$ref)?.$ref;
      if (refPath && elementSchema?.config_schema?.$defs) {
        // Extract definition name from $ref path (e.g., "#/$defs/McpKind" -> "McpKind")
        const defName = refPath.split('/').pop();
        const enumDef = elementSchema.config_schema.$defs[defName];
        
        if (enumDef?.enum && Array.isArray(enumDef.enum)) {
          console.log(`[ALLOF ENUM FIELD] ${fieldName}:`, enumDef);
          return (
            <div key={fieldName} className="space-y-2">
              <Label htmlFor={fieldName}>
                {fieldName} {isRequired && <span className="text-red-400">*</span>}
              </Label>
              <Select
                value={value || fieldSchema.default || enumDef.enum[0]}
                onValueChange={(newValue) => handleInputChange(fieldName, newValue)}
              >
                <SelectTrigger className="bg-background-dark">
                  <SelectValue placeholder={`Select ${fieldName}`} />
                </SelectTrigger>
                <SelectContent>
                  {enumDef.enum.map((option: string) => (
                    <SelectItem key={option} value={option}>
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {fieldSchema.description && (
                <p className="text-xs text-gray-400">{fieldSchema.description}</p>
              )}
            </div>
          );
        }
      }
    }

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

    // Handle enum fields (Pydantic Enum types)
    if (fieldSchema.enum && Array.isArray(fieldSchema.enum)) {
      console.log(`[ENUM FIELD] ${fieldName}:`, fieldSchema);
      return (
        <div key={fieldName} className="space-y-2">
          <Label htmlFor={fieldName}>
            {fieldName} {isRequired && <span className="text-red-400">*</span>}
          </Label>
          <Select
            value={value || fieldSchema.default || fieldSchema.enum[0]}
            onValueChange={(newValue) => handleInputChange(fieldName, newValue)}
          >
            <SelectTrigger className="bg-background-dark">
              <SelectValue placeholder={`Select ${fieldName}`} />
            </SelectTrigger>
            <SelectContent>
              {fieldSchema.enum.map((option: string) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {fieldSchema.description && (
            <p className="text-xs text-gray-400">{fieldSchema.description}</p>
          )}
        </div>
      );
    }

    // Handle enum/Literal fields with anyOf structure (Pydantic Literal types)
    if (fieldSchema.anyOf && Array.isArray(fieldSchema.anyOf)) {
      // Check if this is an enum-like anyOf (all options have 'const' values)
      const enumValues = fieldSchema.anyOf
        .filter((option: any) => option.const !== undefined)
        .map((option: any) => option.const);
      
      if (enumValues.length > 0) {
        console.log(`[ANYOF ENUM FIELD] ${fieldName}:`, fieldSchema, 'values:', enumValues);
        return (
          <div key={fieldName} className="space-y-2">
            <Label htmlFor={fieldName}>
              {fieldName} {isRequired && <span className="text-red-400">*</span>}
            </Label>
            <Select
              value={value || fieldSchema.default || enumValues[0]}
              onValueChange={(newValue) => handleInputChange(fieldName, newValue)}
            >
              <SelectTrigger className="bg-background-dark">
                <SelectValue placeholder={`Select ${fieldName}`} />
              </SelectTrigger>
              <SelectContent>
                {enumValues.map((option: string) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {fieldSchema.description && (
              <p className="text-xs text-gray-400">{fieldSchema.description}</p>
            )}
          </div>
        );
      }
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
    
    return (
      <div key={fieldName} className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor={fieldName} className="flex items-center gap-2">
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
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-xs text-primary hover:text-primary/80 hover:bg-primary/10"
                    onClick={(e) => {
                      e.preventDefault();
                      const guidePath = "/guides/mcp-server-setup-guide.md";
                      // Try to download the guide file
                      fetch(guidePath)
                        .then((response) => {
                          if (!response.ok) {
                            throw new Error("File not found");
                          }
                          return response.blob();
                        })
                        .then((blob) => {
                          const url = window.URL.createObjectURL(blob);
                          const link = document.createElement("a");
                          link.href = url;
                          link.download = "mcp-server-setup-guide.md";
                          document.body.appendChild(link);
                          link.click();
                          document.body.removeChild(link);
                          window.URL.revokeObjectURL(url);
                        })
                        .catch(() => {
                          // If download fails, try opening in new tab
                          window.open(guidePath, "_blank");
                        });
                    }}
                  >
                    
                  </Button>
                </TooltipTrigger>
              </Tooltip>
            </TooltipProvider>
          
        </div>
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
        {fieldName === "sse_endpoint" && formData.kind === "google-workspace" && (
          <div className="mt-3 p-4 bg-primary/5 border border-primary/20 rounded-md space-y-3">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
              <p className="text-sm text-foreground font-medium">
                Need help setting up a Google Workspace MCP server? Follow below steps
              </p>
            </div>

            {/* Step 1: Google Client Setup */}
            <div className="border border-gray-700 rounded-md overflow-hidden">
              <button
                type="button"
                onClick={() => toggleStep(0)}
                className="w-full flex items-center justify-between p-3 bg-background-dark hover:bg-background-dark/80 transition-colors"
              >
                <span className="text-sm font-medium text-foreground">
                  Step 1: Google Client Setup
                </span>
                {expandedStep === 0 ? (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                )}
              </button>
              {expandedStep === 0 && (
                <div className="p-3 bg-background-card border-t border-gray-700 space-y-4">
                  {/* Create Google Cloud Project */}
                  <div>
                    <h4 className="text-sm font-semibold text-foreground mb-2">✅ Create a Google Cloud Project</h4>
                    <ol className="text-sm text-muted-foreground space-y-1.5 list-decimal list-inside">
                      <li>Go to: <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">https://console.cloud.google.com/</a></li>
                      <li>Click <strong>Create Project</strong></li>
                      <li>Note your:
                        <ul className="ml-6 mt-1 list-disc list-inside">
                          <li><strong>Project Name</strong></li>
                          <li><strong>Project Location</strong> (default is fine)</li>
                        </ul>
                      </li>
                    </ol>
                  </div>

                  {/* Configure OAuth Credentials */}
                  <div>
                    <h4 className="text-sm font-semibold text-foreground mb-2">🔑 Configure OAuth Credentials</h4>
                    <ol className="text-sm text-muted-foreground space-y-1.5 list-decimal list-inside">
                      <li>Go to: <strong>APIs & Services → Credentials</strong></li>
                      <li>Click: <strong>Create Credentials → OAuth Client ID</strong></li>
                      <li>Select <strong>Web Application</strong></li>
                      <li>Set the following:
                        <div className="mt-2 ml-6 text-xs">
                          <div className="bg-background-dark p-2 rounded space-y-1">
                            <div><strong>Authorized JavaScript origins:</strong> <code className="text-primary">http://localhost:8000</code></div>
                            <div><strong>Authorized redirect URIs:</strong> <code className="text-primary">http://localhost:8000/oauth2callback</code></div>
                          </div>
                        </div>
                      </li>
                      <li className="mt-2">Click <strong>Create</strong></li>
                      <li><strong>Download the OAuth JSON file</strong></li>
                    </ol>
                  </div>

                  {/* Enable Required APIs */}
                  <div>
                    <h4 className="text-sm font-semibold text-foreground mb-2">📌 Enable Required Google APIs</h4>
                    <p className="text-sm text-muted-foreground">
                      Navigate to: <strong>APIs & Services → Library</strong> and enable the required APIs 
                      (Calendar, Drive, Gmail, Docs, Sheets, Slides, Forms, Tasks, Chat, Search)
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Step 2: Download & Run Script */}
            <div className="border border-gray-700 rounded-md overflow-hidden">
              <button
                type="button"
                onClick={() => toggleStep(1)}
                className="w-full flex items-center justify-between p-3 bg-background-dark hover:bg-background-dark/80 transition-colors"
              >
                <span className="text-sm font-medium text-foreground">
                  Step 2: Download & Run the Script
                </span>
                {expandedStep === 1 ? (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                )}
              </button>
              {expandedStep === 1 && (
                <div className="p-3 bg-background-card border-t border-gray-700 space-y-4">
                  {/* Extract OAuth Credentials */}
                  <div>
                    <h4 className="text-sm font-semibold text-foreground mb-2">📋 Extract OAuth Credentials</h4>
                    <p className="text-sm text-muted-foreground mb-2">Open the OAuth JSON file downloaded in Step 1 and extract:</p>
                    <ul className="text-sm text-muted-foreground space-y-1 ml-6 list-disc list-inside">
                      <li><strong>client_id</strong>: Found in the JSON under <code className="px-1 py-0.5 bg-background-dark rounded">web.client_id</code></li>
                      <li><strong>client_secret</strong>: Found in the JSON under <code className="px-1 py-0.5 bg-background-dark rounded">web.client_secret</code></li>
                      <li><strong>user_email</strong>: Your Google account email address</li>
                    </ul>
                  </div>

                  {/* Download & Run Setup Script */}
                  <div>
                    <h4 className="text-sm font-semibold text-foreground mb-2">💻 Download & Run Setup Script</h4>
                    <p className="text-sm text-muted-foreground mb-2"><strong>Prerequisites:</strong> Ensure Docker (or Podman) and Docker Compose are installed</p>
                    
                    <button
                      type="button"
                      onClick={() => {
                        const scriptPath = "/guides/local_mcp.sh";
                        fetch(scriptPath)
                          .then((response) => {
                            if (!response.ok) {
                              throw new Error(`File not found: ${response.status}`);
                            }
                            return response.text();
                          })
                          .then((scriptContent) => {
                            // Download as .txt to avoid browser blocking
                            const blob = new Blob([scriptContent], { type: "text/plain" });
                            const url = window.URL.createObjectURL(blob);
                            const link = document.createElement("a");
                            link.href = url;
                            link.download = "local_mcp.txt";
                            link.style.display = "none";
                            document.body.appendChild(link);
                            link.click();
                            
                            setTimeout(() => {
                              document.body.removeChild(link);
                              window.URL.revokeObjectURL(url);
                            }, 100);
                          })
                          .catch((error) => {
                            console.error("Download failed:", error);
                          });
                      }}
                      className="mb-2 px-3 py-1.5 text-sm bg-primary hover:bg-primary/80 text-white rounded"
                    >
                      Download local_mcp.txt
                    </button>

                    <p className="text-sm text-muted-foreground mb-1">After downloading, rename, provide the <b>client id </b>, <b>client secret</b> and <b>user email</b> and run the script:</p>
                    <div className="relative bg-background-dark p-2 rounded mb-2">
                      <button
                        type="button"
                        onClick={copyCommandToClipboard}
                        className="absolute top-2 right-2 p-1.5 rounded hover:bg-gray-700 transition-colors"
                        title="Copy command"
                      >
                        {commandCopied ? (
                          <Check className="w-4 h-4 text-green-400" />
                        ) : (
                          <Copy className="w-4 h-4 text-gray-400" />
                        )}
                      </button>
                      <code className="text-xs text-primary">
                        cd ~/Downloads<br />
                        mv local_mcp.txt local_mcp.sh<br />
                        chmod +x local_mcp.sh<br />
                        ./local_mcp.sh \<br />
                        &nbsp;&nbsp;--client_id "YOUR_CLIENT_ID" \<br />
                        &nbsp;&nbsp;--client_secret "YOUR_CLIENT_SECRET" \<br />
                        &nbsp;&nbsp;--user_email "your-email@example.com"
                      </code>
                    </div>
                    <p className="text-sm text-muted-foreground">The script will automatically clone the repository, configure the environment, and start the MCP server.</p>
                  </div>

                  {/* Connect to UniFAI */}
                  <div>
                    <h4 className="text-sm font-semibold text-foreground mb-2">🔗 Connect UniFAI to Your Local MCP Server</h4>
                    <p className="text-sm text-muted-foreground mb-2">
                      After the script completes successfully, you'll need to provide your machine's public IP address.
                    </p>
                    <ol className="text-sm text-muted-foreground space-y-1.5 list-decimal list-inside">
                      <li>The SSE endpoint format is: <code className="px-1 py-0.5 bg-background-dark rounded text-primary">http://YOUR_PUBLIC_IP:8000/mcp</code></li>
                      <li>Replace <code className="px-1 py-0.5 bg-background-dark rounded">YOUR_PUBLIC_IP</code> with your machine's actual IP address</li>
                      <li>Enter the complete SSE endpoint URL in the field above, and wait for the validation to complete</li>
                      <li>Click <strong>Save</strong> to complete the setup</li>
                    </ol>
                  </div>
                </div>
              )}
            </div>
          </div>
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
            .filter(([fieldName, fieldSchema]) => {
              // Always exclude category and type (handled by GUI)
              if (['category', 'type'].includes(fieldName)) {
                return false;
              }

              // Filter out hidden fields - check if field has hints.hidden.hint_type === "hidden"
              if (fieldSchema?.hints?.hidden?.hint_type === "hidden") {
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
            .map(([fieldName, fieldSchema]) => {
              return renderFormField(fieldName, fieldSchema);
            })}

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