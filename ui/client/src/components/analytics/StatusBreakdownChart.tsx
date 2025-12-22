import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from "recharts";
import { FaCheckCircle } from "react-icons/fa";
import { AnalyticCard } from "./AnalyticCard";

interface StatusBreakdownChartProps {
  statusData: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  totalRuns: number;
  colors: Record<string, string>;
}

export function StatusBreakdownChart({ statusData, totalRuns, colors }: StatusBreakdownChartProps) {
  return (
    <AnalyticCard
      title="Status Breakdown"
      icon={<FaCheckCircle className="text-success" />}
    >
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  dataKey="value"
                  label={false}
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Legend 
                  verticalAlign="bottom" 
                  height={36}
                  formatter={(value: string, entry: any) => {
                    const count = entry.payload.value;
                    const percent = ((count / totalRuns) * 100).toFixed(0);
                    return <span className="text-sm">{value}: {count} ({percent}%)</span>;
                  }}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#374151', border: '1px solid #6B7280', borderRadius: '0.375rem' }}
                  labelStyle={{ color: '#F9FAFB' }}
                  formatter={(value: number) => [
                    `${value} runs (${((value / totalRuns) * 100).toFixed(1)}%)`,
                    'Status'
                  ]}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-gray-400">
              <FaCheckCircle className="text-5xl mb-4 opacity-30" />
              <p className="text-sm">No workflow data available</p>
            </div>
          )}
    </AnalyticCard>
  );
}

