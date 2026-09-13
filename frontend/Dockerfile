FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine AS runtime
# Patch the base image before adding anything. nginx:alpine trails Alpine
# security updates (libuuid/util-linux and friends), and the publish gate blocks
# on fixable findings. Rebuilt without cache on every publish — see
# no-cache-filters in publish.yml — because a cached layer would replay the
# package set from whenever it was first built.
RUN apk upgrade --no-cache \
    && apk add --no-cache openssl
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.d/40-selfsigned-cert.sh /docker-entrypoint.d/40-selfsigned-cert.sh
RUN chmod +x /docker-entrypoint.d/40-selfsigned-cert.sh
ENV NGINX_ENVSUBST_FILTER='^(HTTPS_PORT)$'
EXPOSE 80 443
