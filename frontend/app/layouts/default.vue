<template>
  <v-app>
    <v-app-bar flat border>
      <v-app-bar-title class="font-weight-bold">
        <NuxtLink to="/" class="text-decoration-none text-high-emphasis">
          Simple Finance
        </NuxtLink>
      </v-app-bar-title>
      <v-spacer />
      <v-btn to="/" variant="text">Watchlist</v-btn>
      <v-btn to="/backtest" variant="text">Backtest</v-btn>
      <v-btn to="/backtest/history" variant="text">History</v-btn>
    </v-app-bar>

    <v-main>
      <div class="mx-auto max-w-6xl p-4 md:p-6">
        <slot />
      </div>
    </v-main>
  </v-app>
</template>
