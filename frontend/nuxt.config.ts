import { breakpoints } from './app/config/breakpoints'

const apiTarget = process.env.NUXT_API_TARGET || 'http://127.0.0.1:8000'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  modules: [
    'vuetify-nuxt-module',
    '@pinia/nuxt'
  ],

  css: [
    '~/assets/styles/layers.css',
    'vuetify/styles',
    '~/assets/styles/tailwind.css',
  ],

  postcss: {
    plugins: {
      '@tailwindcss/postcss': {},
    },
  },

  runtimeConfig: {
    apiTarget,
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || '/api/backend',
    },
  },

  routeRules: {
    '/api/backend/**': { proxy: `${apiTarget}/**` },
  },

  vuetify: {
    moduleOptions: {
      styles: { configFile: 'assets/styles/settings.scss' },
    },
    vuetifyOptions: {
      display: {
        mobileBreakpoint: 'md',
        thresholds: breakpoints,
      },
      theme: {
        defaultTheme: 'light',
        utilities: false,
      },
    },
  },

  vite: {
    ssr: {
      noExternal: ['vuetify'],
    },
  },
})
