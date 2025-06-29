import React, { FC, useState, useMemo, useCallback, forwardRef, useImperativeHandle } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FaSearch, FaSpinner } from 'react-icons/fa';
import { HiOutlineLockClosed } from 'react-icons/hi';

import { fetchAvailableSlackChannels, fetchEmbeddedSlackChannels } from '@/api/slack';
import { EmbedChannel } from './SlackIntegration';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
// ── Scope Constants ────────────────────────────────────────────────────
export const SCOPE = {
  ALL: 'all' as const,
  PUBLIC: 'public' as const,
  PRIVATE: 'private' as const,
};
export type Scope = typeof SCOPE[keyof typeof SCOPE];

// ── Channel Type Constants ─────────────────────────────────────────────
export const CHANNEL_TYPE = {
  PUBLIC: 'public_channel' as const,
  PRIVATE: 'private_channel' as const,
};
export type ChannelType = typeof CHANNEL_TYPE[keyof typeof CHANNEL_TYPE];
export const ALL_CHANNEL_TYPES = `${CHANNEL_TYPE.PUBLIC},${CHANNEL_TYPE.PRIVATE}` as const;

// ── Cache Key ─────────────────────────────────────────────────────────
const CACHE_KEY = 'slackChannels';

// ── Scope Options ──────────────────────────────────────────────────────
const scopeOptions: { label: string; value: Scope }[] = [
  { label: 'All', value: SCOPE.ALL },
  { label: 'Public', value: SCOPE.PUBLIC },
  { label: 'Private', value: SCOPE.PRIVATE },
];

// ── Channel Interface ─────────────────────────────────────────────────
export interface Channel {
  channel_name: string;
  channel_id: string;
  is_private: boolean;
}
export interface AddSourceSectionHandle {
  getSelectedChannels(): Channel[];
}

export interface AddSourceSectionProps {
  onSave?: () => void;
  onCancel?: () => void;
  isSubmitting?: boolean;
}

