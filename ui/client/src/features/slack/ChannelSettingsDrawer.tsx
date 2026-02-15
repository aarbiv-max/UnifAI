import { CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { motion } from "framer-motion";
import { EmbedChannel } from "@/types";
import { HiOutlineLockClosed } from "react-icons/hi";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";

export interface ChannelSettingsDrawerProps {
  channel: EmbedChannel;
  isOpen: boolean;
  onClose: () => void;
  onSave: (values: Record<string, string | boolean>) => void;
}


export function ChannelSettingsDrawer({
  channel,
  isOpen,
  onClose,
  onSave,
}: ChannelSettingsDrawerProps) {
  return (
    <motion.div
      className="bg-background-card shadow-lg border-l border-border rounded-lg"
      style={{ pointerEvents: isOpen ? "auto" : "none" }}
    >
      {isOpen && (
        <CardContent className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-foreground">Channel Settings</h3>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="w-4 h-4" />
            </Button>
          </div>

          <div className="space-y-6">
            {/* Channel info card */}
            <div className="space-y-4">
              <div className="flex items-center space-x-3 p-4 bg-muted/50 rounded-lg">
                <div className="w-12 h-12 bg-primary/20 rounded-lg flex items-center justify-center">
                  {channel.is_private ? (
                    <HiOutlineLockClosed className="h-5 w-5" />
                  ) : (
                    <span className="text-lg">#</span>
                  )}
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-foreground text-lg">{channel.name}</h4>
                  <p className="text-sm text-muted-foreground">
                    {channel.messages?.toLocaleString() || 0} messages processed
                  </p>
                </div>
                <Badge
                  variant={channel.status === "DONE" ? "default" : "secondary"}
                  className="capitalize"
                >
                  {channel.status}
                </Badge>
              </div>

              <div className="grid grid-cols-3 gap-3 text-sm">
                <div className="text-center p-3 bg-muted/30 rounded-lg">
                  <p className="text-muted-foreground text-xs uppercase tracking-wide">Last Sync</p>
                  <p className="font-semibold text-foreground text-sm mt-1">{channel.lastSync || "Never"}</p>
                </div>
                <div className="text-center p-3 bg-muted/30 rounded-lg">
                  <p className="text-muted-foreground text-xs uppercase tracking-wide">Type</p>
                  <p className="font-semibold text-foreground text-sm mt-1">{channel.is_private ? "Private" : "Public"}</p>
                </div>
                <div className="text-center p-3 bg-muted/30 rounded-lg">
                  <p className="text-muted-foreground text-xs uppercase tracking-wide">Frequency</p>
                  <p className="font-semibold text-foreground text-sm mt-1">Every 12h</p>
                </div>
              </div>
            </div>

            <Separator />

            {/* Sync Info */}
            <div>
              <Label className="text-sm font-medium mb-3 block">Sync Schedule</Label>
              <div className="flex items-start gap-2 rounded-md bg-blue-500/10 border border-blue-500/20 px-3 py-2">
                <span className="text-blue-400 text-sm mt-0.5">&#8505;</span>
                <p className="text-xs text-blue-300">
                  Messages are collected from the moment this channel was added and
                  synced automatically every 12 hours.
                </p>
              </div>
            </div>

            <Separator />

            {/* Include Threads — disabled for now */}
            <div>
              <Label className="text-sm font-medium mb-3 block">Processing Options</Label>
              <div className="flex items-center justify-between opacity-50 cursor-not-allowed">
                <div>
                  <div className="flex items-center space-x-2">
                    <Label className="text-base">Include Threads</Label>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400 font-medium">
                      Disabled
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">Process conversation threads</p>
                </div>
                <Switch checked disabled />
              </div>

              {/* Process File Content — disabled for now */}
              <div className="flex items-center justify-between mt-4 opacity-50 cursor-not-allowed">
                <div>
                  <div className="flex items-center space-x-2">
                    <Label className="text-base">Process File Content</Label>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-primary text-white font-medium">
                      Soon
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">Extract text from shared files</p>
                </div>
                <Switch checked={false} disabled />
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-6 border-t border-border mt-6">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </div>
        </CardContent>
      )}
    </motion.div>
  );
}
