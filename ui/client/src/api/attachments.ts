import axios from '@/http/axiosAgentConfig';

export interface AttachmentContent {
  filename: string;
  extension: string;
  text_content: string;
  char_count: number;
}

export interface AttachmentUploadResponse {
  attachments: AttachmentContent[];
}

export interface AttachmentValidationError {
  file_name: string;
  error_type: 'extension' | 'size';
  message: string;
}

export interface SupportedTypesResponse {
  allowed_extensions: string[];
  max_file_size_bytes: number;
  max_file_size_mb: number;
}

/**
 * Upload files and extract text content for prompt attachment.
 * Files are base64-encoded and sent to the backend for processing.
 */
export async function uploadAndProcessAttachments(
  files: { name: string; content: string }[]
): Promise<AttachmentUploadResponse> {
  const response = await axios.post<AttachmentUploadResponse>(
    '/attachments/upload-and-process',
    { files }
  );
  return response.data;
}

/**
 * Get supported file types for prompt attachments.
 */
export async function getAttachmentSupportedTypes(): Promise<SupportedTypesResponse> {
  const response = await axios.get<SupportedTypesResponse>(
    '/attachments/supported-types'
  );
  return response.data;
}

export const ATTACHMENT_ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.md'];
export const ATTACHMENT_MAX_FILE_SIZE_MB = 10;
export const ATTACHMENT_MAX_FILE_SIZE_BYTES = ATTACHMENT_MAX_FILE_SIZE_MB * 1024 * 1024;

/**
 * Client-side validation of files before upload.
 */
export function validateAttachmentFiles(
  files: File[]
): { valid: File[]; errors: AttachmentValidationError[] } {
  const valid: File[] = [];
  const errors: AttachmentValidationError[] = [];

  for (const file of files) {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();

    if (!ATTACHMENT_ALLOWED_EXTENSIONS.includes(ext)) {
      errors.push({
        file_name: file.name,
        error_type: 'extension',
        message: `Unsupported file type "${ext}". Allowed: ${ATTACHMENT_ALLOWED_EXTENSIONS.join(', ')}`,
      });
    } else if (file.size > ATTACHMENT_MAX_FILE_SIZE_BYTES) {
      errors.push({
        file_name: file.name,
        error_type: 'size',
        message: `File exceeds maximum size of ${ATTACHMENT_MAX_FILE_SIZE_MB} MB`,
      });
    } else {
      valid.push(file);
    }
  }

  return { valid, errors };
}

/**
 * Convert a File to base64 data URL string.
 */
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
