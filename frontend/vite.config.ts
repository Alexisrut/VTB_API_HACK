import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Needed for Docker
    port: 5173,
    watch: {
      usePolling: true, // Needed for Docker on some systems
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://app:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/auth': {
        target: process.env.VITE_API_URL || 'http://app:8000',
        changeOrigin: true,
      },
      '/users': {
        target: process.env.VITE_API_URL || 'http://app:8000',
        changeOrigin: true,
      }
    }
  }
})
