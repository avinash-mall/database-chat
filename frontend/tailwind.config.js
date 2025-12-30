/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'vanna-navy': '#023d60',
                'vanna-cream': '#e7e1cf',
                'vanna-teal': '#15a8a8',
                'vanna-orange': '#fe5d26',
                'vanna-magenta': '#bf1363',
            },
            fontFamily: {
                sans: ['Space Grotesk', 'ui-sans-serif', 'system-ui'],
                serif: ['Roboto Slab', 'ui-serif', 'Georgia'],
                mono: ['Space Mono', 'ui-monospace', 'monospace'],
            },
        },
    },
    plugins: [],
}
