import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { FaUsers } from "react-icons/fa";
import { AnalyticCard } from "./AnalyticCard";

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
    <AnalyticCard
      title="Top Active Users"
      icon={<FaUsers style={{ color: colors.info }} />}
    >
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
    </AnalyticCard>
  );
}

