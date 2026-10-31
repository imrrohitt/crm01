import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The API runs on :8000; proxying /api avoids CORS in development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/profile-pictures': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
