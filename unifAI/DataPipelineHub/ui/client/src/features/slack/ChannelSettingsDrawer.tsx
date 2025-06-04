import { useState, useEffect } from "react";
import { CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { motion } from "framer-motion";
import { FaTimes } from "react-icons/fa";

export interface SettingOption {
  value: string | number;
  label: string;
}

export type SettingType = "select" | "switch";

export interface SettingBase<T extends SettingType> {
  id: string;
  type: T;
  label: string;
  description?: string;
  defaultValue: T extends "select" ? string : boolean;
  options?: T extends "select" ? SettingOption[] : never;
}

export type SelectSetting = SettingBase<"select"> & {
  defaultValue: string;
  options: SettingOption[];
};

export type SwitchSetting = SettingBase<"switch"> & {
  defaultValue: boolean;
};

export type AnySetting = SelectSetting | SwitchSetting;

export interface SettingsCategory {
  title?: string;
  settings: AnySetting[];
}

export interface ChannelSettingsDrawerProps {
  channelName: string;
  isOpen: boolean;
  onClose: () => void;
  onSave: (values: Record<string, string | boolean>) => void;
}

const categories: SettingsCategory[] = [
  {
    title: "Sync Options",
    settings: [
      {
        id: "updateFrequency",
        type: "select",
        label: "Update Frequency",
        description: "How often to sync new messages",
        defaultValue: "30",
        options: [
          { value: "15", label: "Every 15 minutes" },
          { value: "30", label: "Every 30 minutes" },
          { value: "60", label: "Every hour" },
          { value: "360", label: "Every 6 hours" },
          { value: "720", label: "Every 12 hours" },
          { value: "1440", label: "Every day" },
        ],
      },
      {
        id: "includeThreads",
        type: "switch",
        label: "Include Threads",
        description: "Process conversation threads",
        defaultValue: true,
      },
      {
        id: "includeEmoji",
        type: "switch",
        label: "Include Reactions",
        description: "Store emoji reactions as metadata",
        defaultValue: true,
      },
      {
        id: "channelActive",
        type: "switch",
        label: "Channel Active",
        description: "Toggle channel processing",
        defaultValue: true,
      },
    ],
  },
  {
    title: "Historical Data",
    settings: [
      {
        id: "historyRange",
        type: "select",
        label: "Historical Data Range",
        description: "Messages to keep in the database",
        defaultValue: "all",
        options: [
          { value: "30d", label: "Last 30 days" },
          { value: "90d", label: "Last 90 days" },
          { value: "180d", label: "Last 6 months" },
          { value: "365d", label: "Last year" },
          { value: "all", label: "All time" },
        ],
      },
    ],
  },
];

export function ChannelSettingsDrawer({
  channelName,
  isOpen,
  onClose,
  onSave,
}: ChannelSettingsDrawerProps) {

  const [values, setValues] = useState<Record<string, string | boolean>>({});

  // Initialize defaults whenever `categories` or `isOpen` changes
  useEffect(() => {
    if (isOpen) {
      const initial: Record<string, string | boolean> = {};
      categories.forEach((cat) => {
        cat.settings.forEach((s) => {
          initial[s.id] = s.defaultValue;
        });
      });
      setValues(initial);
    }
  }, [categories, isOpen]);

  // Handler for select / switch changes
  const handleChange = (id: string, newValue: string | boolean) => {
    setValues((prev) => ({ ...prev, [id]: newValue }));
  };

  // When “Save Changes” is clicked
  const handleSave = () => {
    onSave(values);
    onClose();
  };

  return (
    <motion.div
      className="h-full bg-background-card shadow-lg border-l border-gray-800"
      initial={{ x: 300, opacity: 0 }}
      animate={isOpen ? { x: 0, opacity: 1 } : { x: 300, opacity: 0 }}
      exit={{ x: 300, opacity: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      style={{ pointerEvents: isOpen ? "auto" : "none" }}
    >
      {isOpen && (
        <CardContent className="p-6 flex flex-col h-full justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">
                Settings for #{channelName}
              </h3>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <FaTimes />
              </Button>
            </div>

            <Separator className="bg-gray-800 mb-4" />

            {/* Iterate over each category */}
            {categories.map((category, catIdx) => (
              <div key={catIdx} className="mb-6">
                {category.title && (
                  <>
                    <Label className="text-sm font-medium mb-2 block">
                      {category.title}
                    </Label>
                    <Separator className="bg-gray-800 mb-4" />
                  </>
                )}

                {category.settings.map((setting) => {
                  if (setting.type === "select") {
                    const sel = setting as SelectSetting;
                    return (
                      <div key={sel.id} className="mb-4">
                        <Label
                          htmlFor={sel.id}
                          className="text-sm block"
                        >
                          {sel.label}
                        </Label>
                        <Select
                          value={String(values[sel.id] ?? sel.defaultValue)}
                          onValueChange={(val) =>
                            handleChange(sel.id, val)
                          }
                        >
                          <SelectTrigger
                            id={sel.id}
                            className="mt-1 bg-background-dark w-full"
                          >
                            <SelectValue placeholder="Select…" />
                          </SelectTrigger>
                          <SelectContent>
                            {sel.options.map((opt) => (
                              <SelectItem key={opt.value} value={String(opt.value)}>
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {sel.description && (
                          <p className="text-xs text-gray-400 mt-1">
                            {sel.description}
                          </p>
                        )}
                      </div>
                    );
                  } else {
                    // type === "switch"
                    const sw = setting as SwitchSetting;
                    return (
                      <div
                        key={sw.id}
                        className="flex items-center justify-between mb-4"
                      >
                        <div>
                          <Label htmlFor={sw.id} className="text-base">
                            {sw.label}
                          </Label>
                          {sw.description && (
                            <p className="text-xs text-gray-400 mt-1">
                              {sw.description}
                            </p>
                          )}
                        </div>
                        <Switch
                          id={sw.id}
                          checked={Boolean(values[sw.id])}
                          onCheckedChange={(checked) =>
                            handleChange(sw.id, checked)
                          }
                        />
                      </div>
                    );
                  }
                })}
              </div>
            ))}
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button className="bg-secondary" onClick={handleSave}>
              Save Changes
            </Button>
          </div>
        </CardContent>
      )}
    </motion.div>
  );
}
