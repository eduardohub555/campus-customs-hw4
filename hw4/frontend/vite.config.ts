import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The FastAPI backend owns /api (catalogue + chat) and /media (product photos).
// Proxying both keeps the browser on one origin during development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/api': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
    },
  },
})
