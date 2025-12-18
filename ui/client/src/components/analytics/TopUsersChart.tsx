import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { FaUsers } from "react-icons/fa";
import GlassPanel from "@/components/ui/GlassPanel";

interface TopUsersChartProps {
  topUsersData: Array<{
    name: string;
    fullName: string;
    runs: number;
    blueprints: number;
    completed: number;
    failed: number;
  }>;
  colors: Record<string, string>;
}

export function TopUsersChart({ topUsersData, colors }: TopUsersChartProps) {
  return (
    <GlassPanel>
      <Card className="shadow-card border-gray-800 h-full flex flex-col bg-transparent border-0">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-heading flex items-center gap-2">
            <FaUsers style={{ color: colors.info }} />
            Top Active Users
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={topUsersData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis 
                dataKey="name" 
                stroke="#9CA3AF" 
                angle={-45} 
                textAnchor="end" 
                height={80}
                style={{ fontSize: '12px' }}
              />
              <YAxis stroke="#9CA3AF" style={{ fontSize: '12px' }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#374151', border: '1px solid #6B7280', borderRadius: '0.375rem' }}
                labelStyle={{ color: '#F9FAFB' }}
                formatter={(value, name) => [value, name === 'runs' ? 'Total Runs' : 'Blueprints']}
              />
              <Bar dataKey="runs" fill={colors.primary} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </GlassPanel>
  );
}

