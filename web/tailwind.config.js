module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#0b2545'
        },
        accent: {
          DEFAULT: '#006d77'
        }
      },
      borderRadius: {
        lg: '0.75rem'
      }
    }
  },
  plugins: [],
}
