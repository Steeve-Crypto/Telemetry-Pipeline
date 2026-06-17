/** Recharts palette aligned with Fable design tokens */

export const CHART_COLORS = {
  temperature: "#2a6b5e",
  pressure: "#4a7c8c",
  vibration: "#c26b4a",
  grid: "#e8e4de",
  axis: "#6b6560",
  tooltipBg: "#ffffff",
  tooltipBorder: "#e8e4de",
  sparkline: {
    default: "#2a6b5e",
    accent: "#2a6b5e",
    alert: "#c26b4a",
  },
} as const;

export const SERIES_META = [
  { key: "temperature" as const, label: "Temperature", unit: "°C", color: CHART_COLORS.temperature },
  { key: "pressure" as const, label: "Pressure", unit: "bar", color: CHART_COLORS.pressure },
  { key: "vibration" as const, label: "Vibration", unit: "mm/s", color: CHART_COLORS.vibration },
];