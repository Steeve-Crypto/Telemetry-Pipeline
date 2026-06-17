"use client";

import { Area, AreaChart, ResponsiveContainer } from "recharts";

import { CHART_COLORS } from "@/lib/chart-theme";
import { cn } from "@/lib/utils";

interface SparklineProps {
  data: number[];
  color?: keyof typeof CHART_COLORS.sparkline;
  className?: string;
}

export function Sparkline({ data, color = "default", className }: SparklineProps) {
  if (data.length < 2) {
    return (
      <div
        className={cn("h-10 rounded-input bg-canvas/80", className)}
        aria-hidden
      />
    );
  }

  const stroke = CHART_COLORS.sparkline[color];
  const points = data.map((value, index) => ({ index, value }));

  return (
    <div className={cn("h-10 w-full", className)} aria-hidden>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={points} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`spark-${color}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={stroke} stopOpacity={0.28} />
              <stop offset="100%" stopColor={stroke} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={stroke}
            strokeWidth={1.5}
            fill={`url(#spark-${color})`}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}