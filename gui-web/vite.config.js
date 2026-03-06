import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const LOCAL_HOST = '127.0.0.1'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: LOCAL_HOST,
    port: 3000,
    proxy: {
      '/api': {
        target: `http://${LOCAL_HOST}:8000`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  preview: {
    host: LOCAL_HOST
  }
})
