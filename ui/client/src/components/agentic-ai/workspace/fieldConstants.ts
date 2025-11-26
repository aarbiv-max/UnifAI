/**
 * Constants for field level definitions in resource schemas.
 * These define which fields are first-level, system fields, etc.
 */

/**
 * First-level fields from resource schema.
 * These are fields that exist at the top level of a resource, not in cfg_dict.
 */
export const FIRST_LEVEL_RESOURCE_FIELDS = ['name', 'category','type','cfg_dict', 'version', 'created', 'updated', 'nested_refs','rid','user_id'] as const;

/**
 * System fields that should never be included in save payload.
 * These are read-only or system-managed fields.
 */
export const SYSTEM_FIELDS = ['version', 'created', 'updated', 'nested_refs', 'rid', 'user_id', 'category', 'type', 'cfg_dict'] as const;

/**
 * First-level fields that are required and should be shown in forms.
 * Currently only 'name' is included as a first-level field for saving.
 */
export const FIRST_LEVEL_REQUIRED_FIELDS = ['name'] as const;

/**
 * Fields that should be excluded from form display (handled by GUI).
 */
export const GUI_MANAGED_FIELDS = ['category', 'type'] as const;

/**
 * Check if a field is a first-level field
 */
export const isFirstLevelField = (fieldName: string): boolean => {
  return FIRST_LEVEL_REQUIRED_FIELDS.includes(fieldName as any);
};

/**
 * Check if a field is a system field
 */
export const isSystemField = (fieldName: string): boolean => {
  return SYSTEM_FIELDS.includes(fieldName as any);
};

/**
 * Check if a field is a GUI-managed field
 */
export const isGuiManagedField = (fieldName: string): boolean => {
  return GUI_MANAGED_FIELDS.includes(fieldName as any);
};

/**
 * Check if a field is a cfg_dict field (not first-level or system)
 */
export const isCfgDictField = (fieldName: string): boolean => {
  return !FIRST_LEVEL_RESOURCE_FIELDS.includes(fieldName as any);
};

