/**
 * Utility functions for checking JSON Schema field types.
 * These functions help determine the type of a field schema, handling
 * various schema patterns like anyOf, oneOf, allOf, etc.
 */

/**
 * Get the primary type of a field schema.
 * Handles direct type, anyOf, oneOf, and allOf patterns.
 */
export const getFieldType = (fieldSchema: any): string | null => {
  if (!fieldSchema || typeof fieldSchema !== 'object') {
    return null;
  }

  // Direct type
  if (fieldSchema.type) {
    return fieldSchema.type;
  }

  // Check anyOf - use the first type found
  if (fieldSchema.anyOf && Array.isArray(fieldSchema.anyOf)) {
    for (const option of fieldSchema.anyOf) {
      if (option.type) {
        return option.type;
      }
    }
  }

  // Check oneOf - use the first type found
  if (fieldSchema.oneOf && Array.isArray(fieldSchema.oneOf)) {
    for (const option of fieldSchema.oneOf) {
      if (option.type) {
        return option.type;
      }
    }
  }

  // Check allOf - use the first type found
  if (fieldSchema.allOf && Array.isArray(fieldSchema.allOf)) {
    for (const option of fieldSchema.allOf) {
      if (option.type) {
        return option.type;
      }
    }
  }

  return null;
};

/**
 * Check if a field is of a specific type (handles anyOf, oneOf, allOf)
 */
export const isFieldType = (fieldSchema: any, type: string): boolean => {
  const fieldType = getFieldType(fieldSchema);
  return fieldType === type;
};

/**
 * Check if a field has anyOf with specific type
 */
export const hasAnyOfType = (fieldSchema: any, type: string): boolean => {
  if (!fieldSchema.anyOf || !Array.isArray(fieldSchema.anyOf)) {
    return false;
  }
  return fieldSchema.anyOf.some((option: any) => option.type === type);
};

/**
 * Check if a field is a long text field (based on field name patterns)
 */
export const isLongTextField = (fieldName: string): boolean => {
  const longTextPatterns = ['message', 'prompt', 'description'];
  return longTextPatterns.some(pattern => fieldName.includes(pattern));
};

/**
 * Check if a field is hidden (has hints.hidden.hint_type === "hidden")
 */
export const isHiddenField = (fieldSchema: any): boolean => {
  return fieldSchema?.hints?.hidden?.hint_type === "hidden";
};

/**
 * Check if a field is a secret field (has hints.secret.hint_type === "secret")
 */
export const isSecretField = (fieldSchema: any): boolean => {
  return fieldSchema?.hints?.secret?.hint_type === "secret";
};

/**
 * Get hint from field schema
 */
export const getHint = (fieldSchema: any, fieldName: any): any | null => {
  return fieldSchema?.hints?.action?.hint_type === fieldName
    ? fieldSchema.hints.action 
    : null;
};

/**
 * Get default value for a field based on its schema type.
 * Respects the schema's default property if present, otherwise returns type-appropriate defaults.
 */
export const getDefaultValue = (fieldSchema: any): any => {
  // If schema has an explicit default, use it
  if (fieldSchema?.default !== undefined) {
    return fieldSchema.default;
  }

  // Determine default based on field type
  const fieldType = getFieldType(fieldSchema);
  
  switch (fieldType) {
    case 'array':
      return [];
    case 'boolean':
      return false;
    case 'object':
      return {};
    case 'number':
    case 'integer':
      return null; // Numbers should be null initially, not 0
    case 'string':
      return "";
    case 'null':
      return null;
    default:
      // For unknown types or no type, default to empty string
      // This handles cases where type might be undefined or in anyOf/oneOf/allOf
      return "";
  }
};


