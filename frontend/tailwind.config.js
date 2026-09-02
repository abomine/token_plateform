/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#05070b",
          900: "#0a0f16",
          800: "#121925",
          700: "#1a2433",
          600: "#243044",
        },
        mist: {
          100: "#e8eef7",
          300: "#9db0c9",
          500: "#6b829e",
        },
        signal: {
          DEFAULT: "#3ddc97",
          dim: "#1f8f63",
          glow: "rgba(61, 220, 151, 0.18)",
        },
        warn: "#ff8a5b",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        panel: "0 0 0 1px rgba(157, 176, 201, 0.08), 0 24px 60px rgba(0,0,0,0.45)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
        balancePop: {
          "0%": { transform: "scale(1)" },
          "40%": { transform: "scale(1.06)" },
          "100%": { transform: "scale(1)" },
        },
      },
      animation: {
        rise: "rise 0.45s ease-out both",
        pulseSoft: "pulseSoft 1.4s ease-in-out infinite",
        balancePop: "balancePop 0.55s ease-out",
      },
    },
  },
  plugins: [],
};
