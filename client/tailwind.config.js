/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme palette based on screenshots
        'dark': {
          'primary': '#0A0E1A',    // Very dark blue-black background
          'secondary': '#141B2D',  // Dark blue-gray
          'card': '#1E293B',       // Card background
          'border': '#2D3748',     // Border color
          'hover': '#252F43',      // Hover state
        },
        'accent': {
          'blue': '#60A5FA',       // Primary blue
          'purple': '#A78BFA',     // Purple accent
          'green': '#10B981',      // Success green
          'orange': '#F59E0B',     // Warning orange
          'red': '#EF4444',        // Error red
        },
        'text': {
          'primary': '#E5E7EB',    // Light gray text
          'secondary': '#9CA3AF',  // Medium gray text
          'tertiary': '#6B7280',   // Darker gray text
        }
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)',
        'card-hover': '0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3)',
      },
      backdropBlur: {
        'glass': '12px',
      }
    },
  },
  plugins: [],
}
