/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      // Custom breakpoints for all device sizes
      screens: {
        'xs': '320px',      // Extra small phones
        'sm': '480px',      // Small phones
        'md': '768px',      // Tablets (iPad mini)
        'lg': '1024px',     // Tablets (iPad) / Small laptops
        'xl': '1280px',     // Laptops
        '2xl': '1536px',    // Large desktops
        '3xl': '1920px',    // Full HD displays
        '4xl': '2560px',    // 2K displays
        'tv': '3840px',     // 4K TVs
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      },
      colors: {},
      // Responsive font sizes
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
        '5xl': ['3rem', { lineHeight: '1' }],
      },
      // Touch-friendly spacing
      spacing: {
        'touch': '44px',  // Minimum touch target size
      }
    }
  },
  plugins: [require("tailwindcss-animate")],
}
