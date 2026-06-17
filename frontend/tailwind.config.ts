import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "rgb(var(--color-canvas) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        border: "rgb(var(--color-border) / <alpha-value>)",
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        muted: "rgb(var(--color-muted) / <alpha-value>)",
        accent: "rgb(var(--color-accent) / <alpha-value>)",
        alert: "rgb(var(--color-alert) / <alpha-value>)",
        severity: {
          low: "rgb(var(--color-severity-low) / <alpha-value>)",
          medium: "rgb(var(--color-severity-medium) / <alpha-value>)",
          high: "rgb(var(--color-severity-high) / <alpha-value>)",
          critical: "rgb(var(--color-severity-critical) / <alpha-value>)",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      borderRadius: {
        card: "12px",
        input: "8px",
        pill: "999px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(26, 24, 20, 0.04), 0 8px 24px rgba(26, 24, 20, 0.06)",
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-out motion-reduce:transition-none",
        "count-up": "countUp 0.6s ease-out motion-reduce:transition-none",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        countUp: {
          "0%": { opacity: "0.6" },
          "100%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;