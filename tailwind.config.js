module.exports = {
  content: ["./apylaas/**/*.{html,js}"],

  theme: {
    extend: {},
  },
  variants: {
    backgroundColor: ["active", "even", "odd"],
  },
  plugins: [require("@tailwindcss/forms"), require("tailwindcss")],
};
