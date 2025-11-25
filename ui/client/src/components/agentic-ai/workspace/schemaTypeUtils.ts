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
 * Check if a field is an array type
 */
export const isArrayField = (fieldSchema: any): boolean => {
  return isFieldType(fieldSchema, 'array');
};

/**
 * Check if a field is an object type
 */
export const isObjectField = (fieldSchema: any): boolean => {
  return isFieldType(fieldSchema, 'object');
};

/**
 * Check if a field is a string type
 */
export const isStringField = (fieldSchema: any): boolean => {
  return isFieldType(fieldSchema, 'string');
};

/**
 * Check if a field is a number type (including integer)
 */
export const isNumberField = (fieldSchema: any): boolean => {
  const fieldType = getFieldType(fieldSchema);
  return fieldType === 'number' || fieldType === 'integer';
};

/**
 * Check if a field is a boolean type
 */
export const isBooleanField = (fieldSchema: any): boolean => {
  return isFieldType(fieldSchema, 'boolean');
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
 * Check if a field has anyOf with number or integer type
 */
export const hasAnyOfNumberType = (fieldSchema: any): boolean => {
  return hasAnyOfType(fieldSchema, 'number') || hasAnyOfType(fieldSchema, 'integer');
};

/**
 * Check if a field has anyOf with array type
 */
export const hasAnyOfArrayType = (fieldSchema: any): boolean => {
  return hasAnyOfType(fieldSchema, 'array');
};

/**
 * Check if a field has anyOf with string type
 */
export const hasAnyOfStringType = (fieldSchema: any): boolean => {
  return hasAnyOfType(fieldSchema, 'string');
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
 * Get validation hint from field schema
 */
export const getValidationHint = (fieldSchema: any): any | null => {
  return fieldSchema?.hints?.action?.hint_type === 'validate' 
    ? fieldSchema.hints.action 
    : null;
};

/**
 * Get populate hint from field schema
 */
export const getPopulateHint = (fieldSchema: any): any | null => {
  return fieldSchema?.hints?.action?.hint_type === 'populate' 
    ? fieldSchema.hints.action 
    : null;
};

