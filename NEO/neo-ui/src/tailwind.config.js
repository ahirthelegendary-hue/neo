export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        neonCyan: "#00ffff",
        neonPurple: "#9f00ff",
        glass: "rgba(255,255,255,0.05)"
      },
      boxShadow: {
        neon: "0 0 10px #00ffff, 0 0 20px #9f00ff"
      },
      backdropBlur: {
        xs: "4px"
      }
    },
  },
  plugins: [],
}