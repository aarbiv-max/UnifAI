import React from 'react';
import { PieChart, BarChart, LineChart } from '@mui/x-charts';
import { Typography } from '@mui/material';

const DEFAULT_WIDTH=600;
const DEFAULT_HEIGHT=400;

export interface ChartData {
  id?: number;
  label: string;
  value: number;
}

interface ChartProps {
  type: 'pie' | 'bar' | 'line';
  data: ChartData[];
  className: string;
  title?: string;
  label?: string;
  width?: number;
  height?: number;
  colors?: string[];
  isHidden?: boolean;
}

const Charts: React.FC<ChartProps> = ({
  type,
  data,
  className,
  title = '',
  label = '',
  width = DEFAULT_WIDTH,
  height = DEFAULT_HEIGHT,
  colors,
  isHidden = false
}) => {
  const renderChart = () => {
    switch (type) {
      case 'pie':
        return (
          <PieChart
            series={[{ 
              data: data.map((item, index) => ({
                ...item,
                ...(colors && { color: colors[index] }) // Only add color property if colors array exists
              })),
              innerRadius: '70px'
            }]}
            width={width}
            height={height}
            margin={{ top: 50, bottom: 50, left: 50, right: 50 }}
            slotProps={{
              legend: {
                direction: 'row',
                position: { vertical: 'top', horizontal: 'middle' },
                padding: -10, // in MUI charts, negative padding is valid and used to push the legend up
                labelStyle: {
                  fontSize: '12px'
                },
              },
            }}
          />
        );
      case 'bar':
        return (
          <BarChart
            xAxis={[{ data: data.map(item => item.label), scaleType: 'band',
            colorMap: {
              type: "ordinal",
              colors: colors ? colors : ["#02B2AF"]
            }
            }]}
            slotProps={{ legend: { hidden: isHidden } }}
            series={[{ data: data.map((item: any) => item.value), label: label }]}
            width={width}
            height={height}
            borderRadius={10}
          />
        );
      case 'line':
        return (
          <LineChart
            xAxis={[{ data: data.map((item: any) => item.label), scaleType: 'band' }]}
            yAxis={[{ scaleType: 'linear' }]}
            series={[{ data: data.map((item: any) => item.value), label: label }]}
            width={width}
            height={height}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className={className}>
      {title &&
        <Typography variant="h6"  sx={{ textAlign: 'center', mb: 2, width: '100%'}}>
          {title}
        </Typography>}
      {renderChart()}
    </div>
  );
};

export default Charts;
