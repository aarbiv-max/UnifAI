// ────────────────────────────────────────────────────────────────────────────────
// Template List Types (from templates.list API)
// ────────────────────────────────────────────────────────────────────────────────

export interface TemplateListItem {
  template_id: string;
  name: string;
  description: string;
  author: string;
  category: string;
  tags: string[];
  version: string;
  output_capabilities: string[];
  placeholder_count: number;
}

export interface TemplatesListResponse {
  count: number;
  templates: TemplateListItem[];
}

// ────────────────────────────────────────────────────────────────────────────────
// Template Detail Types (from template.get API)
// ────────────────────────────────────────────────────────────────────────────────

export interface PlaceholderField {
  field_path: string;
  required: boolean;
  label: string;
  hint?: string;
}

export interface PlaceholderResource {
  rid: string;
  placeholders: PlaceholderField[];
}

export interface PlaceholderCategory {
  category: string;
  resources: PlaceholderResource[];
}

export interface TemplatePlaceholders {
  categories: PlaceholderCategory[];
}

export interface TemplateMetadata {
  author: string;
  tags: string[];
  version: string;
  category: string;
  output_capabilities: string[];
  is_public: boolean;
}

export interface TemplateDetail {
  template_id: string;
  draft: Record<string, any>;
  placeholders: TemplatePlaceholders;
  metadata: TemplateMetadata;
  created_at: string;
  updated_at: string;
}

// ────────────────────────────────────────────────────────────────────────────────
// Template Schema Types (from template.schema.get API - JSON Schema)
// ────────────────────────────────────────────────────────────────────────────────

export interface SchemaHintSecret {
  hint_type: 'secret';
  allow_reveal?: boolean;
  mask_char?: string;
  reason?: string;
}

export interface SchemaHintSelection {
  hint_type: 'selection';
  options?: string[];
}

export interface SchemaHintMultiline {
  hint_type: 'multiline';
  rows?: number;
}

export interface SchemaHintUrl {
  hint_type: 'url';
}

export type SchemaHint = SchemaHintSecret | SchemaHintSelection | SchemaHintMultiline | SchemaHintUrl;

export interface SchemaFieldProperty {
  type: string;
  title?: string;
  description?: string;
  default?: any;
  hints?: Record<string, SchemaHint>;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  minimum?: number;
  maximum?: number;
  enum?: string[];
  items?: { type: string };
  $ref?: string;
}

export interface SchemaDefinition {
  type: string;
  title?: string;
  description?: string;
  properties?: Record<string, SchemaFieldProperty>;
  required?: string[];
  $ref?: string;
}

export interface TemplateInputSchema {
  $defs: Record<string, SchemaDefinition>;
  properties: Record<string, SchemaFieldProperty>;
  required: string[];
  title: string;
  type: string;
}

// ────────────────────────────────────────────────────────────────────────────────
// Validation Types (from template.input.validate API)
// ────────────────────────────────────────────────────────────────────────────────

export interface ValidationError {
  field: string;
  message: string;
  type: string;
}

export interface ValidationResponse {
  is_valid: boolean;
  errors: ValidationError[];
}

// ────────────────────────────────────────────────────────────────────────────────
// Materialize Types (from template.materialize API)
// ────────────────────────────────────────────────────────────────────────────────

export interface MaterializeRequest {
  templateId: string;
  userId: string;
  input: Record<string, Record<string, Record<string, any>>>;
  blueprintName?: string;
  skipValidation?: boolean;
}

export interface MaterializeResponse {
  status: 'success' | 'error';
  blueprint_id: string;
  template_id: string;
  template_name: string;
  fields_filled: number;
  name: string;
  resource_ids: string[];
}

export interface MaterializeErrorResponse {
  error: string;
  errors?: Array<{
    rid: string;
    category: string;
    is_valid: boolean;
    messages: string[];
  }>;
}

// ────────────────────────────────────────────────────────────────────────────────
// UI Types (for component state management)
// ────────────────────────────────────────────────────────────────────────────────

export type InstantiationStatus = 
  | 'idle'
  | 'validating'
  | 'submitting'
  | 'completed'
  | 'failed';

/**
 * Normalized field representation for UI rendering
 * Derived from JSON Schema + placeholders
 */
export interface NormalizedField {
  // Path components for building input payload
  category: string;
  resourceRid: string;
  fieldPath: string;
  
  // Display properties
  key: string;  // Unique key: category.rid.field_path
  label: string;
  description?: string;
  type: 'string' | 'secret' | 'number' | 'boolean' | 'array' | 'enum';
  required: boolean;
  default?: any;
  
  // Validation
  pattern?: string;
  minLength?: number;
  maxLength?: number;
  minimum?: number;
  maximum?: number;
  enumOptions?: string[];
  
  // UI hints
  isSecret?: boolean;
  isMultiline?: boolean;
}

export interface TemplateFormData {
  [key: string]: any;
}

export interface TemplateCategory {
  name: string;
  count: number;
}
