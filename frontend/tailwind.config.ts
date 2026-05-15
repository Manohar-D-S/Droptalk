import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        deepBlue: "#0B3C5D",
        teal: "#007C91",
        cyanAccent: "#00B8D9"
      }
    }
  },
  plugins: []
} satisfies Config;
