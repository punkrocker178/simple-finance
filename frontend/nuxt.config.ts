import { breakpoints } from './app/config/breakpoints'

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
    apiTarget: 'http://127.0.0.1:8000',
    public: {
      apiBase: '/api/backend',
    },
  },

  routeRules: {
    '/api/backend/**': { proxy: 'http://127.0.0.1:8000/**' },
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
