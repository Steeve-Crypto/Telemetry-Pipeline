"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CHART_COLORS } from "@/lib/chart-theme";
import type { AnomalyScore } from "@/lib/types";

interface MethodBreakdownChartProps {
  anomaly: AnomalyScore;
}

export function MethodBreakdownChart({ anomaly }: MethodBreakdownChartProps) {
  const methods = Object.entries(anomaly.methods ?? {})
    .filter(([key]) => !key.startsWith("if_") && !key.startsWith("ae_") && !key.startsWith("rule_"))
    .map(([name, score]) => ({ name, score }));

  if (methods.length === 0) {
    return null;
  }

  return (
    <div className="h-28 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={methods} layout="vertical" margin={{ left: 0, right: 8, top: 0, bottom: 0 }}>
          <CartesianGrid stroke={CHART_COLORS.grid} horizontal={false} strokeDasharray="3 3" />
          <XAxis type="number" domain={[0, 1]} hide />
          <YAxis
            type="category"
            dataKey="name"
            width={88}
            tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: CHART_COLORS.tooltipBg,
              border: `1px solid ${CHART_COLORS.tooltipBorder}`,
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value: number) => [value.toFixed(2), "score"]}
          />
          <Bar dataKey="score" fill={CHART_COLORS.alert} radius={[0, 4, 4, 0]} barSize={10} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}