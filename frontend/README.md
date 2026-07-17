# Simple Finance Frontend

Nuxt 4 UI for the Simple Finance FastAPI backend.

## Stack

- Nuxt 4 (SSR for data, `<ClientOnly>` for ECharts)
- Vuetify 3 + Tailwind CSS
- Pinia
- ECharts (`vue-echarts`)

## Architecture

Data fetching uses typed API composables (`useMarketApi`, `useBacktestApi`) with `useAsyncData` for page reads, and Pinia only for interactive/mutable state (backtest form + run result).

See [docs/state-and-data-fetching.md](docs/state-and-data-fetching.md) for when to use Pinia vs `useAsyncData` in this SSR app.

## Setup

```bash
cp .env.example .env
npm install
```

## Dev

Start FastAPI on `:8000`, then:

```bash
npm run dev
```

Open http://127.0.0.1:3000

## Scripts

- `npm run dev` — development server
- `npm run build` — production build
- `npm run preview` — preview production build
