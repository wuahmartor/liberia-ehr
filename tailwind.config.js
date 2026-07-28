module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./static/src/js/**/*.js",
  ],

  theme: {
    extend: {
      colors: {
        ehr: {
          50: "#effcfb",
          100: "#d5f6f2",
          500: "#0f9f8f",
          700: "#087368",
          800: "#075d57",
          900: "#064b47",
          950: "#033c3a",
        },
      },

      boxShadow: {
        panel:
          "0 1px 3px rgb(15 23 42 / 0.08), 0 1px 2px rgb(15 23 42 / 0.06)",
      },
    },
  },

  plugins: [
    require("@tailwindcss/forms"),
  ],
};