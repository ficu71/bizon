/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "#0a0a0c",
                panel: "rgba(255, 255, 255, 0.03)",
                accent: "#3b82f6",
                "accent-dark": "#2563eb",
            },
            backgroundImage: {
                "glass-gradient": "linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%)",
            },
            backdropBlur: {
                xs: "2px",
            }
        },
    },
    plugins: [],
}
