import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FaRocket } from "react-icons/fa";
import { useMemo } from "react";
import { generateColorPalette } from "@/lib/colorUtils";
import { AnalyticCard } from "./AnalyticCard";

interface BlueprintsTableProps {
  blueprints: Array<{
    blueprint_name: string;
    run_count: number;
    unique_users: number;
  }>;
  colors: Record<string, string>;
}

export function BlueprintsTable({ blueprints, colors }: BlueprintsTableProps) {
  const colorPalette = useMemo(() => {
    return generateColorPalette(colors.primary, blueprints?.length || 0);
  }, [colors.primary, blueprints?.length]);

  return (
    <AnalyticCard
      title="Most Used Blueprints"
      icon={<FaRocket style={{ color: colors.primary }} />}
    >
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Blueprint Name</TableHead>
              <TableHead className="text-right">Total Runs</TableHead>
              <TableHead className="text-right">Unique Users</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {blueprints.length > 0 ? (
              blueprints.map((bp, idx) => {
                const color = colorPalette[idx % colorPalette.length];
                return (
                  <TableRow key={idx} className="hover:bg-muted/50">
                    <TableCell className="font-medium text-sm max-w-[300px] truncate">
                      {bp.blueprint_name}
                    </TableCell>
                    <TableCell className="text-right text-sm font-semibold" style={{ color }}>
                      {bp.run_count}
                    </TableCell>
                    <TableCell className="text-right text-sm">{bp.unique_users}</TableCell>
                  </TableRow>
                );
              })
            ) : (
              <TableRow>
                <TableCell colSpan={3} className="text-center py-6 text-gray-400">
                  No blueprint data available
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </AnalyticCard>
  );
}
