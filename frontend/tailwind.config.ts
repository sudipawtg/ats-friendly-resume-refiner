import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        apple: {
          bg: "#F7F7FA",
          "bg-elevated": "#FBFBFD",
          surface: "#FFFFFF",
          "surface-secondary": "#F3F3F8",
          "surface-tertiary": "#E8E8EF",
          sidebar: "rgba(252, 252, 254, 0.88)",
          separator: "#E2E2EA",
          "separator-opaque": "#D4D4DE",
          label: "#12121A",
          "label-secondary": "#64647A",
          "label-tertiary": "#9898A8",
          blue: "#007AFF",
          "blue-hover": "#0071E3",
          green: "#22C55E",
          orange: "#F59E0B",
          red: "#EF4444",
          purple: "#8B5CF6",
          indigo: "#6366F1",
          teal: "#14B8A6",
          fill: "#78788026",
          "fill-secondary": "#7878801A",
          "fill-tertiary": "#76768014",
        },
        brand: {
          50: "#EEF2FF",
          100: "#E0E7FF",
          200: "#C7D2FE",
          300: "#A5B4FC",
          400: "#818CF8",
          500: "#6366F1",
          600: "#4F46E5",
          700: "#4338CA",
          800: "#3730A3",
          accent: "#7C3AED",
          glow: "#A78BFA",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Text",
          "SF Pro Display",
          "Helvetica Neue",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
      },
      fontSize: {
        "apple-large-title": ["2.125rem", { lineHeight: "2.5rem", fontWeight: "700", letterSpacing: "-0.02em" }],
        "apple-title-1": ["1.75rem", { lineHeight: "2.125rem", fontWeight: "600", letterSpacing: "-0.02em" }],
        "apple-title-2": ["1.375rem", { lineHeight: "1.75rem", fontWeight: "600", letterSpacing: "-0.01em" }],
        "apple-headline": ["1.0625rem", { lineHeight: "1.375rem", fontWeight: "600" }],
        "apple-body": ["1.0625rem", { lineHeight: "1.47059", fontWeight: "400" }],
        "apple-callout": ["1rem", { lineHeight: "1.3125rem", fontWeight: "400" }],
        "apple-subheadline": ["0.9375rem", { lineHeight: "1.25rem", fontWeight: "400" }],
        "apple-footnote": ["0.8125rem", { lineHeight: "1.125rem", fontWeight: "400" }],
        "apple-caption": ["0.75rem", { lineHeight: "1rem", fontWeight: "400" }],
      },
      borderRadius: {
        apple: "10px",
        "apple-lg": "12px",
        "apple-xl": "16px",
      },
      boxShadow: {
        apple: "0 1px 2px rgba(18, 18, 26, 0.04), 0 1px 3px rgba(18, 18, 26, 0.06)",
        "apple-md": "0 4px 20px rgba(18, 18, 26, 0.06), 0 1px 4px rgba(18, 18, 26, 0.04)",
        "apple-lg": "0 12px 40px rgba(18, 18, 26, 0.08), 0 2px 8px rgba(18, 18, 26, 0.04)",
        brand: "0 4px 14px rgba(99, 102, 241, 0.28), 0 1px 3px rgba(99, 102, 241, 0.12)",
        "brand-soft": "0 8px 24px rgba(99, 102, 241, 0.12)",
        logo: "0 2px 8px rgba(79, 70, 229, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.2)",
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #6366F1 0%, #7C3AED 100%)",
        "brand-gradient-soft": "linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(124, 58, 237, 0.06) 100%)",
        "surface-gradient": "linear-gradient(180deg, #FFFFFF 0%, #FAFAFC 100%)",
        "app-mesh":
          "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.07), transparent), radial-gradient(ellipse 60% 40% at 100% 0%, rgba(124, 58, 237, 0.05), transparent)",
      },
      spacing: {
        sidebar: "260px",
      },
    },
  },
  plugins: [],
};

export default config;
