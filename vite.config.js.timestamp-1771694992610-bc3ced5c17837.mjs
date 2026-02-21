// vite.config.js
import { defineConfig } from "file:///home/ubuntu/Ops-Center-OSS/node_modules/.pnpm/vite@5.4.21_@types+node@25.0.10_terser@5.46.0/node_modules/vite/dist/node/index.js";
import react from "file:///home/ubuntu/Ops-Center-OSS/node_modules/.pnpm/@vitejs+plugin-react@4.7.0_vite@5.4.21_@types+node@25.0.10_terser@5.46.0_/node_modules/@vitejs/plugin-react/dist/index.js";
import { VitePWA } from "file:///home/ubuntu/Ops-Center-OSS/node_modules/.pnpm/vite-plugin-pwa@1.2.0_vite@5.4.21_@types+node@25.0.10_terser@5.46.0__workbox-build@7.4._19d8193f4115fe14f63713809ee0e2d8/node_modules/vite-plugin-pwa/dist/index.js";
import { visualizer } from "file:///home/ubuntu/Ops-Center-OSS/node_modules/.pnpm/rollup-plugin-visualizer@6.0.5_rollup@2.79.2/node_modules/rollup-plugin-visualizer/dist/plugin/index.js";
import { imagetools } from "file:///home/ubuntu/Ops-Center-OSS/node_modules/.pnpm/vite-imagetools@9.0.2_rollup@2.79.2/node_modules/vite-imagetools/dist/index.js";
var vite_config_default = defineConfig({
  plugins: [
    react({
      // Ensure React loads first
      babel: {
        plugins: []
      }
    }),
    // Image optimization - generates WebP variants
    imagetools({
      defaultDirectives: (url) => {
        if (url.pathname.includes("/logos/")) {
          return new URLSearchParams({
            format: "webp",
            quality: "80"
          });
        }
        return new URLSearchParams();
      }
    }),
    // Bundle analyzer - generates stats.html after build
    visualizer({
      open: false,
      gzipSize: true,
      brotliSize: true,
      filename: "dist/stats.html"
    }),
    VitePWA({
      disable: true,
      // Temporarily disable PWA to force cache refresh
      registerType: "prompt",
      // Changed from autoUpdate to prompt for manual control
      injectRegister: false,
      // Disable automatic SW registration
      includeAssets: ["favicon.ico", "robots.txt", "logos/**/*.png", "logos/**/*.svg"],
      manifest: {
        name: "Ops-Center - UC-Cloud Management",
        short_name: "Ops-Center",
        description: "UC-Cloud Operations and Management Dashboard",
        theme_color: "#7c3aed",
        background_color: "#0f172a",
        display: "standalone",
        orientation: "portrait",
        scope: "/",
        start_url: "/",
        icons: [
          {
            src: "/logos/uc-logo-192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "any maskable"
          },
          {
            src: "/logos/uc-logo-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any maskable"
          }
        ]
      },
      workbox: {
        // Increase cache size limit for large bundles
        maximumFileSizeToCacheInBytes: 10 * 1024 * 1024,
        // 10 MB
        // Cache all static assets (exclude bundle analyzer stats)
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2,woff,ttf,eot}"],
        globIgnores: ["**/stats.html", "**/node_modules/**"],
        // Runtime caching strategies
        runtimeCaching: [
          {
            // API responses - Network First (fresh data priority)
            urlPattern: /^https?:\/\/your-domain.com\/api\/.*/i,
            handler: "NetworkFirst",
            options: {
              cacheName: "api-cache",
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 5
                // 5 minutes
              },
              cacheableResponse: {
                statuses: [0, 200]
              },
              networkTimeoutSeconds: 10
            }
          },
          {
            // Static API data (rarely changes) - Cache First
            urlPattern: /^https?:\/\/your-domain.com\/api\/v1\/(system\/status|service-urls|deployment\/config)/i,
            handler: "CacheFirst",
            options: {
              cacheName: "static-api-cache",
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 60
                // 1 hour
              }
            }
          },
          {
            // External fonts - Cache First (rarely changes)
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: "CacheFirst",
            options: {
              cacheName: "google-fonts-cache",
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365
                // 1 year
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          },
          {
            // Font files
            urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
            handler: "CacheFirst",
            options: {
              cacheName: "google-fonts-webfonts",
              expiration: {
                maxEntries: 30,
                maxAgeSeconds: 60 * 60 * 24 * 365
                // 1 year
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          },
          {
            // Images - Cache First with size limit
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/i,
            handler: "CacheFirst",
            options: {
              cacheName: "image-cache",
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 30
                // 30 days
              }
            }
          }
        ],
        // Clean up old caches
        cleanupOutdatedCaches: true,
        // Skip waiting to activate immediately
        skipWaiting: true,
        clientsClaim: true
      },
      // Development options
      devOptions: {
        enabled: false,
        // Disable in dev mode for easier debugging
        type: "module"
      }
    })
  ],
  server: {
    port: 8084,
    proxy: {
      "/api": {
        target: "http://localhost:8085",
        changeOrigin: true
      },
      "/ws": {
        target: "ws://localhost:8085",
        ws: true
      }
    }
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    // Increase chunk size warning limit
    chunkSizeWarningLimit: 1e3,
    // Inline assets smaller than 4KB as base64
    assetsInlineLimit: 4096,
    // Disable modulePreload to prevent wrong load order
    modulePreload: false,
    // Minification
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: true,
        // Remove console.log in production
        drop_debugger: true,
        pure_funcs: ["console.log", "console.info", "console.debug"]
      }
    },
    rollupOptions: {
      output: {
        // Ensure vendor-react loads first by making it the earliest chunk
        chunkFileNames: (chunkInfo) => {
          if (chunkInfo.name === "vendor-react") {
            return "assets/0-vendor-react-[hash].js";
          }
          return "assets/[name]-[hash].js";
        },
        // Simplified chunk splitting - bundle most things with React to ensure correct load order
        manualChunks: (id) => {
          if (id.includes("node_modules")) {
            if (id.includes("swagger-ui-react")) {
              return "vendor-swagger";
            }
            if (id.includes("redoc")) {
              return "vendor-redoc";
            }
            return "vendor-react";
          }
        }
      }
    },
    // Optimize dependencies
    commonjsOptions: {
      include: [/node_modules/],
      transformMixedEsModules: true
    }
  },
  // Dependency optimization
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-router-dom",
      "@mui/material",
      "@mui/icons-material"
    ],
    exclude: [
      "swagger-ui-react",
      // Lazy loaded
      "redoc"
      // Lazy loaded
    ]
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCIvaG9tZS91YnVudHUvT3BzLUNlbnRlci1PU1NcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIi9ob21lL3VidW50dS9PcHMtQ2VudGVyLU9TUy92aXRlLmNvbmZpZy5qc1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vaG9tZS91YnVudHUvT3BzLUNlbnRlci1PU1Mvdml0ZS5jb25maWcuanNcIjtpbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tICd2aXRlJ1xuaW1wb3J0IHJlYWN0IGZyb20gJ0B2aXRlanMvcGx1Z2luLXJlYWN0J1xuaW1wb3J0IHsgVml0ZVBXQSB9IGZyb20gJ3ZpdGUtcGx1Z2luLXB3YSdcbmltcG9ydCB7IHZpc3VhbGl6ZXIgfSBmcm9tICdyb2xsdXAtcGx1Z2luLXZpc3VhbGl6ZXInXG5pbXBvcnQgeyBpbWFnZXRvb2xzIH0gZnJvbSAndml0ZS1pbWFnZXRvb2xzJ1xuXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xuICBwbHVnaW5zOiBbXG4gICAgcmVhY3Qoe1xuICAgICAgLy8gRW5zdXJlIFJlYWN0IGxvYWRzIGZpcnN0XG4gICAgICBiYWJlbDoge1xuICAgICAgICBwbHVnaW5zOiBbXVxuICAgICAgfVxuICAgIH0pLFxuICAgIC8vIEltYWdlIG9wdGltaXphdGlvbiAtIGdlbmVyYXRlcyBXZWJQIHZhcmlhbnRzXG4gICAgaW1hZ2V0b29scyh7XG4gICAgICBkZWZhdWx0RGlyZWN0aXZlczogKHVybCkgPT4ge1xuICAgICAgICAvLyBPbmx5IHByb2Nlc3MgaW1hZ2VzIGZyb20gL2xvZ29zIGRpcmVjdG9yeVxuICAgICAgICBpZiAodXJsLnBhdGhuYW1lLmluY2x1ZGVzKCcvbG9nb3MvJykpIHtcbiAgICAgICAgICByZXR1cm4gbmV3IFVSTFNlYXJjaFBhcmFtcyh7XG4gICAgICAgICAgICBmb3JtYXQ6ICd3ZWJwJyxcbiAgICAgICAgICAgIHF1YWxpdHk6ICc4MCdcbiAgICAgICAgICB9KVxuICAgICAgICB9XG4gICAgICAgIHJldHVybiBuZXcgVVJMU2VhcmNoUGFyYW1zKClcbiAgICAgIH1cbiAgICB9KSxcbiAgICAvLyBCdW5kbGUgYW5hbHl6ZXIgLSBnZW5lcmF0ZXMgc3RhdHMuaHRtbCBhZnRlciBidWlsZFxuICAgIHZpc3VhbGl6ZXIoe1xuICAgICAgb3BlbjogZmFsc2UsXG4gICAgICBnemlwU2l6ZTogdHJ1ZSxcbiAgICAgIGJyb3RsaVNpemU6IHRydWUsXG4gICAgICBmaWxlbmFtZTogJ2Rpc3Qvc3RhdHMuaHRtbCcsXG4gICAgfSksXG4gICAgVml0ZVBXQSh7XG4gICAgICBkaXNhYmxlOiB0cnVlLCAvLyBUZW1wb3JhcmlseSBkaXNhYmxlIFBXQSB0byBmb3JjZSBjYWNoZSByZWZyZXNoXG4gICAgICByZWdpc3RlclR5cGU6ICdwcm9tcHQnLCAvLyBDaGFuZ2VkIGZyb20gYXV0b1VwZGF0ZSB0byBwcm9tcHQgZm9yIG1hbnVhbCBjb250cm9sXG4gICAgICBpbmplY3RSZWdpc3RlcjogZmFsc2UsIC8vIERpc2FibGUgYXV0b21hdGljIFNXIHJlZ2lzdHJhdGlvblxuICAgICAgaW5jbHVkZUFzc2V0czogWydmYXZpY29uLmljbycsICdyb2JvdHMudHh0JywgJ2xvZ29zLyoqLyoucG5nJywgJ2xvZ29zLyoqLyouc3ZnJ10sXG4gICAgICBtYW5pZmVzdDoge1xuICAgICAgICBuYW1lOiAnT3BzLUNlbnRlciAtIFVDLUNsb3VkIE1hbmFnZW1lbnQnLFxuICAgICAgICBzaG9ydF9uYW1lOiAnT3BzLUNlbnRlcicsXG4gICAgICAgIGRlc2NyaXB0aW9uOiAnVUMtQ2xvdWQgT3BlcmF0aW9ucyBhbmQgTWFuYWdlbWVudCBEYXNoYm9hcmQnLFxuICAgICAgICB0aGVtZV9jb2xvcjogJyM3YzNhZWQnLFxuICAgICAgICBiYWNrZ3JvdW5kX2NvbG9yOiAnIzBmMTcyYScsXG4gICAgICAgIGRpc3BsYXk6ICdzdGFuZGFsb25lJyxcbiAgICAgICAgb3JpZW50YXRpb246ICdwb3J0cmFpdCcsXG4gICAgICAgIHNjb3BlOiAnLycsXG4gICAgICAgIHN0YXJ0X3VybDogJy8nLFxuICAgICAgICBpY29uczogW1xuICAgICAgICAgIHtcbiAgICAgICAgICAgIHNyYzogJy9sb2dvcy91Yy1sb2dvLTE5Mi5wbmcnLFxuICAgICAgICAgICAgc2l6ZXM6ICcxOTJ4MTkyJyxcbiAgICAgICAgICAgIHR5cGU6ICdpbWFnZS9wbmcnLFxuICAgICAgICAgICAgcHVycG9zZTogJ2FueSBtYXNrYWJsZSdcbiAgICAgICAgICB9LFxuICAgICAgICAgIHtcbiAgICAgICAgICAgIHNyYzogJy9sb2dvcy91Yy1sb2dvLTUxMi5wbmcnLFxuICAgICAgICAgICAgc2l6ZXM6ICc1MTJ4NTEyJyxcbiAgICAgICAgICAgIHR5cGU6ICdpbWFnZS9wbmcnLFxuICAgICAgICAgICAgcHVycG9zZTogJ2FueSBtYXNrYWJsZSdcbiAgICAgICAgICB9XG4gICAgICAgIF1cbiAgICAgIH0sXG4gICAgICB3b3JrYm94OiB7XG4gICAgICAgIC8vIEluY3JlYXNlIGNhY2hlIHNpemUgbGltaXQgZm9yIGxhcmdlIGJ1bmRsZXNcbiAgICAgICAgbWF4aW11bUZpbGVTaXplVG9DYWNoZUluQnl0ZXM6IDEwICogMTAyNCAqIDEwMjQsIC8vIDEwIE1CXG5cbiAgICAgICAgLy8gQ2FjaGUgYWxsIHN0YXRpYyBhc3NldHMgKGV4Y2x1ZGUgYnVuZGxlIGFuYWx5emVyIHN0YXRzKVxuICAgICAgICBnbG9iUGF0dGVybnM6IFsnKiovKi57anMsY3NzLGh0bWwsaWNvLHBuZyxzdmcsd29mZjIsd29mZix0dGYsZW90fSddLFxuICAgICAgICBnbG9iSWdub3JlczogWycqKi9zdGF0cy5odG1sJywgJyoqL25vZGVfbW9kdWxlcy8qKiddLFxuXG4gICAgICAgIC8vIFJ1bnRpbWUgY2FjaGluZyBzdHJhdGVnaWVzXG4gICAgICAgIHJ1bnRpbWVDYWNoaW5nOiBbXG4gICAgICAgICAge1xuICAgICAgICAgICAgLy8gQVBJIHJlc3BvbnNlcyAtIE5ldHdvcmsgRmlyc3QgKGZyZXNoIGRhdGEgcHJpb3JpdHkpXG4gICAgICAgICAgICB1cmxQYXR0ZXJuOiAvXmh0dHBzPzpcXC9cXC95b3VyLWRvbWFpbi5jb21cXC9hcGlcXC8uKi9pLFxuICAgICAgICAgICAgaGFuZGxlcjogJ05ldHdvcmtGaXJzdCcsXG4gICAgICAgICAgICBvcHRpb25zOiB7XG4gICAgICAgICAgICAgIGNhY2hlTmFtZTogJ2FwaS1jYWNoZScsXG4gICAgICAgICAgICAgIGV4cGlyYXRpb246IHtcbiAgICAgICAgICAgICAgICBtYXhFbnRyaWVzOiAxMDAsXG4gICAgICAgICAgICAgICAgbWF4QWdlU2Vjb25kczogNjAgKiA1IC8vIDUgbWludXRlc1xuICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICBjYWNoZWFibGVSZXNwb25zZToge1xuICAgICAgICAgICAgICAgIHN0YXR1c2VzOiBbMCwgMjAwXVxuICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICBuZXR3b3JrVGltZW91dFNlY29uZHM6IDEwXG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSxcbiAgICAgICAgICB7XG4gICAgICAgICAgICAvLyBTdGF0aWMgQVBJIGRhdGEgKHJhcmVseSBjaGFuZ2VzKSAtIENhY2hlIEZpcnN0XG4gICAgICAgICAgICB1cmxQYXR0ZXJuOiAvXmh0dHBzPzpcXC9cXC95b3VyLWRvbWFpbi5jb21cXC9hcGlcXC92MVxcLyhzeXN0ZW1cXC9zdGF0dXN8c2VydmljZS11cmxzfGRlcGxveW1lbnRcXC9jb25maWcpL2ksXG4gICAgICAgICAgICBoYW5kbGVyOiAnQ2FjaGVGaXJzdCcsXG4gICAgICAgICAgICBvcHRpb25zOiB7XG4gICAgICAgICAgICAgIGNhY2hlTmFtZTogJ3N0YXRpYy1hcGktY2FjaGUnLFxuICAgICAgICAgICAgICBleHBpcmF0aW9uOiB7XG4gICAgICAgICAgICAgICAgbWF4RW50cmllczogNTAsXG4gICAgICAgICAgICAgICAgbWF4QWdlU2Vjb25kczogNjAgKiA2MCAvLyAxIGhvdXJcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgIH0sXG4gICAgICAgICAge1xuICAgICAgICAgICAgLy8gRXh0ZXJuYWwgZm9udHMgLSBDYWNoZSBGaXJzdCAocmFyZWx5IGNoYW5nZXMpXG4gICAgICAgICAgICB1cmxQYXR0ZXJuOiAvXmh0dHBzOlxcL1xcL2ZvbnRzXFwuZ29vZ2xlYXBpc1xcLmNvbVxcLy4qL2ksXG4gICAgICAgICAgICBoYW5kbGVyOiAnQ2FjaGVGaXJzdCcsXG4gICAgICAgICAgICBvcHRpb25zOiB7XG4gICAgICAgICAgICAgIGNhY2hlTmFtZTogJ2dvb2dsZS1mb250cy1jYWNoZScsXG4gICAgICAgICAgICAgIGV4cGlyYXRpb246IHtcbiAgICAgICAgICAgICAgICBtYXhFbnRyaWVzOiAxMCxcbiAgICAgICAgICAgICAgICBtYXhBZ2VTZWNvbmRzOiA2MCAqIDYwICogMjQgKiAzNjUgLy8gMSB5ZWFyXG4gICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgIGNhY2hlYWJsZVJlc3BvbnNlOiB7XG4gICAgICAgICAgICAgICAgc3RhdHVzZXM6IFswLCAyMDBdXG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9LFxuICAgICAgICAgIHtcbiAgICAgICAgICAgIC8vIEZvbnQgZmlsZXNcbiAgICAgICAgICAgIHVybFBhdHRlcm46IC9eaHR0cHM6XFwvXFwvZm9udHNcXC5nc3RhdGljXFwuY29tXFwvLiovaSxcbiAgICAgICAgICAgIGhhbmRsZXI6ICdDYWNoZUZpcnN0JyxcbiAgICAgICAgICAgIG9wdGlvbnM6IHtcbiAgICAgICAgICAgICAgY2FjaGVOYW1lOiAnZ29vZ2xlLWZvbnRzLXdlYmZvbnRzJyxcbiAgICAgICAgICAgICAgZXhwaXJhdGlvbjoge1xuICAgICAgICAgICAgICAgIG1heEVudHJpZXM6IDMwLFxuICAgICAgICAgICAgICAgIG1heEFnZVNlY29uZHM6IDYwICogNjAgKiAyNCAqIDM2NSAvLyAxIHllYXJcbiAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgY2FjaGVhYmxlUmVzcG9uc2U6IHtcbiAgICAgICAgICAgICAgICBzdGF0dXNlczogWzAsIDIwMF1cbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgIH0sXG4gICAgICAgICAge1xuICAgICAgICAgICAgLy8gSW1hZ2VzIC0gQ2FjaGUgRmlyc3Qgd2l0aCBzaXplIGxpbWl0XG4gICAgICAgICAgICB1cmxQYXR0ZXJuOiAvXFwuKD86cG5nfGpwZ3xqcGVnfHN2Z3xnaWZ8d2VicHxpY28pJC9pLFxuICAgICAgICAgICAgaGFuZGxlcjogJ0NhY2hlRmlyc3QnLFxuICAgICAgICAgICAgb3B0aW9uczoge1xuICAgICAgICAgICAgICBjYWNoZU5hbWU6ICdpbWFnZS1jYWNoZScsXG4gICAgICAgICAgICAgIGV4cGlyYXRpb246IHtcbiAgICAgICAgICAgICAgICBtYXhFbnRyaWVzOiAxMDAsXG4gICAgICAgICAgICAgICAgbWF4QWdlU2Vjb25kczogNjAgKiA2MCAqIDI0ICogMzAgLy8gMzAgZGF5c1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfVxuICAgICAgICBdLFxuXG4gICAgICAgIC8vIENsZWFuIHVwIG9sZCBjYWNoZXNcbiAgICAgICAgY2xlYW51cE91dGRhdGVkQ2FjaGVzOiB0cnVlLFxuXG4gICAgICAgIC8vIFNraXAgd2FpdGluZyB0byBhY3RpdmF0ZSBpbW1lZGlhdGVseVxuICAgICAgICBza2lwV2FpdGluZzogdHJ1ZSxcbiAgICAgICAgY2xpZW50c0NsYWltOiB0cnVlXG4gICAgICB9LFxuXG4gICAgICAvLyBEZXZlbG9wbWVudCBvcHRpb25zXG4gICAgICBkZXZPcHRpb25zOiB7XG4gICAgICAgIGVuYWJsZWQ6IGZhbHNlLCAvLyBEaXNhYmxlIGluIGRldiBtb2RlIGZvciBlYXNpZXIgZGVidWdnaW5nXG4gICAgICAgIHR5cGU6ICdtb2R1bGUnXG4gICAgICB9XG4gICAgfSlcbiAgXSxcbiAgc2VydmVyOiB7XG4gICAgcG9ydDogODA4NCxcbiAgICBwcm94eToge1xuICAgICAgJy9hcGknOiB7XG4gICAgICAgIHRhcmdldDogJ2h0dHA6Ly9sb2NhbGhvc3Q6ODA4NScsXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcbiAgICAgIH0sXG4gICAgICAnL3dzJzoge1xuICAgICAgICB0YXJnZXQ6ICd3czovL2xvY2FsaG9zdDo4MDg1JyxcbiAgICAgICAgd3M6IHRydWUsXG4gICAgICB9LFxuICAgIH0sXG4gIH0sXG4gIGJ1aWxkOiB7XG4gICAgb3V0RGlyOiAnZGlzdCcsXG4gICAgc291cmNlbWFwOiBmYWxzZSxcbiAgICAvLyBJbmNyZWFzZSBjaHVuayBzaXplIHdhcm5pbmcgbGltaXRcbiAgICBjaHVua1NpemVXYXJuaW5nTGltaXQ6IDEwMDAsXG4gICAgLy8gSW5saW5lIGFzc2V0cyBzbWFsbGVyIHRoYW4gNEtCIGFzIGJhc2U2NFxuICAgIGFzc2V0c0lubGluZUxpbWl0OiA0MDk2LFxuICAgIC8vIERpc2FibGUgbW9kdWxlUHJlbG9hZCB0byBwcmV2ZW50IHdyb25nIGxvYWQgb3JkZXJcbiAgICBtb2R1bGVQcmVsb2FkOiBmYWxzZSxcbiAgICAvLyBNaW5pZmljYXRpb25cbiAgICBtaW5pZnk6ICd0ZXJzZXInLFxuICAgIHRlcnNlck9wdGlvbnM6IHtcbiAgICAgIGNvbXByZXNzOiB7XG4gICAgICAgIGRyb3BfY29uc29sZTogdHJ1ZSwgLy8gUmVtb3ZlIGNvbnNvbGUubG9nIGluIHByb2R1Y3Rpb25cbiAgICAgICAgZHJvcF9kZWJ1Z2dlcjogdHJ1ZSxcbiAgICAgICAgcHVyZV9mdW5jczogWydjb25zb2xlLmxvZycsICdjb25zb2xlLmluZm8nLCAnY29uc29sZS5kZWJ1ZyddXG4gICAgICB9XG4gICAgfSxcbiAgICByb2xsdXBPcHRpb25zOiB7XG4gICAgICBvdXRwdXQ6IHtcbiAgICAgICAgLy8gRW5zdXJlIHZlbmRvci1yZWFjdCBsb2FkcyBmaXJzdCBieSBtYWtpbmcgaXQgdGhlIGVhcmxpZXN0IGNodW5rXG4gICAgICAgIGNodW5rRmlsZU5hbWVzOiAoY2h1bmtJbmZvKSA9PiB7XG4gICAgICAgICAgaWYgKGNodW5rSW5mby5uYW1lID09PSAndmVuZG9yLXJlYWN0Jykge1xuICAgICAgICAgICAgcmV0dXJuICdhc3NldHMvMC12ZW5kb3ItcmVhY3QtW2hhc2hdLmpzJzsgLy8gUHJlZml4IHdpdGggMCB0byBsb2FkIGZpcnN0XG4gICAgICAgICAgfVxuICAgICAgICAgIHJldHVybiAnYXNzZXRzL1tuYW1lXS1baGFzaF0uanMnO1xuICAgICAgICB9LFxuICAgICAgICAvLyBTaW1wbGlmaWVkIGNodW5rIHNwbGl0dGluZyAtIGJ1bmRsZSBtb3N0IHRoaW5ncyB3aXRoIFJlYWN0IHRvIGVuc3VyZSBjb3JyZWN0IGxvYWQgb3JkZXJcbiAgICAgICAgbWFudWFsQ2h1bmtzOiAoaWQpID0+IHtcbiAgICAgICAgICAvLyBOb2RlIG1vZHVsZXMgdmVuZG9yIGNodW5rc1xuICAgICAgICAgIGlmIChpZC5pbmNsdWRlcygnbm9kZV9tb2R1bGVzJykpIHtcbiAgICAgICAgICAgIC8vIFN3YWdnZXIgVUkgLSBMb2FkIG9ubHkgd2hlbiBBcGlEb2N1bWVudGF0aW9uIHRhYiAwIGlzIGFjdGl2ZSAobGF6eSBsb2FkZWQpXG4gICAgICAgICAgICBpZiAoaWQuaW5jbHVkZXMoJ3N3YWdnZXItdWktcmVhY3QnKSkge1xuICAgICAgICAgICAgICByZXR1cm4gJ3ZlbmRvci1zd2FnZ2VyJ1xuICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAvLyBSZURvYyAtIExvYWQgb25seSB3aGVuIEFwaURvY3VtZW50YXRpb24gdGFiIDEgaXMgYWN0aXZlIChsYXp5IGxvYWRlZClcbiAgICAgICAgICAgIGlmIChpZC5pbmNsdWRlcygncmVkb2MnKSkge1xuICAgICAgICAgICAgICByZXR1cm4gJ3ZlbmRvci1yZWRvYydcbiAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgLy8gQnVuZGxlIEVWRVJZVEhJTkcgZWxzZSB3aXRoIFJlYWN0IHRvIGVuc3VyZSBjb3JyZWN0IGxvYWQgb3JkZXJcbiAgICAgICAgICAgIC8vIFRoaXMgaW5jbHVkZXM6IFJlYWN0LCBSZWFjdC1ET00sIFJlYWN0LVJvdXRlciwgRW1vdGlvbiwgTVVJLFxuICAgICAgICAgICAgLy8gRnJhbWVyIE1vdGlvbiwgYWxsIFJlYWN0IGNvbXBvbmVudCBsaWJyYXJpZXMsIGV0Yy5cbiAgICAgICAgICAgIHJldHVybiAndmVuZG9yLXJlYWN0J1xuICAgICAgICAgIH1cbiAgICAgICAgfSxcbiAgICAgIH0sXG4gICAgfSxcblxuICAgIC8vIE9wdGltaXplIGRlcGVuZGVuY2llc1xuICAgIGNvbW1vbmpzT3B0aW9uczoge1xuICAgICAgaW5jbHVkZTogWy9ub2RlX21vZHVsZXMvXSxcbiAgICAgIHRyYW5zZm9ybU1peGVkRXNNb2R1bGVzOiB0cnVlLFxuICAgIH0sXG4gIH0sXG5cbiAgLy8gRGVwZW5kZW5jeSBvcHRpbWl6YXRpb25cbiAgb3B0aW1pemVEZXBzOiB7XG4gICAgaW5jbHVkZTogW1xuICAgICAgJ3JlYWN0JyxcbiAgICAgICdyZWFjdC1kb20nLFxuICAgICAgJ3JlYWN0LXJvdXRlci1kb20nLFxuICAgICAgJ0BtdWkvbWF0ZXJpYWwnLFxuICAgICAgJ0BtdWkvaWNvbnMtbWF0ZXJpYWwnLFxuICAgIF0sXG4gICAgZXhjbHVkZTogW1xuICAgICAgJ3N3YWdnZXItdWktcmVhY3QnLCAvLyBMYXp5IGxvYWRlZFxuICAgICAgJ3JlZG9jJywgICAgICAgICAgICAvLyBMYXp5IGxvYWRlZFxuICAgIF0sXG4gIH0sXG59KSJdLAogICJtYXBwaW5ncyI6ICI7QUFBbVEsU0FB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
