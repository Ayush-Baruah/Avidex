import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Any request the browser makes to /api/... on the Vite dev server
      // (port 5173) is forwarded to Flask on 8001. This is the dev-time
      // stand-in for the nginx rule we'll write on the server.
      '/api': 'http://localhost:8001',
    },
  },
})

