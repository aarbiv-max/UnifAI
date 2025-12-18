import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { FaChartLine } from "react-icons/fa";
import GlassPanel from "@/components/ui/GlassPanel";

type TimeRange = 'today' | '7days' | '30days' | 'all';

interface WorkflowExecutionChartProps {
  timeSeriesData: Array<{
    period: string;
    count: number;
  }>;
  timeRange: TimeRange;
  colors: Record<string, string>;
}

export function WorkflowExecutionChart({ timeSeriesData, timeRange, colors }: WorkflowExecutionChartProps) {
  // Format the data for the chart
  const chartData = timeSeriesData.map((item) => ({
    period: formatPeriodLabel(item.period, timeRange),
    count: item.count,
    fullPeriod: item.period
  }));

  // Format period label based on time range
  function formatPeriodLabel(period: string, range: string): string {
    if (!period) return '';
    
    try {
      if (range === 'today') {
        // Format: "2024-01-15 14:00" -> "2:00 PM"
        // Try parsing as date first
        let date: Date | null = null;
        if (period.includes('T') || period.includes('Z')) {
          date = new Date(period);
        } else if (period.includes(' ')) {
          // Format: "2024-01-15 14:00" - add timezone for parsing
          date = new Date(period + ':00Z');
        } else {
          date = new Date(period);
        }
        
        if (date && !isNaN(date.getTime())) {
          return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
        }
        
        // Fallback: extract hour from string like "2024-01-15 14:00"
        const parts = period.split(' ');
        if (parts.length > 1) {
          const hourStr = parts[1].split(':')[0];
          const hour = parseInt(hourStr);
          if (!isNaN(hour)) {
            const ampm = hour >= 12 ? 'PM' : 'AM';
            const displayHour = hour % 12 || 12;
            return `${displayHour}:00 ${ampm}`;
          }
        }
      } else {
        // Format: "2024-01-15" -> "Jan 15"
        let date: Date | null = null;
        if (period.includes('T') || period.includes('Z')) {
          date = new Date(period);
        } else {
          // Assume it's a date string like "2024-01-15"
          date = new Date(period + 'T00:00:00Z');
        }
        
        if (date && !isNaN(date.getTime())) {
          return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }
      }
      return period;
    } catch {
      return period;
    }
  }

  const getChartTitle = () => {
    switch (timeRange) {
      case 'today':
        return 'Workflow Executions Today (by Hour)';
      case '7days':
        return 'Workflow Executions (Last 7 Days)';
      case '30days':
        return 'Workflow Executions (Last 30 Days)';
      default:
        return 'Workflow Executions Over Time';
    }
  };

  return (
    <GlassPanel>
      <Card className="shadow-card border-gray-800 h-full flex flex-col bg-transparent border-0">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-heading flex items-center gap-2">
            <FaChartLine style={{ color: colors.primary }} />
            {getChartTitle()}
          </CardTitle>
        </CardHeader>
        <CardContent>
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
                  contentStyle={{ 
                    backgroundColor: '#374151', 
                    border: '1px solid #6B7280', 
                    borderRadius: '0.375rem' 
                  }}
                  labelStyle={{ color: '#F9FAFB' }}
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
        </CardContent>
      </Card>
    </GlassPanel>
  );
}

