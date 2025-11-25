/**
 * Schema helper functions for handling JSON Schema $ref resolution
 * and category extraction from field schemas.
 */


/**
 * Parse JSON path from a reference string (e.g., "#/definitions/Resource" -> ["definitions", "Resource"])
 */
export const parseJsonPath = (ref: string): string[] | null => {
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

/**
 * Generic helper function to resolve JSON path in an object
 */
export const resolveJsonPath = (obj: any, pathSegments: string[]): any | null => {
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

/**
 * Find definition in schema by reference path
 */
export const findDefinitionByRef = (ref: string, configSchema: any): any | null => {
  const pathSegments = parseJsonPath(ref);
  if (!pathSegments || !configSchema) {
    return null;
  }

  return resolveJsonPath(configSchema, pathSegments);
};

/**
 * Resolve $ref to actual definition with full details
 */
export const resolveRef = (ref: string, configSchema: any): any | null => {
  const definition = findDefinitionByRef(ref, configSchema);
  if (definition) {
    console.log(`Resolved $ref ${ref} to:`, definition);
    return definition;
  }

  console.warn(`Could not resolve $ref: ${ref}`);
  return null;
};

/**
 * Extract category from resolved definition
 */
export const extractCategoryFromDefinition = (definition: any): string | null => {
  if (!definition || typeof definition !== 'object') {
    return null;
  }

  // Direct category property
  if (definition.category && typeof definition.category === 'string') {
    return definition.category;
  }

  return null;
};

/**
 * Extract category from $ref field or anyOf structure
 */
export const extractCategoryFromField = (fieldSchema: any, configSchema: any): string | null => {
  // Handle direct $ref by resolving it
  if (fieldSchema.$ref) {
    const resolved = resolveRef(fieldSchema.$ref, configSchema);
    const category = extractCategoryFromDefinition(resolved);
    if (category) {
      return category;
    }
  }

  // Handle items with $ref (for arrays)
  if (fieldSchema.items && fieldSchema.items.$ref) {
    const resolved = resolveRef(fieldSchema.items.$ref, configSchema);
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
        const resolved = resolveRef(option.$ref, configSchema);
        const category = extractCategoryFromDefinition(resolved);
        if (category) {
          return category;
        }
      }

      // Check for array with $ref items in anyOf
      if (option.type === "array" && option.items && option.items.$ref) {
        const resolved = resolveRef(option.items.$ref, configSchema);
        const category = extractCategoryFromDefinition(resolved);
        if (category) {
          return category;
        }
      }
    }
  }
  return null; // Return null if no category is found
};

/**
 * Check if a field is an array with $ref items
 */
export const isArrayWithRefItems = (fieldSchema: any): boolean => {
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

/**
 * Get array items schema from anyOf or direct structure
 */
export const getArrayItemsSchema = (fieldSchema: any): any => {
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

/**
 * Check if a field has a $ref (direct or in anyOf)
 */
export const hasRefField = (fieldSchema: any): boolean => {
  return !!(
    fieldSchema.$ref ||
    (fieldSchema.items && fieldSchema.items.$ref) ||
    (fieldSchema.anyOf && fieldSchema.anyOf.some((option: any) => option.$ref))
  );
};

/**
 * Get all reference fields from a schema
 */
export const getRefFields = (properties: Record<string, any>): Array<[string, any]> => {
  return Object.entries(properties).filter(
    ([, property]: [string, any]) =>
      property.$ref ||
      (property.items && property.items.$ref) ||
      (property.type === "array" &&
        property.items &&
        property.items.$ref) ||
      isArrayWithRefItems(property) ||
      (property.anyOf && property.anyOf.some((option: any) => option.$ref)),
  );
};

/**
 * Extract all unique categories from reference fields
 */
export const extractRefCategories = (
  properties: Record<string, any>,
  configSchema: any
): Set<string> => {
  const refFields = getRefFields(properties);
  const categories = new Set<string>();
  
  refFields.forEach(([, property]: [string, any]) => {
    const category = extractCategoryFromField(property, configSchema);
    if (category) {
      categories.add(category);
    }
  });
  
  return categories;
};

