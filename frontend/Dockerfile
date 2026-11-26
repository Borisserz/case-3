# case-3 frontend — Vite React SPA + Nginx reverse proxy to backend
FROM node:22-alpine AS build

WORKDIR /web

COPY package.json package-lock.json ./
RUN npm ci

COPY . ./
RUN npm run build

FROM nginx:1.27-alpine

ENV CASE3_PORT=8000

# Шаблон: nginx подставляет CASE3_PORT при старте. $host и $uri не трогает.
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /web/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
