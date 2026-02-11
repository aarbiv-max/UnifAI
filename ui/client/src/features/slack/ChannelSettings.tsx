import React, { useState } from 'react';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { X, Tag } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export interface ChannelSettingsData {
  dateRange: string;
  includeThreads: boolean;
  processFileContent: boolean;
  tags: string[];
}

export interface ChannelSettingsProps {
  channelId: string;
  channelName: string;
  settings: ChannelSettingsData;
  onSettingsChange: (channelId: string, settings: ChannelSettingsData) => void;
}

export const defaultChannelSettings: ChannelSettingsData = {
  dateRange: '180d',
  includeThreads: true,
  processFileContent: false,
  tags: [],
};

export function ChannelSettings({ 
  channelId, 
  channelName, 
  settings, 
  onSettingsChange 
}: ChannelSettingsProps) {
  const [tagInput, setTagInput] = useState('');

  const updateSetting = <K extends keyof ChannelSettingsData>(
    key: K, 
    value: ChannelSettingsData[K]
  ) => {
    onSettingsChange(channelId, { ...settings, [key]: value });
  };

  const handleAddTag = () => {
    const tag = tagInput.trim().toLowerCase();
    if (tag && !settings.tags.includes(tag)) {
      updateSetting('tags', [...settings.tags, tag]);
    }
    setTagInput('');
  };

  const handleRemoveTag = (tagToRemove: string) => {
    updateSetting('tags', settings.tags.filter(t => t !== tagToRemove));
  };

  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  return (
    <div className="bg-background-card border border-gray-800 rounded-lg p-4 space-y-4">
      <h4 className="font-medium text-sm text-foreground">
        Settings for{' '}
        <span className="inline-block px-3 py-1 bg-blue-500/20 border border-blue-500/40 rounded-md text-blue-400 font-bold text-base">
          #{channelName}
        </span>
      </h4>
      
      {/* Date Range */}
      <div>
        <Label htmlFor={`date-range-${channelId}`} className="text-sm">
          Date Range
        </Label>
        <Select 
          value={settings.dateRange} 
          onValueChange={(value) => updateSetting('dateRange', value)}
        >
          <SelectTrigger
            id={`date-range-${channelId}`}
            className="mt-1 bg-background-dark"
          >
            <SelectValue placeholder="Select date range" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7d">Last 7 days</SelectItem>
            <SelectItem value="30d">Last 30 days</SelectItem>
            <SelectItem value="90d">Last 90 days</SelectItem>
            <SelectItem value="180d">Last 6 months</SelectItem>
            <SelectItem value="365d">Last year</SelectItem>
            <SelectItem value="all">All time</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-gray-400 mt-1">
          How far back to fetch messages
        </p>
      </div>

      {/* Tags */}
      <div>
        <Label className="text-sm flex items-center gap-1.5">
          <Tag className="h-3.5 w-3.5" />
          Tags
        </Label>
        <p className="text-xs text-gray-400 mt-1 mb-2">
          Add tags to organize and filter this channel in retrievers
        </p>
        {settings.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {settings.tags.map(tag => (
              <Badge key={tag} variant="outline" className="text-xs px-2 py-0.5 gap-1">
                {tag}
                <X
                  className="h-3 w-3 cursor-pointer hover:text-destructive transition-colors"
                  onClick={() => handleRemoveTag(tag)}
                />
              </Badge>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <Input
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={handleTagKeyDown}
            placeholder="Type tag and press Enter..."
            className="text-sm dark:bg-zinc-800 dark:!text-white dark:border-zinc-700"
          />
        </div>
      </div>

      {/* Include Threads - Disabled for now */}
      <div className="flex items-center justify-between pt-1 opacity-50 cursor-not-allowed">
        <div>
          <div className="flex items-center space-x-2">
            <Label htmlFor={`include-threads-${channelId}`} className="text-base">
              Include Threads
            </Label>
            <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400 font-medium">
              Disabled
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Process conversation threads
          </p>
        </div>
        <Switch 
          id={`include-threads-${channelId}`} 
          checked={settings.includeThreads}
          disabled
        />
      </div>

      {/* Process File Content - Disabled for now */}
      <div className="flex items-start justify-between opacity-50 cursor-not-allowed">
        <div>
          <div className="flex items-center space-x-2">
            <Label htmlFor={`include-files-${channelId}`} className="text-base">
              Process File Content
            </Label>
            <span className="text-xs px-2 py-0.5 rounded-full bg-primary text-white font-medium">
              Soon
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Extract text from shared files
          </p>
        </div>
        <div className="flex items-center space-x-2 pt-1">
          <Switch 
            id={`include-files-${channelId}`} 
            checked={settings.processFileContent}
            disabled 
          />
        </div>
      </div>
    </div>
  );
} 