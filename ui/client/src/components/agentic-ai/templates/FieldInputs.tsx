import React, { useState, useCallback, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { 
  X, 
  Plus, 
  Key, 
  Eye, 
  EyeOff,
  AlertCircle,
  Globe,
  Loader2,
  CheckCircle,
  Lock,
  XCircle,
} from 'lucide-react';
import { NormalizedField, TemplateFormData } from '@/types/templates';
import { getFieldDisplayType } from '@/utils/templateHelpers';
import { AuthFieldRenderer } from '@/components/agentic-ai/workspace/AuthFieldRenderer';
import { executeAction } from '@/api/actions';
import { useAuth } from '@/contexts/AuthContext';

type ValidateStatus = 'idle' | 'checking' | 'connected' | 'auth_required' | 'unreachable' | 'error';

const ValidateFieldRenderer: React.FC<{
  field: NormalizedField;
  value: any;
  fullFormData: TemplateFormData;
}> = ({ field, value, fullFormData }) => {
  const { user } = useAuth();
  const userId = user?.username || '';
  const [status, setStatus] = useState<ValidateStatus>('idle');
  const [message, setMessage] = useState('');

  // Reset status whenever value or any mapped dependency value changes so a
  // stale result is never shown after the user edits an input.
  const depsDigest = field.validateHint
    ? Object.keys(field.validateHint.dependencies)
        .map((cf) => String(fullFormData[`${field.category}.${field.resourceRid}.${cf}`] ?? ''))
        .join('\x00')
    : '';
  useEffect(() => {
    setStatus('idle');
    setMessage('');
  }, [value, depsDigest]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleValidate = useCallback(async () => {
    if (!field.validateHint || !value) return;
    setStatus('checking');

    const { action_uid, dependencies } = field.validateHint;
    const prefix = `${field.category}.${field.resourceRid}.`;
    const inputData: Record<string, any> = {};

    // Populate all mapped dependency fields from the current form state.
    // The dependency map fully specifies config-field → action-input-field,
    // so no additional fallbacks are needed.
    Object.entries(dependencies).forEach(([configField, actionField]) => {
      const val = fullFormData[`${prefix}${configField}`];
      if (val !== undefined && val !== null) {
        inputData[actionField as string] = val;
      }
    });

    try {
      const data = await executeAction(action_uid, inputData, userId);

      if (data.is_reachable && !data.auth_required) {
        setStatus('connected');
        setMessage(data.message || 'Connection successful');
      } else if (data.auth_required) {
        setStatus('auth_required');
        setMessage(data.message || 'Authentication required — use the Sign In field below');
      } else if (data.is_reachable === false) {
        setStatus('unreachable');
        setMessage(data.message || 'Server not reachable');
      } else {
        setStatus('error');
        setMessage(data.message || 'Validation failed');
      }
    } catch {
      setStatus('error');
      setMessage('Failed to reach validation service');
    }
  }, [field, value, fullFormData, userId]);

  const statusColor =
    status === 'connected' ? 'text-green-400' :
    status === 'auth_required' ? 'text-yellow-400' :
    status === 'checking' ? 'text-blue-400' :
    'text-red-400';

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="flex-1 flex items-center gap-2 px-3 py-2 bg-background-dark border border-gray-700 rounded-md overflow-hidden">
          <Globe className="h-4 w-4 text-gray-500 shrink-0" />
          <span className="text-sm text-gray-400 font-mono truncate">{value || 'URL not configured'}</span>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleValidate}
          disabled={status === 'checking' || !value}
          className="border-gray-700 shrink-0"
        >
          {status === 'checking' ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Validate'}
        </Button>
      </div>
      {status !== 'idle' && (
        <div className={`flex items-center gap-2 text-xs ${statusColor}`}>
          {status === 'checking' && <Loader2 className="h-3 w-3 animate-spin" />}
          {status === 'connected' && <CheckCircle className="h-3 w-3" />}
          {status === 'auth_required' && <Lock className="h-3 w-3" />}
          {(status === 'unreachable' || status === 'error') && <XCircle className="h-3 w-3" />}
          <span>{status === 'checking' ? 'Validating connection...' : message}</span>
        </div>
      )}
    </div>
  );
};

function buildResourceConfigSliceForAuth(
  field: NormalizedField,
  fullFormData: TemplateFormData,
): Record<string, unknown> {
  const prefix = `${field.category}.${field.resourceRid}.`;
  const slice: Record<string, unknown> = {};
  const depKeys = field.authHint?.dependencies
    ? Object.keys(field.authHint.dependencies)
    : [];
  for (const configKey of depKeys) {
    slice[configKey] = fullFormData[`${prefix}${configKey}`];
  }
  return slice;
}

interface FieldInputProps {
  field: NormalizedField;
  value: any;
  onChange: (value: any) => void;
  error?: string;
  compact?: boolean;
  /** Full template form; required for auth / MCP sign-in fields */
  fullFormData?: TemplateFormData;
  onAuthValidationChange?: (fieldKey: string, valid: boolean) => void;
}

export const StringArrayInput: React.FC<{
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
}> = ({ value = [], onChange, placeholder }) => {
  const [inputValue, setInputValue] = useState('');

  const handleAdd = () => {
    if (inputValue.trim() && !value.includes(inputValue.trim())) {
      onChange([...value, inputValue.trim()]);
      setInputValue('');
    }
  };

  const handleRemove = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || 'Add item...'}
          className="bg-background-dark border-gray-700"
        />
        <Button 
          type="button" 
          onClick={handleAdd}
          variant="outline"
          size="sm"
          className="border-gray-700 shrink-0"
          aria-label="Add item"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {value.map((item, index) => (
            <Badge 
              key={index} 
              variant="secondary"
              className="bg-primary/20 text-primary border-primary/30 flex items-center gap-1"
            >
              {item}
              <button
                type="button"
                onClick={() => handleRemove(index)}
                className="ml-1 hover:text-red-400"
                aria-label={`Remove ${item}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
};

export const SecretInput: React.FC<{
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}> = ({ value, onChange, placeholder }) => {
  const [showSecret, setShowSecret] = useState(false);

  return (
    <div className="relative">
      <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-yellow-500" />
      <Input
        type={showSecret ? 'text' : 'password'}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pl-10 pr-10 bg-background-dark border-gray-700 font-mono"
      />
      <button
        type="button"
        onClick={() => setShowSecret(!showSecret)}
        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
        aria-label={showSecret ? 'Hide secret' : 'Show secret'}
        aria-pressed={showSecret}
      >
        {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
};

export const FieldInput: React.FC<FieldInputProps> = ({
  field,
  value,
  onChange,
  error,
  compact = false,
  fullFormData,
  onAuthValidationChange,
}) => {
  const renderInput = () => {
    switch (field.type) {
      case 'validate':
        return (
          <ValidateFieldRenderer
            field={field}
            value={value}
            fullFormData={fullFormData || {}}
          />
        );

      case 'auth':
        if (!field.authHint || !fullFormData || !onAuthValidationChange) {
          return (
            <p className="text-xs text-amber-500">
              Sign-in could not be loaded. Refresh the template detail and try again.
            </p>
          );
        }
        return (
          <AuthFieldRenderer
            fieldName={field.key}
            fieldSchema={{
              hints: { auth: field.authHint },
              description: field.description || field.label,
            }}
            formData={buildResourceConfigSliceForAuth(field, fullFormData)}
            elementActions={[]}
            onValidationChange={onAuthValidationChange}
            onInputChange={() => {}}
          />
        );

      case 'object':
        return (
          <Textarea
            value={typeof value === 'object' ? JSON.stringify(value ?? {}, null, 2) : (value || '{}')}
            onChange={(e) => {
              try {
                onChange(JSON.parse(e.target.value));
              } catch {
                // Keep raw string while the user is mid-edit
                onChange(e.target.value);
              }
            }}
            placeholder='{}'
            className="bg-background-dark border-gray-700 font-mono text-sm"
            rows={4}
          />
        );

      case 'secret':
        return (
          <SecretInput
            value={value}
            onChange={onChange}
            placeholder={`Enter ${field.label.toLowerCase()}`}
          />
        );
      
      case 'array':
        return (
          <StringArrayInput
            value={value || []}
            onChange={onChange}
            placeholder={`Add ${field.label.toLowerCase()}...`}
          />
        );
      
      case 'boolean':
        return (
          <div className="flex items-center space-x-2">
            <Checkbox
              id={field.key}
              checked={value || false}
              onCheckedChange={onChange}
            />
            <label 
              htmlFor={field.key}
              className="text-sm text-gray-400 cursor-pointer"
            >
              {field.description || 'Enable this option'}
            </label>
          </div>
        );
      
      case 'enum':
        return (
          <Select value={value || field.default || ''} onValueChange={onChange}>
            <SelectTrigger className="bg-background-dark border-gray-700">
              <SelectValue placeholder={`Select ${field.label}`} />
            </SelectTrigger>
            <SelectContent>
              {field.enumOptions?.map((option) => (
                <SelectItem key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      
      case 'number':
        return (
          <Input
            type="number"
            value={value ?? ''}
            onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
            placeholder={`Enter ${field.label.toLowerCase()}`}
            className="bg-background-dark border-gray-700"
            min={field.minimum}
            max={field.maximum}
          />
        );
      
      default:
        // String type - use Textarea for multiline fields
        if (field.isMultiline) {
          return (
            <Textarea
              value={value || ''}
              onChange={(e) => onChange(e.target.value)}
              placeholder={`Enter ${field.label.toLowerCase()}`}
              className="bg-background-dark border-gray-700"
              rows={4}
            />
          );
        }
        return (
          <Input
            type="text"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={`Enter ${field.label.toLowerCase()}`}
            className="bg-background-dark border-gray-700"
          />
        );
    }
  };

  return (
    <div className="space-y-2">
      {field.type !== 'boolean' && field.type !== 'auth' && field.type !== 'validate' && !compact && (
        <div className="flex items-center justify-between">
          <Label htmlFor={field.key} className="text-sm font-medium">
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </Label>
          <Badge variant="outline" className="text-xs px-1.5 py-0">
            {getFieldDisplayType(field)}
          </Badge>
        </div>
      )}
      {renderInput()}
      {field.description && field.type !== 'boolean' && field.type !== 'auth' && field.type !== 'validate' && !compact && (
        <p className="text-xs text-gray-500">{field.description}</p>
      )}
      {error && (
        <p className="text-xs text-red-500 flex items-center gap-1">
          <AlertCircle className="h-3 w-3" />
          {error}
        </p>
      )}
    </div>
  );
};

export default FieldInput;
