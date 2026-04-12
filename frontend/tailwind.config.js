/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        sapa: {
          blue: '#1d4ed8',
          red: '#dc2626',
        },
      },
    },
  },
  plugins: [],
}
