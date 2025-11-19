import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Copy, Check, Share2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import axios from "../../http/axiosAgentConfig";
import { useAuth } from "@/contexts/AuthContext";

interface ShareWorkflowProps {
  blueprintId: string;
  className?: string;
}

export default function ShareWorkflow({
  blueprintId,
  className = "",
}: ShareWorkflowProps) {
  const [enabled, setEnabled] = useState(false);
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();
  const { user } = useAuth();

  // Fetch current sharing status
  useEffect(() => {
    if (!blueprintId) return;
    
    const fetchStatus = async () => {
      try {
        const response = await axios.get(
          `/shares/public-chat.status.get?blueprintId=${blueprintId}`
        );
        setEnabled(response.data.enabled || false);
        setShareLink(response.data.share_link || null);
      } catch (error) {
        console.error("Error fetching share status:", error);
      }
    };

    fetchStatus();
  }, [blueprintId]);

  const handleToggle = async (checked: boolean) => {
    if (!user?.username) {
      toast({
        title: "Authentication Required",
        description: "Please log in to enable sharing",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      if (checked) {
        // Enable sharing
        const response = await axios.post("/shares/public-chat.enable", {
          blueprintId,
          userId: user.username,
        });
        setEnabled(true);
        setShareLink(response.data.share_link);
        toast({
          title: "Sharing Enabled",
          description: "Your workflow is now accessible via the share link",
        });
      } else {
        // Disable sharing
        await axios.post("/shares/public-chat.disable", {
          blueprintId,
          userId: user.username,
        });
        setEnabled(false);
        setShareLink(null);
        toast({
          title: "Sharing Disabled",
          description: "Your workflow is no longer accessible via the share link",
        });
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.error || "Failed to update sharing settings",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyLink = () => {
    if (shareLink) {
      navigator.clipboard.writeText(shareLink);
      setCopied(true);
      toast({
        title: "Link Copied",
        description: "Share link copied to clipboard",
      });
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!blueprintId) {
    return null;
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Share2 className="h-4 w-4 text-gray-400" />
          <Label htmlFor="share-toggle" className="text-sm font-medium">
            Enable Public Chat Sharing
          </Label>
        </div>
        <Switch
          id="share-toggle"
          checked={enabled}
          onCheckedChange={handleToggle}
          disabled={isLoading}
        />
      </div>

      {enabled && shareLink && (
        <div className="space-y-2">
          <Label className="text-xs text-gray-400">Share Link</Label>
          <div className="flex items-center space-x-2">
            <div className="flex-1 bg-background-dark border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-300 font-mono break-all">
              {shareLink}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyLink}
              className="border-gray-700 hover:bg-background-surface flex-shrink-0"
              title="Copy link"
            >
              {copied ? (
                <Check className="h-4 w-4 text-green-400" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="text-xs text-gray-500">
            Anyone with this link can chat with your workflow (authentication required)
          </p>
        </div>
      )}

      {!enabled && (
        <p className="text-xs text-gray-500">
          Enable sharing to generate a public chat link for this workflow
        </p>
      )}
    </div>
  );
}

