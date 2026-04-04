/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
  	extend: {
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)',
  			'crucib-sm': '8px',
  			'crucib-md': '10px',
  			'crucib-lg': '12px',
  			'crucib-xl': '16px'
  		},
  		colors: {
  			bg: { 0: "#0B0D10", 1: "#111418", 2: "#171B20", 3: "#1E242B" },
  			text: { strong: "#F3F5F7", primary: "#D7DCE1", secondary: "#9AA3AD", muted: "#707984" },
  			border: { 1: "#242B33", 2: "#313A45" },
  			state: { success: "#3FB950", warning: "#D29922", error: "#F85149", info: "#58A6FF" },
  			accent: { primary: "#8B949E" },
  			kimi: {
  				bg: 'var(--kimi-bg)',
  				'elevated': 'var(--kimi-bg-elevated)',
  				card: 'var(--kimi-bg-card)',
  				input: 'var(--kimi-bg-input)',
  				text: 'var(--kimi-text)',
  				muted: 'var(--kimi-text-muted)',
  				secondary: 'var(--kimi-text-secondary)',
  				accent: 'var(--kimi-accent)',
  				border: 'var(--kimi-border)'
  			},
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		boxShadow: {
  			panel: '0 0 0 1px rgba(255,255,255,0.03), 0 8px 24px rgba(0,0,0,0.28)'
  		},
  		fontFamily: {
  			sans: ['Inter', 'system-ui', 'sans-serif'],
  			mono: ['JetBrains Mono', 'Consolas', 'monospace']
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		},
  		fontSize: {
  			'kimi-hero': ['clamp(2.5rem, 5vw, 4rem)', { lineHeight: '1.1' }],
  			'kimi-section': ['1.875rem', { lineHeight: '1.2' }],
  			'kimi-card': ['1.125rem', { lineHeight: '1.3' }],
  			'kimi-body': ['1rem', { lineHeight: '1.6' }],
  			'kimi-nav': ['0.875rem', { lineHeight: '1.4' }]
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};
