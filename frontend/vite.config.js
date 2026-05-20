import { defineConfig } from "vite";

export default defineConfig({
  server: {
    host: true,
    port: 5178,
    proxy: {
      "/api": {
        target: "http://api-gateway:8420",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});