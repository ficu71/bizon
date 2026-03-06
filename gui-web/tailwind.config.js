/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                bgVoid: "#05030B",
                bgDeep: "#0B0A1A",
                bgSurface: "#101225",
                neonCyan: "#35F3FF",
                neonPink: "#FF2BD6",
                cyberYellow: "#FFD84D",
                toxicLime: "#B8FF5C",
                electricPurple: "#9D4DFF",
                dangerHot: "#FF5A7A",
                textMain: "#EEF3FF",
                textDim: "#9AA8C7",
            },
            boxShadow: {
                "neon-cyan": "0 0 0 1px rgba(53,243,255,.35), 0 0 24px rgba(53,243,255,.22)",
                "neon-pink": "0 0 0 1px rgba(255,43,214,.35), 0 0 24px rgba(255,43,214,.22)",
                "pixel-frame": "inset 0 0 0 1px rgba(255,255,255,.04), 0 0 0 1px rgba(53,243,255,.14)",
            },
            backgroundImage: {
                "glass-gradient": "linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%)",
                "neon-radial": "radial-gradient(circle at 20% 10%, rgba(53,243,255,.18), transparent 34%), radial-gradient(circle at 88% 20%, rgba(255,43,214,.16), transparent 36%)",
                "crt-lines": "repeating-linear-gradient(180deg, rgba(255,255,255,var(--fx-scan-opacity)) 0 1px, transparent 1px 3px)",
                "cyber-grid": "url('/src/assets/neon-grid-bg.svg')",
            },
            fontFamily: {
                sans: ["Space Grotesk", "Avenir Next", "Segoe UI", "sans-serif"],
                mono: ["IBM Plex Mono", "SFMono-Regular", "Menlo", "monospace"],
                display: ["VT323", "monospace"],
            },
            keyframes: {
                "glitch-shift": {
                    "0%, 100%": { transform: "translateX(0)" },
                    "20%": { transform: "translateX(var(--fx-glitch-amp))" },
                    "40%": { transform: "translateX(calc(var(--fx-glitch-amp) * -1))" },
                    "60%": { transform: "translateX(calc(var(--fx-glitch-amp) * .5))" },
                },
                "crt-flicker": {
                    "0%, 100%": { opacity: "1" },
                    "50%": { opacity: ".94" },
                },
                "neon-pulse": {
                    "0%, 100%": { boxShadow: "0 0 0 rgba(53,243,255,0)" },
                    "50%": { boxShadow: "0 0 18px rgba(53,243,255,.36)" },
                },
                "micro-jitter": {
                    "0%, 100%": { transform: "translate(0,0)" },
                    "25%": { transform: "translate(-1px, 1px)" },
                    "75%": { transform: "translate(1px, -1px)" },
                },
            },
            animation: {
                glitch: "glitch-shift .45s steps(2, end)",
                flicker: "crt-flicker var(--fx-flicker-speed) linear infinite",
                pulseNeon: "neon-pulse 2.6s ease-in-out infinite",
                jitter: "micro-jitter .2s linear",
            },
            backdropBlur: {
                xs: "2px",
            }
        },
    },
    plugins: [],
}
