import { Card, CardContent } from "@/components/ui/card";
import { useState } from "react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { FaChevronDown, FaChevronRight } from "react-icons/fa";
import { Separator } from "@/components/ui/separator";


interface ProcessingOptionsProps {
  className?: string;
}

interface ProcessingSettings {
  autoProcess: boolean;
  extractMetadata: boolean;
  ocrEnabled: boolean;
}

export const ProcessingOptions: React.FC<ProcessingOptionsProps> = ({ className }) => {
  const [showProcessingOptions, setShowProcessingOptions] = useState(false);
  const [settings, setSettings] = useState<ProcessingSettings>({
    autoProcess: true,
    extractMetadata: true,
    ocrEnabled: false,
  });

  const handleSettingChange = (key: keyof ProcessingSettings, value: boolean) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className={className}>
      <div
        className="flex items-center space-x-2 cursor-pointer text-primary text-sm font-semibold mt-4"
        onClick={() => setShowProcessingOptions((prev) => !prev)}
      >
        {showProcessingOptions ? (
          <FaChevronDown className="transition-transform duration-200" />
        ) : (
          <FaChevronRight className="transition-transform duration-200" />
        )}
        <span>Processing Options</span>
      </div>

      {showProcessingOptions && (
        <Card className="bg-background-card shadow-card border-gray-800 w-full">
          <CardContent className="p-6 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="auto-process" className="text-base">
                  Auto-Process Files
                </Label>
                <p className="text-xs text-gray-400 mt-1">
                  Automatically start processing after upload
                </p>
              </div>
              <Switch 
                id="auto-process" 
                checked={settings.autoProcess}
                onCheckedChange={(checked) => handleSettingChange('autoProcess', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="extract-metadata" className="text-base">
                  Extract Metadata
                </Label>
                <p className="text-xs text-gray-400 mt-1">
                  Extract file properties as metadata
                </p>
              </div>
              <Switch 
                id="extract-metadata" 
                checked={settings.extractMetadata}
                onCheckedChange={(checked) => handleSettingChange('extractMetadata', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="ocr-enabled" className="text-base">
                  Enable OCR
                </Label>
                <p className="text-xs text-gray-400 mt-1">
                  Extract text from images within documents
                </p>
              </div>
              <Switch 
                id="ocr-enabled" 
                checked={settings.ocrEnabled}
                onCheckedChange={(checked) => handleSettingChange('ocrEnabled', checked)}
              />
            </div>
            <Separator className="bg-gray-800" />
          </CardContent>
        </Card>
      )}
    </div>
  );
};