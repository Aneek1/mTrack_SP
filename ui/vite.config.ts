import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/test_case_result': 'http://127.0.0.1:8765',
      '/load_result': 'http://127.0.0.1:8765',
      '/session_result': 'http://127.0.0.1:8765',
      '/history_result': 'http://127.0.0.1:8765',
      '/current_test_case': 'http://127.0.0.1:8765',
    }
  }
})
