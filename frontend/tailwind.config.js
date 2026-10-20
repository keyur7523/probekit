import colors from 'tailwindcss/colors'

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // Apple-style tokens: the app's existing classes pick these up without page edits
      colors: {
        gray: colors.neutral,
        // indigo is the app's accent; remapped to Apple system blue (#007AFF at 600)
        indigo: {
          50: '#eef6ff',
          100: '#d9ebff',
          200: '#b3d7ff',
          300: '#80bdff',
          400: '#4da3ff',
          500: '#1a8cff',
          600: '#007aff',
          700: '#0062cc',
          800: '#004a99',
          900: '#003166',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"SF Pro Text"', 'system-ui', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', 'sans-serif'],
      },
      borderRadius: {
        lg: '0.75rem',
        xl: '1.125rem',
      },
      boxShadow: {
        sm: '0 1px 2px rgb(0 0 0 / 0.04), 0 2px 10px rgb(0 0 0 / 0.04)',
        lg: '0 4px 12px rgb(0 0 0 / 0.06), 0 16px 40px rgb(0 0 0 / 0.08)',
      },
    },
  },
  plugins: [],
}
