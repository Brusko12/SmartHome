import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig, loadEnv } from 'vite';
import { fileURLToPath } from 'node:url';

export default defineConfig(({ mode }) => {
  const root = fileURLToPath(new URL('..', import.meta.url));
  const env = loadEnv(mode, root, 'SMARTHOME_');
  const port = Number(env.SMARTHOME_PORT ?? '8000');
  if (!Number.isInteger(port) || port < 1024 || port > 65535) {
    throw new Error('SMARTHOME_PORT must be an integer between 1024 and 65535');
  }
  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      proxy: { '/api': { target: `http://127.0.0.1:${port}` } },
    },
  };
});
