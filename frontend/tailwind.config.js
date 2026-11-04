/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        fintech: {
          dark: '#0B0F19',
          card: '#111827',
          border: '#1F2937',
          accent: '#0D9488', // Teal accent
          accentHover: '#0F766E',
          income: '#10B981',
          expense: '#EF4444',
          transfer: '#6366F1',
          warning: '#F59E0B'
        }
      }
    },
  },
  plugins: [],
}
