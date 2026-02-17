import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { FaChartLine } from "react-icons/fa";
import { AnalyticCard } from "./AnalyticCard";
import {
  CHART_TOOLTIP_CONTENT_STYLE,
  CHART_TOOLTIP_LABEL_STYLE,
  formatPeriodLabel,
  getTimeRangeSuffix,
} from "./analyticsHelpers";
import type { TimeRange } from "@/types/systemStats";

interface WorkflowExecutionChartProps {
  timeSeriesData: Array<{
    period: string;
    count: number;
  }>;
  timeRange: TimeRange;
  colors: Record<string, string>;
}

export function WorkflowExecutionChart({ timeSeriesData, timeRange, colors }: WorkflowExecutionChartProps) {
  const chartData = timeSeriesData.map((item) => ({
    period: formatPeriodLabel(item.period, timeRange),
    count: item.count,
    fullPeriod: item.period
  }));

  const chartTitle = `Workflow Executions ${getTimeRangeSuffix(timeRange)}`;

  return (
    <AnalyticCard
      title={chartTitle}
      icon={<FaChartLine style={{ color: colors.primary }} />}
    >
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorWorkflows" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={colors.primary} stopOpacity={0.3}/>
                <stop offset="95%" stopColor={colors.primary} stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="period" 
              stroke="#9CA3AF" 
              style={{ fontSize: '12px' }}
              angle={chartData.length > 10 ? -45 : 0}
              textAnchor={chartData.length > 10 ? 'end' : 'middle'}
              height={chartData.length > 10 ? 80 : 30}
            />
            <YAxis stroke="#9CA3AF" style={{ fontSize: '12px' }} />
            <Tooltip 
              contentStyle={CHART_TOOLTIP_CONTENT_STYLE}
              labelStyle={CHART_TOOLTIP_LABEL_STYLE}
              formatter={(value: number) => [`${value} workflows`, 'Executions']}
              labelFormatter={(label) => `Period: ${label}`}
            />
            <Area 
              type="monotone" 
              dataKey="count" 
              stroke={colors.primary} 
              fillOpacity={1} 
              fill="url(#colorWorkflows)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="flex flex-col items-center justify-center h-64 text-gray-400">
          <FaChartLine className="text-5xl mb-4 opacity-30" />
          <p className="text-sm">No workflow execution data available for this period</p>
        </div>
      )}
    </AnalyticCard>
  );
}
