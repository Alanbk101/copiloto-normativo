import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        papel: "#F6F5F1",
        tinta: "#111110",
        guinda: "#6E1423",
        linea: "#D8D4CC",
        masa: "#3A3530",
        cita: "#EDECE7",
      },
      fontFamily: {
        serif: ["var(--font-spectral)", "Georgia", "serif"],
        sans: ["var(--font-ibm-plex-sans)", "system-ui", "sans-serif"],
      },
      animation: {
        "fade-up": "fade-up 0.3s ease-out both",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
