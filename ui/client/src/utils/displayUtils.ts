/**
 * Shared display utilities for formatting config values and objects for UI display.
 * Used by ElementData, ElementGrid, and ResourceDetailsModal.
 * 
 * DISPLAY OBJECT PROTOCOL:
 * Objects that should be simplified for display must include a `_display` field
 * containing the display string value. This is the explicit marker that identifies
 * a display object. Example: { id: "abc123", name: "My Doc", _display: "My Doc" }
 * 
 * For backwards compatibility, we also support objects with common display patterns
 * (name+id, label+value) but the _display field takes priority.
 */

/**
 * Check if an object is marked as a display object.
 * A display object has an explicit `_display` field OR follows known display patterns.
 */
export const isDisplayObject = (obj: any): boolean => {
  if (!obj || typeof obj !== 'object') return false;
  
  // Explicit marker - preferred method
  if ('_display' in obj) return true;
  
  // Backwards compatibility: known display patterns
  // These should be phased out in favor of _display marker
  const hasLegacyPattern = ('name' in obj && ('id' in obj || 'value' in obj)) ||
                           ('label' in obj && 'value' in obj);
  return hasLegacyPattern;
};

/**
 * Extract display value from an object.
 * Uses explicit _display field if present, otherwise checks common display field names.
 */
export const getDisplayValue = (obj: any): string => {
  if (!obj || typeof obj !== 'object') return String(obj || '');
  
  // Explicit _display marker takes priority (preferred protocol)
  if (obj._display != null) return String(obj._display);
  
  // Backwards compatibility: common display field names in priority order
  // TODO: Consider deprecating these fallbacks once all BE responses use _display
  const displayFields = ['name', 'label', 'title', 'display', 'text'];
  for (const field of displayFields) {
    if (obj[field] != null) return String(obj[field]);
  }
  
  // Fallback to id/value
  if (obj.id != null) return String(obj.id);
  if (obj.value != null) return String(obj.value);
  
  return '[Unknown]';
};

/**
 * Extract display value from an item, with optional fallback function for strings.
 * Used for arrays that may contain strings (refs) or objects.
 */
export const getDisplayValueFromItem = (
  item: any, 
  fallbackFn?: (ref: string | any) => string
): string => {
  if (!item) return '';
  
  // If it's a string, use the fallback function if provided
  if (typeof item === 'string') {
    return fallbackFn ? fallbackFn(item) : item;
  }
  
  // If it's an object, extract display value
  if (typeof item === 'object' && item !== null) {
    // Explicit _display marker takes priority (preferred protocol)
    if (item._display != null) return String(item._display);
    
    // Backwards compatibility: common display field patterns
    const displayFields = ['name', 'label', 'title', 'display', 'text'];
    for (const field of displayFields) {
      if (item[field] != null) return String(item[field]);
    }
    // Fallback to id/value
    if (item.id != null) return String(item.id);
    if (item.value != null) return String(item.value);
    
    // If object has $ref, use fallback function
    if (item.$ref && fallbackFn) return fallbackFn(item);
  }
  
  return String(item);
};

/**
 * Recursively simplify config objects for display.
 * Converts display objects (marked with _display or having display patterns) to just display names.
 * 
 * NOTE: This function uses isDisplayObject() to determine what should be simplified.
 * Objects with explicit _display field OR legacy patterns (name+id, label+value) are simplified.
 */
export const simplifyConfigForDisplay = (config: any): any => {
  if (!config || typeof config !== 'object') return config;
  
  if (Array.isArray(config)) {
    return config.map(item => {
      if (typeof item === 'object' && item !== null) {
        // Check if this is a display object using the protocol
        if (isDisplayObject(item)) {
          return getDisplayValue(item);
        }
      }
      return simplifyConfigForDisplay(item);
    });
  }
  
  // For objects, recursively simplify each property
  const result: any = {};
  for (const [key, value] of Object.entries(config)) {
    result[key] = simplifyConfigForDisplay(value);
  }
  return result;
};
