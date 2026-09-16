/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Space Grotesk"', 'system-ui', '-apple-system', 'sans-serif'],
        panchang: ['Panchang', '"Space Grotesk"', 'sans-serif'],
      },
      colors: {
        surface: {
          DEFAULT: '#f7f9fb',
          dim: '#d8dadc',
          bright: '#f7f9fb',
          container: {
            lowest: '#ffffff',
            low: '#f2f4f6',
            DEFAULT: '#eceef0',
            high: '#e6e8ea',
            highest: '#e0e3e5',
          },
        },
        'on-surface': {
          DEFAULT: '#191c1e',
          variant: '#464555',
        },
        primary: {
          DEFAULT: '#3525cd',
          container: '#4f46e5',
          fixed: {
            DEFAULT: '#e2dfff',
            dim: '#c3c0ff',
          },
        },
        'on-primary': {
          DEFAULT: '#ffffff',
          container: '#dad7ff',
          fixed: '#0f0069',
        },
        'inverse-primary': '#c3c0ff',
        secondary: {
          DEFAULT: '#565e74',
          container: '#dae2fd',
          fixed: {
            DEFAULT: '#dae2fd',
            dim: '#bec6e0',
          },
        },
        'on-secondary': {
          DEFAULT: '#ffffff',
          container: '#5c647a',
          fixed: {
            DEFAULT: '#131b2e',
            variant: '#3f465c',
          },
        },
        tertiary: {
          DEFAULT: '#004d70',
          container: '#006693',
          fixed: {
            DEFAULT: '#c9e6ff',
            dim: '#89ceff',
          },
        },
        'on-tertiary': {
          DEFAULT: '#ffffff',
          container: '#b8e0ff',
          fixed: '#001e2f',
        },
        error: {
          DEFAULT: '#ba1a1a',
          container: '#ffdad6',
        },
        'on-error': {
          DEFAULT: '#ffffff',
          container: '#93000a',
        },
        outline: {
          DEFAULT: '#777587',
          variant: '#c7c4d8',
        },
        'inverse-surface': '#2d3133',
        'inverse-on-surface': '#eff1f3',
        clinical: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
        accent: {
          blue: '#0284c7',
          teal: '#0d9488',
          cyan: '#06b6d4',
          amber: '#d97706',
        }
      },
      spacing: {
        'space-xs': '0.25rem',
        'space-sm': '0.5rem',
        'space-md': '1rem',
        'space-lg': '1.5rem',
        'space-xl': '2rem',
      },
    },
  },
  plugins: [],
}
