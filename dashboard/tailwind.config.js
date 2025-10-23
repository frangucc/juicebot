/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        teal: {
          DEFAULT: '#2cae96',
          50: '#e6f7f4',
          100: '#b3e8dd',
          200: '#80d9c6',
          300: '#4dcaaf',
          400: '#2cae96',
          500: '#1f8a77',
          600: '#196b5e',
          700: '#134c45',
          800: '#0c2d2b',
          900: '#060f12',
          light: '#3dd9bd',
          dark: '#1f8a77',
        },
        card: {
          DEFAULT: '#191d27',
          hover: '#1f2430',
        },
      },
      backgroundColor: {
        'glass': 'rgba(44, 174, 150, 0.08)',
        'glass-hover': 'rgba(44, 174, 150, 0.12)',
      },
      borderColor: {
        'glass': 'rgba(44, 174, 150, 0.2)',
      },
      boxShadow: {
        'glow-sm': '0 0 10px rgba(44, 174, 150, 0.3)',
        'glow-md': '0 0 20px rgba(44, 174, 150, 0.3)',
        'glow-lg': '0 0 30px rgba(44, 174, 150, 0.4)',
      },
    },
  },
  plugins: [],
}
