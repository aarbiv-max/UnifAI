import { platformApi } from '@/http/platformClient';

// ─────────────────────────────────────────────────────────────────────────────
//  Types
// ─────────────────────────────────────────────────────────────────────────────

export interface FieldValue {
  key: string;
  label: string;
  field_type: string;
  description: string;
  default: unknown;
  placeholder: string;
  value: unknown;
}

export interface SectionValue {
  key: string;
  title: string;
  description: string;
  fields: FieldValue[];
  on_update_action: string | null;
  updated_at: string | null;
}

export interface CategoryValue {
  key: string;
  title: string;
  description: string;
  sections: SectionValue[];
}

export interface AdminConfigResponse {
  categories: CategoryValue[];
}

export interface UpdateSectionResponse {
  status: string;
  on_update_action: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
//  API calls
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fetch the full admin config template merged with stored values.
 */
export async function getAdminConfig(): Promise<AdminConfigResponse> {
  const response = await platformApi.get('/admin-config/config.get');
  return response.data;
}

/**
 * Update a single config section's values.
 */
export async function updateAdminConfigSection(
  sectionKey: string,
  values: Record<string, unknown>,
): Promise<UpdateSectionResponse> {
  const response = await platformApi.put('/admin-config/config.section.update', {
    sectionKey,
    values,
  });
  return response.data;
}
