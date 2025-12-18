import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FaRocket } from "react-icons/fa";
import GlassPanel from "@/components/ui/GlassPanel";
import { useMemo } from "react";
import { generateColorPalette } from "@/lib/colorUtils";

interface TopBlueprintsQuickViewProps {
  blueprints: Array<{
    blueprint_name: string;
    run_count: number;
    unique_users: number;
  }>;
  totalBlueprints: number;
  colors: Record<string, string>;
}

export function TopBlueprintsQuickView({ blueprints, totalBlueprints, colors }: TopBlueprintsQuickViewProps) {
  const colorPalette = useMemo(() => {
    return generateColorPalette(colors.primary, blueprints?.length || 0);
  }, [colors.primary, blueprints?.length]);

  if (!blueprints || blueprints.length === 0) {
    return (
      <GlassPanel>
        <Card className="shadow-card border-gray-800 h-full flex flex-col bg-transparent border-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-heading flex items-center gap-2">
              <FaRocket style={{ color: colors.primary }} />
              Top Blueprints
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center h-48 text-gray-400">
              <FaRocket className="text-4xl mb-3 opacity-30" />
              <p className="text-sm">No blueprint data available</p>
            </div>
          </CardContent>
        </Card>
      </GlassPanel>
    );
  }

  const maxRuns = Math.max(...blueprints.map((bp) => bp.run_count), 1);

  return (
    <GlassPanel>
      <Card className="shadow-card border-gray-800 h-full flex flex-col bg-transparent border-0">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-heading flex items-center gap-2">
            <FaRocket style={{ color: colors.primary }} />
            Top Blueprints
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {blueprints.map((bp, idx) => {
              const percentage = (bp.run_count / maxRuns) * 100;
              const color = colorPalette[idx % colorPalette.length];
              return (
                <div key={idx} className="space-y-2">
                  <div className="flex justify-between items-center text-sm">
                    <span className="font-medium truncate max-w-[200px]" title={bp.blueprint_name}>
                      {bp.blueprint_name}
                    </span>
                    <div className="flex items-center gap-3">
                      <span className="text-gray-400 text-xs">{bp.unique_users} users</span>
                      <span className="font-semibold" style={{ color }}>
                        {bp.run_count}
                      </span>
                    </div>
                  </div>
                  <div className="w-full bg-background-dark rounded-full h-2">
                    <div
                      className="h-2 rounded-full transition-all"
                      style={{
                        width: `${percentage}%`,
                        backgroundColor: color
                      }}
                    />
                  </div>
                </div>
              );
            })}
            {totalBlueprints > 5 && (
              <div className="pt-2 border-t border-gray-700 text-center">
                <p className="text-xs text-gray-500">
                  +{totalBlueprints - 5} more blueprints
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </GlassPanel>
  );
}

