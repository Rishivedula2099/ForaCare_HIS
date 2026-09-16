FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

FROM node:20-alpine
RUN apk add --no-cache curl && addgroup -g 1001 nodejs && adduser -u 1001 -G nodejs -D nextjs

WORKDIR /app
ENV NODE_ENV=production
# Next's standalone server.js binds to $HOSTNAME (default "localhost"),
# which resolves only to loopback inside the container - unreachable from
# other containers (nginx) and from the healthcheck's own "localhost" curl
# unless explicitly widened to all interfaces.
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD curl -f http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
