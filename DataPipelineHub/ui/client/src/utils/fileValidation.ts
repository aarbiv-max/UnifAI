/**
 * File validation utilities for upload operations
 */

export const MAX_FILE_SIZE_MB = 50;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024; // 50 MB in bytes

export interface FileValidationResult {
  validFiles: File[];
  invalidFiles: string[];
  sizeErrors: string[];
}

/**
 * Validates files for extension and size
 */
export function validateFiles(
  files: FileList,
  isFileExtensionSupported: (fileName: string) => boolean
): FileValidationResult {
  const validFiles: File[] = [];
  const invalidFiles: string[] = [];
  const sizeErrors: string[] = [];
  
  Array.from(files).forEach(file => {
    // Check file extension
    if (!isFileExtensionSupported(file.name)) {
      invalidFiles.push(file.name);
      return;
    }
    
    // Check file size
    if (file.size > MAX_FILE_SIZE_BYTES) {
      const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
      sizeErrors.push(`${file.name} (${fileSizeMB} MB)`);
      return;
    }
    
    validFiles.push(file);
  });
  
  return { validFiles, invalidFiles, sizeErrors };
}

/**
 * Formats file size error messages
 */
export function formatFileSizeErrors(sizeErrors: string[]): string {
  if (sizeErrors.length === 0) return "";
  return `The following files exceed the maximum size of ${MAX_FILE_SIZE_MB} MB: ${sizeErrors.join(', ')}. These files will be ignored.`;
}

/**
 * Formats file extension error messages
 */
export function formatExtensionErrors(invalidFiles: string[]): string {
  if (invalidFiles.length === 0) return "";
  const invalidExtensions = Array.from(new Set(invalidFiles.map(file => 
    file.substring(file.lastIndexOf('.')).toLowerCase()
  )));
  return `The following file extensions are not supported: ${invalidExtensions.join(', ')}. These files will be ignored.`;
}

