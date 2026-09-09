/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        luxury: {
          bg: '#09090b',       // Deep zinc black
          card: '#121215',     // Dark slate card
          elevated: '#18181b', // Elevated surface
          border: '#27272a',   // Subtle frosted border
          gold: '#f59e0b',     // Amber gold accent
          goldLight: '#fbbf24',
          emerald: '#10b981',  // In-stock green
          rose: '#f43f5e',     // Out-of-stock red
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        serif: ['Playfair Display', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glow-gold': '0 0 20px -5px rgba(245, 158, 11, 0.15)',
        'glow-emerald': '0 0 15px -3px rgba(16, 185, 129, 0.2)',
      }
    },
  },
  plugins: [],
}
