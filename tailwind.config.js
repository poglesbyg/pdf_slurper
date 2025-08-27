/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/presentation/web/templates/**/*.html",
    "./pdf_slurper/templates/**/*.html",
    "./web-static/**/*.html"
  ],
  theme: {
    extend: {
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in',
        'slide-up': 'slideUp 0.3s ease-out'
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' }
        },
        slideUp: {
          from: { 
            transform: 'translateY(20px)',
            opacity: '0'
          },
          to: { 
            transform: 'translateY(0)',
            opacity: '1'
          }
        }
      }
    }
  },
  plugins: []
}
