FROM node:22-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM dependencies AS development
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM dependencies AS build
COPY . .
RUN npm run build
ARG RELEASE_SHA=development
RUN printf '{"sha":"%s"}\n' "$RELEASE_SHA" > /app/dist/release.json

FROM caddy:2-alpine AS production
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
EXPOSE 80 443
