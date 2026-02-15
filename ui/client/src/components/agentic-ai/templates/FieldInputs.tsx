import React, { useState } from 'react';
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
  AlertCircle
} from 'lucide-react';
import { NormalizedField } from '@/types/templates';
import { getFieldDisplayType } from '@/utils/templateHelpers';

interface FieldInputProps {
  field: NormalizedField;
  value: any;
  onChange: (value: any) => void;
  error?: string;
  compact?: boolean;
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

export const FieldInput: React.FC<FieldInputProps> = ({ field, value, onChange, error, compact = false }) => {
  const renderInput = () => {
    switch (field.type) {
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
      {field.type !== 'boolean' && !compact && (
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
      {field.description && field.type !== 'boolean' && !compact && (
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
