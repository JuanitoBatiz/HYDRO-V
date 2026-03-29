/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  // Light mode by default — no 'dark' class needed
  theme: {
    extend: {
      colors: {
        // Brand blues — warm and trustworthy, not neon
        'brand-50':  '#eff8ff',
        'brand-100': '#dbeffe',
        'brand-200': '#b9e0fd',
        'brand-300': '#7cc8fc',
        'brand-400': '#38aaf8',
        'brand-500': '#0e8de6',  // Primary action
        'brand-600': '#026fc2',
        'brand-700': '#0558a0',
        'brand-800': '#094984',
        'brand-900': '#0d3e6d',

        // Semantic — accessible, soft
        'success-bg':  '#f0fdf4',
        'success-border': '#bbf7d0',
        'success-text': '#166534',
        'success-icon': '#22c55e',

        'warning-bg':  '#fffbeb',
        'warning-border': '#fde68a',
        'warning-text': '#92400e',
        'warning-icon': '#f59e0b',

        'danger-bg':   '#fff1f2',
        'danger-border': '#fecdd3',
        'danger-text': '#9f1239',
        'danger-icon': '#f43f5e',

        'info-bg':     '#eff8ff',
        'info-border': '#bfdbfe',
        'info-text':   '#1e40af',

        // Neutral grays (high contrast on white)
        'neutral-50':  '#f8fafc',
        'neutral-100': '#f1f5f9',
        'neutral-200': '#e2e8f0',
        'neutral-300': '#cbd5e1',
        'neutral-400': '#94a3b8',
        'neutral-500': '#64748b',
        'neutral-600': '#475569',
        'neutral-700': '#334155',
        'neutral-800': '#1e293b',
        'neutral-900': '#0f172a',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        // Larger base sizes for accessibility
        'xs':   ['0.8125rem', { lineHeight: '1.25rem' }],  // 13px
        'sm':   ['0.9375rem', { lineHeight: '1.5rem' }],   // 15px
        'base': ['1.0625rem', { lineHeight: '1.625rem' }], // 17px
        'lg':   ['1.1875rem', { lineHeight: '1.75rem' }],  // 19px
        'xl':   ['1.375rem',  { lineHeight: '1.875rem' }], // 22px
        '2xl':  ['1.625rem',  { lineHeight: '2rem' }],     // 26px
        '3xl':  ['2rem',      { lineHeight: '2.375rem' }], // 32px
        '4xl':  ['2.5rem',    { lineHeight: '2.875rem' }], // 40px
        '5xl':  ['3.25rem',   { lineHeight: '1' }],        // 52px
        '6xl':  ['4rem',      { lineHeight: '1' }],        // 64px
      },
      borderRadius: {
        'xl':  '1rem',
        '2xl': '1.25rem',
        '3xl': '1.75rem',
      },
      boxShadow: {
        'card':   '0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.06)',
        'card-lg':'0 2px 8px rgba(0,0,0,0.06), 0 16px 40px rgba(0,0,0,0.08)',
        'btn':    '0 2px 4px rgba(14,141,230,0.25), 0 4px 12px rgba(14,141,230,0.15)',
        'btn-lg': '0 4px 8px rgba(14,141,230,0.3), 0 8px 20px rgba(14,141,230,0.2)',
        'focus':  '0 0 0 3px rgba(14,141,230,0.35)',
      },
      animation: {
        'rise':       'rise 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
        'wave':       'wave 6s ease-in-out infinite',
        'bounce-sm':  'bounceSm 2s ease-in-out infinite',
        'slide-down': 'slideDown 0.35s ease-out forwards',
        'fade-in':    'fadeIn 0.4s ease-out forwards',
        'pulse-ring': 'pulseRing 2s ease-out infinite',
      },
      keyframes: {
        rise: {
          '0%':   { transform: 'scaleY(0)', transformOrigin: 'bottom' },
          '100%': { transform: 'scaleY(1)', transformOrigin: 'bottom' },
        },
        wave: {
          '0%, 100%': { transform: 'translateX(-25%) rotate(0deg)', borderRadius: '40% 60% 60% 40% / 40% 40% 60% 60%' },
          '50%':      { transform: 'translateX(-25%) rotate(180deg)', borderRadius: '60% 40% 40% 60% / 60% 60% 40% 40%' },
        },
        bounceSm: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':      { transform: 'translateY(-6px)' },
        },
        slideDown: {
          '0%':   { opacity: '0', transform: 'translateY(-12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        pulseRing: {
          '0%':   { transform: 'scale(1)', opacity: '0.6' },
          '70%':  { transform: 'scale(1.6)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '0' },
        },
      },
    },
  },
  plugins: [],
};
