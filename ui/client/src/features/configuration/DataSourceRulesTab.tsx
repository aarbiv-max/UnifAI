import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { FaSave, FaUndo } from "react-icons/fa";
import {
  getAdminConfig,
  updateAdminConfigSection,
  type AdminConfigResponse,
  type SectionValue,
  type FieldValue,
} from "@/api/adminConfig";
import StringListField from "./StringListField";

/**
 * DataSourceRulesTab — renders the admin config template dynamically.
 *
 * Fetches categories → sections → fields from the platform-backend,
 * renders each field by its `field_type`, and saves per-section.
 */
export default function DataSourceRulesTab() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const {
    data: config,
    isLoading,
    isError,
    error,
  } = useQuery<AdminConfigResponse>({
    queryKey: ["admin-config"],
    queryFn: getAdminConfig,
    staleTime: 30 * 1000,
    refetchOnMount: true,
  });

  if (isLoading) return <LoadingSkeleton />;
  if (isError) return <ErrorState message={(error as Error)?.message} />;
  if (!config) return null;

  return (
    <div className="space-y-8">
      {config.categories.map((category) => (
        <div key={category.key}>
          <div className="mb-4">
            <h2 className="text-xl font-heading font-semibold">{category.title}</h2>
            {category.description && (
              <p className="text-sm text-gray-400 mt-1">{category.description}</p>
            )}
          </div>

          <div className="grid grid-cols-1 gap-6">
            {category.sections.map((section) => (
              <SectionCard
                key={section.key}
                section={section}
                queryClient={queryClient}
                toast={toast}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  Section Card — one card per section, with its own local state + save
// ─────────────────────────────────────────────────────────────────────────────

interface SectionCardProps {
  section: SectionValue;
  queryClient: ReturnType<typeof useQueryClient>;
  toast: ReturnType<typeof useToast>["toast"];
}

function SectionCard({ section, queryClient, toast }: SectionCardProps) {
  // Local form state — keyed by field key
  const [values, setValues] = useState<Record<string, unknown>>(() =>
    buildInitialValues(section.fields),
  );
  const [isDirty, setIsDirty] = useState(false);

  // Reset local state when server data changes
  useEffect(() => {
    setValues(buildInitialValues(section.fields));
    setIsDirty(false);
  }, [section]);

  const mutation = useMutation({
    mutationFn: (vals: Record<string, unknown>) =>
      updateAdminConfigSection(section.key, vals),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-config"] });
      toast({
        title: "Saved",
        description: `${section.title} updated successfully.`,
      });
      setIsDirty(false);
    },
    onError: (err: Error) => {
      toast({
        variant: "destructive",
        title: "Save failed",
        description: err.message,
      });
    },
  });

  const handleFieldChange = (fieldKey: string, newValue: unknown) => {
    setValues((prev) => ({ ...prev, [fieldKey]: newValue }));
    setIsDirty(true);
  };

  const handleSave = () => mutation.mutate(values);

  const handleReset = () => {
    setValues(buildInitialValues(section.fields));
    setIsDirty(false);
  };

  return (
    <Card className="bg-background-card shadow-card border-gray-800">
      <CardContent className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-1">
          <div>
            <h3 className="text-lg font-heading font-semibold">{section.title}</h3>
            {section.description && (
              <p className="text-sm text-gray-400 mt-1 max-w-2xl">
                {section.description}
              </p>
            )}
          </div>
          {section.updated_at && (
            <Badge variant="outline" className="text-xs text-gray-500 shrink-0">
              Last updated: {new Date(section.updated_at).toLocaleDateString()}
            </Badge>
          )}
        </div>

        {/* Fields */}
        <div className="mt-6 space-y-6">
          {section.fields.map((field) => (
            <FieldRenderer
              key={field.key}
              field={field}
              value={values[field.key]}
              onChange={(v) => handleFieldChange(field.key, v)}
            />
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 mt-8 pt-4 border-t border-gray-800">
          <Button
            onClick={handleSave}
            disabled={!isDirty || mutation.isPending}
            className="bg-primary"
          >
            <FaSave className="mr-2 w-3.5 h-3.5" />
            {mutation.isPending ? "Saving..." : "Save Changes"}
          </Button>
          <Button
            variant="outline"
            onClick={handleReset}
            disabled={!isDirty || mutation.isPending}
          >
            <FaUndo className="mr-2 w-3.5 h-3.5" />
            Reset
          </Button>
          {isDirty && (
            <span className="text-xs text-amber-400 ml-2">Unsaved changes</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  Field Renderer — dispatches to the right control by field_type
// ─────────────────────────────────────────────────────────────────────────────

interface FieldRendererProps {
  field: FieldValue;
  value: unknown;
  onChange: (value: unknown) => void;
}

function FieldRenderer({ field, value, onChange }: FieldRendererProps) {
  return (
    <div>
      <Label className="text-base font-medium">{field.label}</Label>
      {field.description && (
        <p className="text-xs text-gray-400 mt-1 mb-2">{field.description}</p>
      )}

      {field.field_type === "string_list" && (
        <StringListField
          value={Array.isArray(value) ? (value as string[]) : []}
          onChange={(v) => onChange(v)}
          placeholder={field.placeholder}
        />
      )}

      {field.field_type === "string" && (
        <Input
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          className="bg-background-dark max-w-md"
        />
      )}

      {field.field_type === "number" && (
        <Input
          type="number"
          value={typeof value === "number" ? value : 0}
          onChange={(e) => onChange(Number(e.target.value))}
          placeholder={field.placeholder}
          className="bg-background-dark w-32"
        />
      )}

      {field.field_type === "boolean" && (
        <div className="flex items-center gap-3 mt-1">
          <Switch
            checked={Boolean(value)}
            onCheckedChange={(checked) => onChange(checked)}
          />
          <span className="text-sm text-gray-400">
            {value ? "Enabled" : "Disabled"}
          </span>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────────────────────────────────────

function buildInitialValues(fields: FieldValue[]): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const f of fields) {
    result[f.key] = f.value ?? f.default ?? null;
  }
  return result;
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      {[1, 2].map((i) => (
        <Card key={i} className="bg-background-card shadow-card border-gray-800">
          <CardContent className="p-6 space-y-4">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-96" />
            <div className="space-y-3 mt-4">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-10 w-full" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ErrorState({ message }: { message?: string }) {
  return (
    <Card className="bg-background-card shadow-card border-gray-800">
      <CardContent className="p-6 text-center">
        <p className="text-red-400 font-medium">Failed to load configuration</p>
        <p className="text-sm text-gray-400 mt-1">
          {message || "Could not connect to the platform backend."}
        </p>
      </CardContent>
    </Card>
  );
}