// ── Component ──────────────────────────────────────────────────────────
const AddSourceSection = forwardRef<AddSourceSectionHandle, AddSourceSectionProps>(({ onSave, onCancel, isSubmitting }, ref) => {
  const queryClient = useQueryClient();
  const [scope, setScope] = useState<Scope>(SCOPE.ALL);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);

  // Slack API `types` param mapping
  const typesParam = useMemo<ChannelType | typeof ALL_CHANNEL_TYPES>(() => {
    if (scope === SCOPE.PUBLIC) return CHANNEL_TYPE.PUBLIC;
    if (scope === SCOPE.PRIVATE) return CHANNEL_TYPE.PRIVATE;
    return ALL_CHANNEL_TYPES;
  }, [scope]);


  const qc = useQueryClient();

  const { data: channels = [], isLoading, isError, error } = useQuery<Channel[], Error>(
    {
      queryKey: [CACHE_KEY, typesParam],
      queryFn: async () => {
        if (scope === SCOPE.ALL) {
          const [pub, priv] = await Promise.all([
            fetchAvailableSlackChannels(CHANNEL_TYPE.PUBLIC),
            fetchAvailableSlackChannels(CHANNEL_TYPE.PRIVATE),
          ]);

          // ① prime the individual caches
          qc.setQueryData<Channel[]>([CACHE_KEY, CHANNEL_TYPE.PUBLIC], pub);
          qc.setQueryData<Channel[]>([CACHE_KEY, CHANNEL_TYPE.PRIVATE], priv);

          // ② return merged & deduped
          const map = new Map<string, Channel>();
          pub.concat(priv).forEach(c => map.set(c.channel_id, c));
          return Array.from(map.values());
        }

        return fetchAvailableSlackChannels(typesParam as ChannelType);
      },
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
      refetchOnWindowFocus: false,
    }
  );

  // Get embedded channels to check for already embedded ones
  const { data: embedChannels = [] } = useQuery<EmbedChannel[], Error>({
    queryKey: ["embeddedSlackChannels"],
    queryFn: fetchEmbeddedSlackChannels,
    staleTime: 30 * 1000, // Reduce stale time for more frequent updates
    refetchOnMount: true, // Always refetch when component mounts
    refetchOnWindowFocus: true, // Refetch when user comes back to the page
  });

  useImperativeHandle(ref, () => ({
    getSelectedChannels: () =>
      channels.filter(c => selectedChannels.includes(c.channel_name)),
  }));

  // Check if a channel is already embedded
  const isChannelEmbedded = useCallback((channelName: string) => {
    return embedChannels.some(embedded => embedded.name === channelName);
  }, [embedChannels]);

  // Filter channels by search term
  const filteredChannels = useMemo(
    () => channels.filter(c => c.channel_name.toLowerCase().includes(searchTerm.toLowerCase())),
    [channels, searchTerm]
  );

  // Toggle a channel selection
  const handleToggleChannel = useCallback((name: string) => {
    // Don't allow toggling if channel is already embedded
    if (isChannelEmbedded(name)) {
      return;
    }
    
    setSelectedChannels(prev =>
      prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]
    );
  }, [isChannelEmbedded]);

  // Select all or clear all (excluding embedded channels)
  const allNames = useMemo(() => 
    filteredChannels
      .filter(c => !isChannelEmbedded(c.channel_name))
      .map(c => c.channel_name), 
    [filteredChannels, isChannelEmbedded]
  );
  const allSelected = allNames.length > 0 && allNames.every(n => selectedChannels.includes(n));
  const handleSelectAll = useCallback(() => {
    setSelectedChannels(prev => (allSelected ? [] : Array.from(new Set([...prev, ...allNames]))));
  }, [allNames, allSelected]);

  // Compute counts for display
  const counts: Record<Scope, number> = useMemo(
    () => {
      const publicChannels = queryClient.getQueryData<Channel[]>([CACHE_KEY, CHANNEL_TYPE.PUBLIC]) ?? [];
      const privateChannels = queryClient.getQueryData<Channel[]>([CACHE_KEY, CHANNEL_TYPE.PRIVATE]) ?? [];
      
      // If we don't have cached data yet, fall back to current channels data
      const totalCount = publicChannels.length + privateChannels.length;
      const fallbackTotal = totalCount > 0 ? totalCount : channels.length;
      
      return {
        [SCOPE.ALL]: fallbackTotal,
        [SCOPE.PUBLIC]: publicChannels.length || (scope === SCOPE.PUBLIC ? channels.length : 0),
        [SCOPE.PRIVATE]: privateChannels.length || (scope === SCOPE.PRIVATE ? channels.length : 0),
      };
    },
    [queryClient, channels.length, scope]
  );

  return (
    <Card className="bg-background-card shadow-card border-gray-800">
      <CardContent className="p-4 space-y-4">
        <h3 className="text-lg font-semibold">Channel Selection</h3>

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex bg-muted rounded-lg p-1">
              {scopeOptions.map(({ label, value }) => (
                <button
                  key={value}
                  onClick={() => setScope(value)}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                    scope === value
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground hover:bg-background'
                  }`}
                >
                  {`${label} (${counts[value]})`}
                </button>
              ))}
            </div>
            <div className="relative w-64">
              {!searchTerm && (
                <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 text-sm pointer-events-none">
                  Search Channels
                </div>
              )}
              <Input 
                id="channel-search" 
                value={searchTerm} 
                onChange={e => setSearchTerm(e.target.value)} 
                placeholder="" 
                className={`pr-10 bg-input border-border ${searchTerm ? 'pl-3' : 'pl-28'}`}
                style={{ color: 'hsl(var(--input-foreground))' }}
              />
              <FaSearch className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            </div>
          </div>
          <div className="flex space-x-3">
            <Button 
              variant="outline" 
              onClick={onCancel}
              className="border-border text-foreground hover:bg-muted"
            >
              Cancel
            </Button>
            <Button
              onClick={onSave}
              disabled={isSubmitting}
              className="btn-animated bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {isSubmitting && (
                <FaSpinner className="animate-spin text-current mr-2" />
              )}
              <span>
                {isSubmitting 
                  ? 'Submitting…' 
                  : `Add Channel${selectedChannels.length !== 1 ? 's' : ''} (${selectedChannels.length})`
                }
              </span>
            </Button>
          </div>
        </div>

        <div className="text-sm text-gray-400">
          Showing {filteredChannels.length} of {counts[scope]} {scopeOptions.find(o => o.value === scope)?.label.toLowerCase()} channels
        </div>

        <div className="border border-gray-800 rounded-md h-48 overflow-y-auto bg-background-dark">
          {isLoading && <div className="p-4 text-center text-gray-400">Loading…</div>}
          {isError && <div className="p-4 text-center text-red-500">{error?.message}</div>}
          {!isLoading && !isError && filteredChannels.length === 0 && <div className="p-4 text-center text-gray-500">No channels found</div>}

          {filteredChannels.map(c => {
            const isEmbedded = isChannelEmbedded(c.channel_name);
            return (
              <div 
                key={c.channel_id} 
                className={`flex items-center justify-between p-3 border-b border-gray-800 ${
                  isEmbedded ? 'opacity-60 cursor-not-allowed' : 'hover:bg-background-surface cursor-pointer'
                }`}
                onClick={() => !isEmbedded && handleToggleChannel(c.channel_name)}
              >
                <div className="flex items-center">
                  <span className="text-gray-400 mr-2">{c.is_private ? <HiOutlineLockClosed className="inline" /> : '#'}</span>
                  <span>{c.channel_name}</span>
                  {c.is_private && <Badge className="ml-2 bg-secondary bg-opacity-20 text-gray-400">Private</Badge>}
                  {!c.is_private && <Badge className="ml-2 bg-secondary bg-opacity-20 text-gray-400">Public</Badge>}
                  {isEmbedded && <Badge className="ml-2 bg-green-500/20 text-green-400 border border-green-400/30">Embedded</Badge>}
                </div>
                <Switch 
                  checked={isEmbedded || selectedChannels.includes(c.channel_name)} 
                  disabled={isEmbedded}
                  onCheckedChange={() => handleToggleChannel(c.channel_name)} 
                />
              </div>
            );
          })}
        </div>

        <div className="flex justify-between items-center">
          <span className="text-sm">{selectedChannels.length} channel{selectedChannels.length !== 1 && 's'} selected</span>
          <Button variant="outline" size="sm" onClick={handleSelectAll}>{allSelected ? 'Clear All' : 'Select All'}</Button>
        </div>

        <div>
          <Label htmlFor="date-range" className="text-sm">
            Date Range
          </Label>
          <Select defaultValue="30d">
            <SelectTrigger
              id="date-range"
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

        <div className="flex items-center justify-between pt-1">
          <div>
            <Label htmlFor="include-threads" className="text-base">
              Include Threads
            </Label>
            <p className="text-xs text-gray-400 mt-1">
              Process conversation threads
            </p>
          </div>
          <Switch id="include-threads" defaultChecked />
        </div>

        <div className="flex items-start justify-between opacity-50 cursor-not-allowed">
          <div>
            <div className="flex items-center space-x-2">
              <Label htmlFor="include-files" className="text-base">
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
            <Switch id="include-files" disabled />
          </div>
        </div>
      </CardContent>
    </Card>
  );
});

export default AddSourceSection;
