// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/agent_tui/web/templates/**/*.html",
    "./src/agent_tui/web/static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        'nb-black': '#000000',
        'nb-white': '#FFFFFF',
        'nb-pink': '#FF006E',
        'nb-blue': '#3A86FF',
        'nb-green': '#06FFA5',
        'nb-yellow': '#FFBE0B',
        'nb-purple': '#8338EC',
        'nb-orange': '#FB5607',
        'nb-bg': '#F0F0F0',
        'nb-card': '#FFFFFF',
        'nb-dark': '#11121D',
      },
      boxShadow: {
        'nb': '4px 4px 0px 0px #000000',
        'nb-sm': '2px 2px 0px 0px #000000',
        'nb-lg': '6px 6px 0px 0px #000000',
        'nb-xl': '8px 8px 0px 0px #000000',
        'nb-pink': '4px 4px 0px 0px #FF006E',
        'nb-blue': '4px 4px 0px 0px #3A86FF',
      },
      borderWidth: {
        '3': '3px',
        '4': '4px',
      },
    },
  },
  plugins: [],
}
