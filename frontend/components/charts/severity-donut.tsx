"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { CHART_COLORS } from "@/lib/chart-theme";
import type { AnomalyScore } from "@/lib/types";

const SEVERITY_COLORS: Record<string, string> = {
  low: CHART_COLORS.axis,
  medium: "#c9a227",
  high: CHART_COLORS.vibration,
  critical: "#8b2e2e",
};

interface SeverityDonutProps {
  anomalies: AnomalyScore[];
}

export function SeverityDonut({ anomalies }: SeverityDonutProps) {
  const counts = anomalies.reduce<Record<string, number>>((acc, item) => {
    acc[item.severity] = (acc[item.severity] ?? 0) + 1;
    return acc;
  }, {});

  const data = Object.entries(counts).map(([name, value]) => ({ name, value }));

  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center rounded-input bg-canvas/60 text-sm text-muted">
        No anomalies to chart
      </div>
    );
  }

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={52}
            outerRadius={72}
            paddingAngle={2}
            stroke="none"
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={SEVERITY_COLORS[entry.name] ?? CHART_COLORS.axis} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: CHART_COLORS.tooltipBg,
              border: `1px solid ${CHART_COLORS.tooltipBorder}`,
              borderRadius: 8,
              fontSize: 12,
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}