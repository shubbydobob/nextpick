import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // `.env`/`.env.[mode]`에서 API_TARGET 로드. serve:prd(=--mode prd)면 .env.prd의 운영 백엔드로 프록시.
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.API_TARGET || process.env.API_TARGET || 'http://localhost:8080'
  return {
    plugins: [react()],
    build: {
      rollupOptions: {
        output: {
          // 무거운 라이브러리를 vendor 청크로 분리 → 앱 코드 변경 시 캐시 유지 + 초기 병렬 로드.
          manualChunks(id: string) {
            if (id.includes('node_modules')) {
              if (id.includes('recharts') || id.includes('d3-')) return 'vendor-charts'
              if (id.includes('react')) return 'vendor-react'
            }
          },
        },
      },
    },
    server: {
      port: Number(process.env.PORT) || 3000,
      proxy: {
        // 기본: 로컬 백엔드(8080). serve:prd면 EC2 운영 백엔드(nginx 80 → 운영 DB)로 프록시.
        '/api': { target: apiTarget, changeOrigin: true },
      },
    },
  }
})
