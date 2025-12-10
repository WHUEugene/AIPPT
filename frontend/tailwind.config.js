/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 北大典雅配色方案
        pku: {
          red: '#8B0012',
          redHover: '#6d000e',
          black: '#000000',
          charcoal: '#333333',
          gray: '#708090',
          light: '#F5F5F5',
          paper: '#FFFFFF',
        }
      },
      fontFamily: {
        serif: ['"Source Han Serif CN"', '"FangSong"', '"Times New Roman"', 'serif'],
        sans: ['"Source Han Sans CN"', '"Microsoft YaHei"', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        academic: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
        float: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
      }
    },
  },
  plugins: [],
};
