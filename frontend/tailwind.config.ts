import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#EFF5FF",
          100: "#DCE8FF",
          200: "#B9D1FF",
          300: "#8DB3FF",
          400: "#5C8DFA",
          500: "#3B6FF6",
          600: "#2457E8",
          700: "#1A44C2",
          800: "#152F87",
          900: "#0B1B4D",
          950: "#070F2E",
        },
        accent: { 300: "#67E8F9", 400: "#22D3EE", 500: "#06B6D4" },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(11,27,77,0.04), 0 12px 32px rgba(11,27,77,0.06)",
        glow: "0 0 0 1px rgba(59,111,246,0.15), 0 24px 60px -12px rgba(36,87,232,0.45)",
      },
      keyframes: {
        "fade-up": { from: { opacity: "0", transform: "translateY(16px)" }, to: { opacity: "1", transform: "none" } },
        float: { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-10px)" } },
        drift: { "0%,100%": { transform: "translate(0,0) scale(1)" }, "50%": { transform: "translate(30px,-20px) scale(1.08)" } },
        flow: { from: { left: "0%" }, to: { left: "100%" } },
        "gradient-x": { "0%,100%": { backgroundPosition: "0% 50%" }, "50%": { backgroundPosition: "100% 50%" } },
        pulse2: { "0%,100%": { opacity: "1" }, "50%": { opacity: ".45" } },
      },
      animation: {
        "fade-up": "fade-up .7s cubic-bezier(.22,1,.36,1) both",
        float: "float 6s ease-in-out infinite",
        drift: "drift 14s ease-in-out infinite",
        flow: "flow 3.2s linear infinite",
        "gradient-x": "gradient-x 8s ease infinite",
        pulse2: "pulse2 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
