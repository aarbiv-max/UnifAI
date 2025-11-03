import React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { FaInfoCircle } from "react-icons/fa";

interface GoogleOAuthCredentials {
  clientId: string;
  clientSecret: string;
  mailAddress: string;
}

interface GoogleMcpOAuthFieldsProps {
  credentials: GoogleOAuthCredentials;
  onCredentialsChange: (credentials: GoogleOAuthCredentials) => void;
}

export const GoogleMcpOAuthFields: React.FC<GoogleMcpOAuthFieldsProps> = ({
  credentials,
  onCredentialsChange,
}) => {
  const googleOAuthGuide = (
    <div className="space-y-2 text-sm max-w-md">
      <p className="font-semibold mb-2">How to get Google OAuth credentials:</p>
      <ol className="list-decimal list-inside space-y-1">
        <li>Go to <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer" className="text-primary underline">Google Cloud Console</a></li>
        <li>Select your project or create a new one</li>
        <li>Navigate to <strong>APIs & Services</strong> → <strong>Credentials</strong></li>
        <li>Click <strong>Create Credentials</strong> → <strong>OAuth client ID</strong></li>
        <li>Choose application type and configure OAuth consent screen if needed</li>
        <li>Copy the <strong>Client ID</strong> and <strong>Client Secret</strong></li>
        <li>Use the email address associated with your Google Cloud project</li>
      </ol>
    </div>
  );

  const handleChange = (field: keyof GoogleOAuthCredentials, value: string) => {
    onCredentialsChange({
      ...credentials,
      [field]: value,
    });
  };

  return (
    <div className="space-y-4 mt-4 p-4 border border-amber-600/50 rounded-lg bg-amber-900/10">
      <div className="flex items-center gap-2 mb-2">
        <div className="flex items-center gap-2 flex-1">
          <Badge variant="outline" className="bg-amber-900/30 text-amber-300 border-amber-600/50">
            Google MCP Server Detected
          </Badge>
          <h4 className="text-sm font-semibold">Google OAuth Credentials</h4>
        </div>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                className="text-gray-400 hover:text-gray-300 cursor-help p-1 rounded hover:bg-gray-800 transition-colors"
                aria-label="Show Google OAuth credentials guide"
              >
                <FaInfoCircle className="w-4 h-4" />
              </button>
            </TooltipTrigger>
            <TooltipPrimitive.Portal>
              <TooltipContent className="max-w-md p-4 z-[9999]">
                {googleOAuthGuide}
              </TooltipContent>
            </TooltipPrimitive.Portal>
          </Tooltip>
        </TooltipProvider>
      </div>

      <div className="space-y-4">
        {/* Client ID Field */}
        <div className="space-y-2">
          <Label htmlFor="google-client-id">
            Client ID <span className="text-red-400">*</span>
          </Label>
          <Input
            id="google-client-id"
            type="text"
            value={credentials.clientId}
            onChange={(e) => handleChange("clientId", e.target.value)}
            className="bg-background-dark"
            placeholder="Enter your Google OAuth Client ID"
          />
          <p className="text-xs text-gray-400">
            Your Google OAuth 2.0 Client ID from Google Cloud Console
          </p>
        </div>

        {/* Client Secret Field */}
        <div className="space-y-2">
          <Label htmlFor="google-client-secret">
            Client Secret <span className="text-red-400">*</span>
          </Label>
          <Input
            id="google-client-secret"
            type="password"
            value={credentials.clientSecret}
            onChange={(e) => handleChange("clientSecret", e.target.value)}
            className="bg-background-dark"
            placeholder="Enter your Google OAuth Client Secret"
          />
          <p className="text-xs text-gray-400">
            Your Google OAuth 2.0 Client Secret from Google Cloud Console
          </p>
        </div>

        {/* Mail Address Field */}
        <div className="space-y-2">
          <Label htmlFor="google-mail-address">
            Mail Address <span className="text-red-400">*</span>
          </Label>
          <Input
            id="google-mail-address"
            type="email"
            value={credentials.mailAddress}
            onChange={(e) => handleChange("mailAddress", e.target.value)}
            className="bg-background-dark"
            placeholder="your-email@example.com"
          />
          <p className="text-xs text-gray-400">
            The email address associated with your Google Cloud project
          </p>
        </div>
      </div>
    </div>
  );
};

