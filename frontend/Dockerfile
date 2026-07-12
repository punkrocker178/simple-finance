FROM node:22-bookworm-slim AS build

WORKDIR /app

ARG NUXT_API_TARGET=http://backend:8000
ARG NUXT_PUBLIC_API_BASE=/api/backend

ENV NUXT_API_TARGET=$NUXT_API_TARGET
ENV NUXT_PUBLIC_API_BASE=$NUXT_PUBLIC_API_BASE

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:22-bookworm-slim AS production

WORKDIR /app

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3001
ENV NUXT_API_TARGET=http://backend:8000
ENV NUXT_PUBLIC_API_BASE=/api/backend

COPY --from=build --chown=node:node /app/.output ./.output

USER node

EXPOSE 3001

CMD ["node", ".output/server/index.mjs"]
